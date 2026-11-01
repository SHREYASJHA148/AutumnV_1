"""Bounded PowerShell over stdin; its owned process tree is cancellable."""
from __future__ import annotations

import ctypes
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import win32job
from pywintypes import error as WindowsError

BOOTSTRAP = """[Console]::InputEncoding=[Text.UTF8Encoding]::new($false); [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); $ErrorActionPreference='Stop'; $s=[Console]::In.ReadToEnd(); try {$b=[scriptblock]::Create($s)} catch {[Console]::Error.WriteLine($_.Exception.Message);exit 2}; try {& $b; if (!$?) {exit 1}} catch {[Console]::Error.WriteLine($_.Exception.Message);exit 1}"""
HELPERS = Path(__file__).with_name('windows.ps1').read_text(encoding='utf-8')


@dataclass(frozen=True)
class ShellResult:
    code: str
    output: str = ''
    returncode: int | None = None

    def observation(self):
        return {'code':self.code,'output':self.output,'returncode':self.returncode}


class PowerShell:
    def __init__(self, cwd: Path):
        self.cwd = cwd

    def run(self, script: str, checkpoint, *, timeout: float = 35) -> ShellResult:
        if not checkpoint():
            return ShellResult('CANCELLED')
        executable = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        job = win32job.CreateJobObject(None, '')
        process = None
        keep_children = False
        buffers = [bytearray(), bytearray()]
        readers = []
        try:
            info = win32job.QueryInformationJobObject(job,win32job.JobObjectExtendedLimitInformation)
            info['BasicLimitInformation']['LimitFlags'] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(job,win32job.JobObjectExtendedLimitInformation,info)
            # Suspend before assignment: no command or descendant can escape the owned job.
            process = subprocess.Popen([str(executable),'-NoLogo','-NoProfile','-NonInteractive','-Command',BOOTSTRAP],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=self.cwd,
                creationflags=subprocess.CREATE_NO_WINDOW | 0x4)
            win32job.AssignProcessToJobObject(job,int(process._handle))
            resume = ctypes.WinDLL('ntdll').NtResumeProcess
            resume.argtypes = [ctypes.c_void_p]
            resume.restype = ctypes.c_long
            if resume(int(process._handle)) != 0:
                raise OSError('Could not resume contained command')

            def drain(stream, buffer):
                try:
                    while chunk := stream.read(4096):
                        buffer.extend(chunk[:max(0,12_000-len(buffer))])
                except (OSError, ValueError):
                    pass

            for stream, buffer in zip((process.stdout,process.stderr),buffers,strict=True):
                reader = threading.Thread(target=drain,args=(stream,buffer),daemon=True)
                reader.start()
                readers.append(reader)
            payload = (HELPERS+'\n'+script).encode('utf-8')
            # Bounded model scripts fit the Windows pipe; use a writer so Stop never waits on it.
            def write():
                try:
                    process.stdin.write(payload)
                    process.stdin.close()
                except (OSError, ValueError):
                    pass
            threading.Thread(target=write,daemon=True).start()
            deadline = time.monotonic()+min(60,max(.1,timeout))
            code = 'OK'
            while process.poll() is None:
                if not checkpoint():
                    code = 'CANCELLED'
                    break
                if time.monotonic() >= deadline:
                    code = 'TIMEOUT'
                    break
                time.sleep(.025)
            if code != 'OK':
                win32job.TerminateJobObject(job,1)
            process.wait(timeout=2)
            keep_children = code == 'OK' and process.returncode == 0 and checkpoint()
            if not keep_children and code == 'OK':
                code = 'CANCELLED' if not checkpoint() else ('SYNTAX_ERROR' if process.returncode == 2 else 'ERROR')
            for reader in readers:
                reader.join(.1)
            output = '\n'.join(b.decode('utf-8',errors='replace').strip() for b in buffers if b).strip()
            return ShellResult(code,output[:16_000],process.returncode)
        except (OSError, WindowsError, subprocess.SubprocessError):
            return ShellResult('COMPONENT_UNAVAILABLE','The local command process could not be contained or started.')
        finally:
            if keep_children:
                # An app deliberately started by a successful command remains open normally.
                info['BasicLimitInformation']['LimitFlags'] = 0
                win32job.SetInformationJobObject(job,win32job.JobObjectExtendedLimitInformation,info)
            else:
                win32job.TerminateJobObject(job,1)
                if process is not None and process.poll() is None:
                    process.kill()  # Also covers an assignment failure before the child joined the job.
            job.Close()

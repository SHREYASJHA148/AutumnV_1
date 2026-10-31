"""Read-only owned-process counters; no paths, audio or prompts logged."""

import ctypes
import os
from ctypes import wintypes as W


class Memory(ctypes.Structure):
    _fields_ = [
        ("cb", W.DWORD),
        ("faults", W.DWORD),
        *[
            (n, ctypes.c_size_t)
            for n in (
                "peak_working",
                "working",
                "peak_paged",
                "paged",
                "peak_nonpaged",
                "nonpaged",
                "pagefile",
                "peak_pagefile",
                "private",
            )
        ],
    ]


def sample(pid):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    kernel.OpenProcess.restype = W.HANDLE
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.GetProcessTimes.argtypes = [W.HANDLE, *([ctypes.POINTER(W.FILETIME)] * 4)]
    psapi = ctypes.WinDLL("psapi")
    psapi.GetProcessMemoryInfo.argtypes = [W.HANDLE, ctypes.POINTER(Memory), W.DWORD]
    handle = kernel.OpenProcess(0x410, False, pid)
    if not handle:
        return None
    try:
        created, ended, cpu_kernel, cpu_user = (W.FILETIME() for _ in range(4))
        memory = Memory(cb=ctypes.sizeof(Memory))
        if not kernel.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(ended),
            ctypes.byref(cpu_kernel),
            ctypes.byref(cpu_user),
        ):
            return None
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(memory), ctypes.sizeof(memory)):
            return None
        def seconds(value):
            return ((value.dwHighDateTime << 32) | value.dwLowDateTime) / 10_000_000
        return {
            "pid": pid,
            "cpu_seconds": seconds(cpu_kernel) + seconds(cpu_user),
            "working_mb": memory.working / 1024**2,
            "private_mb": memory.private / 1024**2,
            "peak_working_mb": memory.peak_working / 1024**2,
        }
    finally:
        kernel.CloseHandle(handle)


def owned_pids(vm, extra=None):
    values = {os.getpid()}
    supervisors = [vm.supervisor, *vm.voice.service.workers.values()]
    if vm.wake.worker:
        supervisors.append(vm.wake.worker)
    if vm.setup.worker:
        supervisors.append(vm.setup.worker)
    if extra:
        supervisors.extend(extra.workers.values())
    for worker in supervisors:
        if worker.process is not None and worker.process.is_alive():
            values.add(worker.process.pid)
    return values

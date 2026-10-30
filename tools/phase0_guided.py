"""Owner-operated Phase 0 speech/playback/focus fixture. No audio/transcript logs."""
from __future__ import annotations
import ctypes
import json
import multiprocessing as mp
from pathlib import Path
import queue
import re
import sys
import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = [
    'Open Notepad', 'Launch the calculator', 'Open my Documents folder',
    'Show Downloads in File Explorer', 'Visit Wikipedia', 'Open the YouTube website',
    'Set the volume to forty percent', 'Set the volume to fifteen percent',
    'Set volume to one hundred percent', 'Mute the sound', 'Unmute my laptop',
    'Pause the music', 'Skip to the next song', 'Go back to the previous track',
    'Take a screenshot', 'Capture all my monitors', 'Run my study routine',
    'Open Notepad please', 'Open my Downloads folder', 'Set the volume to fifty percent',
]


def normalized(text):
    text = ' '.join(re.findall(r'[a-z0-9]+', text.lower()))
    for word, number in [('one hundred','100'),('forty','40'),('fifteen','15'),('fifty','50')]:
        text = text.replace(word, number)
    return text.replace('note pad', 'notepad')


def worker(commands, events):
    import numpy as np
    import sounddevice as sd
    from scipy.signal import resample_poly
    from math import gcd
    from pywhispercpp.model import Model
    from phase0_intent import intent,EXPECTED
    devices = sd.query_devices()
    candidates = [i for i,d in enumerate(devices) if d['max_input_channels'] and 'microphone array' in d['name'].lower()]
    if not candidates:
        events.put(('error', 'Built-in microphone array not found.')); return
    device = next((i for i in candidates if 'WASAPI' in sd.query_hostapis(devices[i]['hostapi'])['name']), candidates[0])
    rate = int(devices[device]['default_samplerate'])
    models, recordings, scored = {}, {}, set()
    events.put(('ready', 'Ready. Press Record, then read the displayed command.'))
    while True:
        parent=mp.parent_process()
        if parent is not None and not parent.is_alive(): return
        try:
            command, index = commands.get(timeout=1)
        except queue.Empty:
            command, index = 'poll', -1
        if command == 'quit': return
        if command == 'play':
            import wave
            played = 0
            for path in sorted((ROOT/'.cache/voice-tests').glob('piper-*.wav'))[:10]:
                with wave.open(str(path),'rb') as stream:
                    audio=np.frombuffer(stream.readframes(stream.getnframes()),dtype=np.int16)
                    sd.play(audio,stream.getframerate()); sd.wait()
                played += 1
            events.put(('playback', played)); continue
        if command == 'record':
            try:
                events.put(('recording', index))
                audio = sd.rec(rate*4, samplerate=rate, channels=1, dtype='float32', device=device)
                sd.wait()
                divisor=gcd(rate,16000)
                audio=resample_poly(audio[:,0],16000//divisor,rate//divisor).astype(np.float32)
                recordings[index]=audio
                events.put(('captured', {'case':index+1,'rms':float(np.sqrt(np.mean(audio**2)))}))
            except Exception as exc:
                events.put(('error', f'Recording failed: {type(exc).__name__}')); continue
        for size in ('base.en','small.en'):
            path=ROOT/f'models/stt/ggml-{size}.bin'
            if not path.exists(): continue
            for case, audio in list(recordings.items()):
                if (size,case) in scored: continue
                try:
                    if size not in models:
                        events.put(('status', f'Loading {size} locally…'))
                        models[size]=Model(str(path),context_params={'use_gpu':False},n_threads=4,
                            redirect_whispercpp_logs_to=None,print_realtime=False,print_progress=False,language='en')
                    started=time.perf_counter()
                    segments=models[size].transcribe(audio,language='en',print_realtime=False,no_context=True)
                    recognized=' '.join(s.text for s in segments)
                    events.put(('preview', f'{size}, previous capture {case+1}: {recognized}'))
                    events.put(('score',{'model':size,'case':case+1,
                        'normalized_phrase_match':normalized(recognized)==normalized(PROMPTS[case]),
                        'intended_action_match':intent(recognized)==EXPECTED[case],
                        'seconds':round(time.perf_counter()-started,3)}))
                    scored.add((size,case))
                    # recognized speech and audio remain in memory only, never sent to a model service.
                except Exception as exc:
                    events.put(('error', f'{size} recognition failed: {type(exc).__name__}'))
                    return
        if command=='record': events.put(('ready', 'Capture completed. Continue with the next command.'))


class Fixture(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Autumn — guided Phase 0 validation')
        self.resize(720,470)
        self.commands,self.events=mp.Queue(),mp.Queue()
        self.process=mp.Process(target=worker,args=(self.commands,self.events),daemon=True)
        self.process.start()
        self.index=0; self.results=[]; self.captured=[]; self.played=0
        self.focus_verified=False; self.heard=False
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('Test fixture only. No computer commands are executed.\nAudio stays in memory and is discarded when this window closes.'))
        self.prompt=QLabel(PROMPTS[0]); self.prompt.setStyleSheet('font-size:24px; padding:16px')
        layout.addWidget(self.prompt)
        self.status=QLabel('Preparing built-in microphone…'); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.preview=QLabel('Recognition preview stays on screen only; it is not written to a log.'); self.preview.setWordWrap(True); layout.addWidget(self.preview)
        self.record=QPushButton('Record command 1 of 20 (four seconds)'); self.record.setEnabled(False)
        self.record.clicked.connect(self.capture); layout.addWidget(self.record)
        play=QPushButton('Play ten female voice samples (microphone closed)'); play.clicked.connect(self.play); layout.addWidget(play)
        heard=QPushButton('I heard the samples clearly'); heard.clicked.connect(self.confirm_heard); layout.addWidget(heard)
        focus=QPushButton('Test overlay focus — click here and keep this window active'); focus.clicked.connect(self.focus); layout.addWidget(focus)
        stop=QPushButton('STOP / close capture and discard audio'); stop.clicked.connect(self.close); layout.addWidget(stop)
        self.overlay=QLabel('Autumn: non-activating confirmation test',None,
            Qt.Tool|Qt.WindowStaysOnTopHint|Qt.WindowDoesNotAcceptFocus)
        self.overlay.setAttribute(Qt.WA_ShowWithoutActivating)
        self.timer=QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(100)

    def capture(self):
        self.record.setEnabled(False); self.status.setText('Opening microphone. Read the displayed command now (four seconds).')
        self.commands.put(('record',self.index))

    def play(self):
        self.record.setEnabled(False); self.status.setText('Playing ten fixed samples; microphone is closed.'); self.commands.put(('play',0))

    def confirm_heard(self):
        self.heard=self.played==10; self.save(); self.status.setText('Playback confirmation saved.' if self.heard else 'Please play all samples before confirming.')

    def focus(self):
        user32=ctypes.WinDLL('user32'); user32.GetForegroundWindow.restype=ctypes.c_void_p
        before=user32.GetForegroundWindow(); expected=int(self.winId())
        self.overlay.show()
        def check():
            self.focus_verified=before==expected and user32.GetForegroundWindow()==expected
            self.overlay.hide(); self.save(); self.status.setText(f'Overlay preserved the explicitly focused target: {self.focus_verified}')
        QTimer.singleShot(600,check)

    def save(self):
        report={'owner_operated':True,'captured_cases':len(self.captured),'raw_audio_saved':False,
            'protocol':'v2 records exact phrase and bounded local intent separately; no actions dispatched',
            'capture_levels':self.captured,
            'transcripts_saved':False,'phrase_scores':self.results,'command_routing_measured':False,
            'playback_files_completed':self.played,'owner_heard_samples':self.heard,
            'focused_overlay_verified':self.focus_verified,'completed':len(self.results)==40}
        (ROOT/'docs/reports/guided_owner.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

    def poll(self):
        while True:
            try: kind,data=self.events.get_nowait()
            except queue.Empty: break
            if kind in ('status','ready','error'): self.status.setText(str(data))
            if kind=='ready': self.record.setEnabled(self.index<20)
            if kind=='captured':
                self.captured.append(data); self.index+=1
                self.status.setText(f'Microphone level RMS: {data["rms"]:.5f}; comparing locally…')
                self.prompt.setText(PROMPTS[self.index] if self.index<20 else '20 recordings captured. Keep open until both models finish.')
                self.record.setText(f'Record command {min(self.index+1,20)} of 20 (four seconds)')
            if kind=='score':
                self.results.append(data)
                self.status.setText(f'{len(self.results)}/40 recognition comparisons complete. No transcript stored.')
            if kind=='preview':
                self.preview.setText(data)
            if kind=='playback':
                self.played=data; self.record.setEnabled(self.index<20); self.status.setText('Samples finished. Confirm whether you heard them clearly.')
            self.save()

    def closeEvent(self,event):
        self.timer.stop(); self.overlay.close()
        if self.process.is_alive(): self.process.terminate(); self.process.join(3)
        self.save(); event.accept()


if __name__=='__main__':
    mp.freeze_support()
    app=QApplication(sys.argv); fixture=Fixture(); fixture.show(); raise SystemExit(app.exec())

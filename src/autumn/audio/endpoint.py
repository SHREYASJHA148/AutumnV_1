"""Frame-continuous local VAD and silence bounds; never stores or logs audio."""
import numpy as np


class SpeechEndpoint:
    rate=16000
    frame_samples=480
    silence_samples=7200  # 450 ms after the final voiced frame.

    def __init__(self,detector=None,silence_ms=450):
        if not 400 <= silence_ms <= 1500:
            raise ValueError('Invalid response-pause bound')
        self.silence_samples=round(silence_ms*self.rate/1000)
        if detector is None:
            import webrtcvad
            detector=webrtcvad.Vad(2)
        self.detector=detector
        self.pending=np.empty(0,dtype=np.float32)
        self.processed=0
        self.total=0
        self.first_voiced=None
        self.last_voiced=None

    def feed(self,audio):
        data=np.asarray(audio,dtype=np.float32).reshape(-1)
        if not np.isfinite(data).all() or self.total+len(data)>320000:
            raise ValueError('Invalid bounded endpoint input')
        self.total+=len(data)
        combined=np.concatenate((self.pending,data))
        self.pending.fill(0)
        end=len(combined)//self.frame_samples*self.frame_samples
        for offset in range(0,end,self.frame_samples):
            frame=combined[offset:offset+self.frame_samples]
            pcm=(np.clip(frame,-1,1)*32767).astype('<i2').tobytes()
            detected=self.detector.is_speech(pcm,self.rate)
            if detected and float(np.sqrt(np.mean(frame*frame)))>=.001:
                if self.first_voiced is None:
                    self.first_voiced=self.processed
                self.last_voiced=self.processed+self.frame_samples
            self.processed+=self.frame_samples
        self.pending=combined[end:].copy()
        combined.fill(0)

    @property
    def heard_speech(self):
        return self.first_voiced is not None

    @property
    def finished(self):
        return self.last_voiced is not None and self.total-self.last_voiced>=self.silence_samples

    def bounds(self,source_rate,length):
        if not self.heard_speech:
            return 0,length
        start=max(0,int((self.first_voiced/self.rate-.25)*source_rate))
        end=min(length,int((self.last_voiced/self.rate+.18)*source_rate))
        return start,end

    def discard(self):
        self.pending.fill(0)
        self.pending=np.empty(0,dtype=np.float32)

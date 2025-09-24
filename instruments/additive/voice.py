import numpy as np

N_PARTIALS = 6
SR = 44100

class Voice:
    def __init__(self, f0, velocity, sr=SR, attack=0.0, decay=0.08, sustain=0.5, release=0.20):
        self.f0 = f0
        # Gentler velocity curve: softens loud hits (tweak 1.3–2.0 to taste)
        self.v = (velocity / 127.0) ** 2.0
        self.sr = sr
        self.a = attack; self.d = decay; self.s = sustain; self.r = release
        self.t = 0.0
        self.state = 'attack'
        self.two_pi = 2*np.pi
        self.phases = np.zeros(N_PARTIALS, dtype=np.float64)

        # Partial amplitudes
        amps = np.array([1.0 / ((k+1)**5) for k in range(N_PARTIALS)], dtype=np.float64)
        amps_sum = np.sum(np.abs(amps))
        self.partial_amps = amps / (amps_sum if amps_sum > 0 else 1.0)

        self.partial_freqs = np.array([(k+1)*self.f0 for k in range(N_PARTIALS)], dtype=np.float64)

    def note_off(self):
        if self.state != 'dead':
            self.state = 'release'
            self.t = 0.0

    def finished(self):
        return self.state == 'dead'

    def _env_step(self, n):
        out = np.zeros(n, dtype=np.float64)
        idx = 0
        while idx < n and self.state != 'dead':
            remain = n - idx
            if self.state == 'attack':
                dur = max(1, int(self.a*self.sr))
                pos = min(remain, dur - int(self.t*self.sr))
                if dur == 1:
                    self.state = 'decay'
                    continue
                start = int(self.t*self.sr); end = start+pos
                envseg = np.linspace(start, end, pos, endpoint=False)
                envseg = (envseg - start)/max(1, dur-1)
                out[idx:idx+pos] = envseg
                self.t += pos/self.sr
                if int(self.t*self.sr) >= dur:
                    self.state = 'decay'; self.t = 0.0
                idx += pos

            elif self.state == 'decay':
                dur = max(1, int(self.d*self.sr))
                pos = min(remain, dur - int(self.t*self.sr))
                start = int(self.t*self.sr); end = start+pos
                if dur <= 1:
                    envseg = np.full(pos, self.s)
                else:
                    envseg = 1 + (self.s-1)*(np.linspace(start, end, pos, endpoint=False)-start)/(dur-1)
                out[idx:idx+pos] = envseg
                self.t += pos/self.sr
                if int(self.t*self.sr) >= dur:
                    self.state = 'sustain'; self.t = 0.0
                idx += pos

            elif self.state == 'sustain':
                out[idx:] = self.s
                idx = n

            elif self.state == 'release':
                dur = max(1, int(self.r*self.sr))
                pos = min(remain, dur - int(self.t*self.sr))
                start = int(self.t*self.sr); end = start+pos
                if dur <= 1:
                    envseg = np.zeros(pos)
                else:
                    envseg = self.s * (1 - (np.linspace(start, end, pos, endpoint=False)-start)/(dur-1))
                out[idx:idx+pos] = envseg
                self.t += pos/self.sr
                if int(self.t*self.sr) >= dur:
                    self.state = 'dead'
                idx += pos
        return out

    def render(self, n):
        phase_incr = (self.two_pi * self.partial_freqs) / self.sr
        env = self._env_step(n)
        out = np.zeros(n, dtype=np.float64)

        phases = self.phases
        for i in range(n):
            phases += phase_incr
            phases -= np.floor(phases/(2*np.pi))*(2*np.pi)
            out[i] = np.sin(phases) @ self.partial_amps
        self.phases = phases

        # No per-block normalization here (prevents pumping)
        return (out * env * self.v).astype(np.float32)

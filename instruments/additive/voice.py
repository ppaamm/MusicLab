import numpy as np

class Voice:
    def __init__(self, f0, velocity, sr, N_PARTIALS=10, attack=0.1, decay=0.08, sustain=0.75, release=0.20):
        #TODO: Manage this N_PARTIALS... Here? Somewhere else?
        self.f0 = f0
        self.v = (velocity/127.0)
        self.sr = sr
        self.a = attack; self.d = decay; self.s = sustain; self.r = release
        self.t = 0.0
        self.state = 'attack'  # 'attack','decay','sustain','release','dead'
        self.phases = np.zeros(N_PARTIALS, dtype=np.float64)
        self.two_pi = 2*np.pi
        # per-partial amplitude (same law as your example)
        amps = np.array([1.0/((k+1)**5) for k in range(N_PARTIALS)], dtype=np.float64)
        amps_sum = np.sum(amps)
        self.partial_amps = amps / (amps_sum if amps_sum > 0 else 1.0)
        
        self.partial_freqs = np.array([(k+1)*self.f0 for k in range(N_PARTIALS)], dtype=np.float64)

    def note_off(self):
        if self.state != 'dead':
            self.state = 'release'
            self.t = 0.0  # restart time within release stage

    def finished(self):
        return self.state == 'dead'

    def _env_step(self, n):
        # Generate amplitude envelope for n samples, advancing envelope time/state
        out = np.zeros(n, dtype=np.float64)
        idx = 0
        while idx < n and self.state != 'dead':
            remain = n - idx
            if self.state == 'attack':
                dur = max(1, int(self.a * self.sr))
                pos = min(remain, dur - int(self.t*self.sr))
                if dur == 1: 
                    self.state = 'decay'
                    continue
                # linear 0 -> 1
                start = int(self.t * self.sr)
                end = start+pos
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
                # linear 1 -> sustain
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
                idx = n  # fill the rest; sustain continues
            elif self.state == 'release':
                dur = max(1, int(self.r * self.sr))
                pos = min(remain, dur - int(self.t*self.sr))
                start = int(self.t*self.sr); end = start+pos
                # linear sustain -> 0
                if dur <= 1:
                    envseg = np.zeros(pos)
                else:
                    envseg = self.s * (1 - (np.linspace(start, end, pos, endpoint=False)-start)/(dur-1))
                out[idx:idx+pos] = envseg
                self.t += pos/self.sr
                
                if int(self.t * self.sr) >= dur:
                    print("dead")
                    self.state = 'dead'
                idx += pos
        return out

    def render(self, n):
        phase_incr = (self.two_pi * self.partial_freqs) / self.sr
        # make n-sample buffer
        out = np.zeros(n, dtype=np.float64)
        env = self._env_step(n)
        # accumulate partials sample-by-sample in vectorized chunks
        # phase accumulation:
        phases = self.phases
        for i in range(n):
            phases += phase_incr
            # wrap
            phases -= np.floor(phases/(2*np.pi))*(2*np.pi)
            # sin sum
            s = np.sin(phases) @ self.partial_amps
            out[i] = s
        self.phases = phases
        # normalize partial bank to sane range
        #out /= max(1e-9, np.max(np.abs(out))+1e-9)
        return (out * env * self.v).astype(np.float32)
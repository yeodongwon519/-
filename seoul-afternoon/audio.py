"""Generates a soft lo-fi piano + pad bed (8 s loop, 44.1 kHz stereo WAV) with pure Python."""
import math, wave, struct, random

SR = 44100
DUR = 8.0
N = int(SR * DUR)
random.seed(3)

def note(freq):  # midi-ish helper
    return freq

def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)

# chord progression (2 s each): Cmaj7 -> Am9 -> Fmaj7 -> G6/9  (lo-fi cafe)
chords = [
    [60, 64, 67, 71, 74],
    [57, 60, 64, 67, 71],
    [53, 57, 60, 64, 67],
    [55, 59, 62, 64, 69],
]
L = [0.0] * N
R = [0.0] * N

def pluck(start, freq, amp, dur=1.8, pan=0.0):
    s0 = int(start * SR)
    n = int(dur * SR)
    for i in range(n):
        idx = s0 + i
        if idx >= N:
            break
        t = i / SR
        env = math.exp(-t * 2.6) * (1 - math.exp(-t * 400))
        v = (math.sin(2 * math.pi * freq * t) * 0.6
             + math.sin(2 * math.pi * freq * 2 * t) * 0.25 * math.exp(-t * 4)
             + math.sin(2 * math.pi * freq * 3 * t) * 0.1 * math.exp(-t * 6))
        v *= env * amp
        L[idx] += v * (1 - pan) * 0.5
        R[idx] += v * (1 + pan) * 0.5

def pad(start, freqs, amp, dur=2.2):
    s0 = int(start * SR)
    n = int(dur * SR)
    for i in range(n):
        idx = s0 + i
        if idx >= N:
            break
        t = i / SR
        env = min(t / 0.6, 1.0) * min((dur - t) / 0.8, 1.0)
        v = 0.0
        for f in freqs:
            v += math.sin(2 * math.pi * f * t + 0.3 * math.sin(2 * math.pi * 0.4 * t))
        v = v / len(freqs) * env * amp
        L[idx] += v * 0.9
        R[idx] += v * 1.0

for ci, ch in enumerate(chords):
    t0 = ci * 2.0
    pad(t0, [midi(n - 12) for n in ch[:3]], 0.16)
    # gentle arpeggio, slightly swung
    order = [0, 2, 1, 3, 4, 2, 3, 1]
    for k, idx in enumerate(order):
        tt = t0 + k * 0.25 + (0.03 if k % 2 else 0)
        pluck(tt, midi(ch[idx] + 12), 0.22 + random.random() * 0.06, pan=(idx - 2) * 0.25)
    # bass
    pluck(t0, midi(ch[0] - 24), 0.30, dur=1.9)
    pluck(t0 + 1.0, midi(ch[0] - 24), 0.18, dur=1.0)

# soft vinyl-ish noise bed
for i in range(N):
    n = (random.random() - 0.5) * 0.012
    L[i] += n
    R[i] += n * 0.8

# simple one-pole low-pass for warmth + normalise
def lp(x, a=0.25):
    y = [0.0] * len(x); p = 0.0
    for i, v in enumerate(x):
        p = p + a * (v - p); y[i] = p
    return y
L = lp(L); R = lp(R)
peak = max(max(abs(v) for v in L), max(abs(v) for v in R)) or 1.0
g = 0.85 / peak
# short fade in/out so the loop is click-free
fade = int(0.05 * SR)
with wave.open('bgm.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    frames = bytearray()
    for i in range(N):
        f = 1.0
        if i < fade: f = i / fade
        elif i > N - fade: f = (N - i) / fade
        l = int(max(-1, min(1, L[i] * g * f)) * 32767)
        r = int(max(-1, min(1, R[i] * g * f)) * 32767)
        frames += struct.pack('<hh', l, r)
    w.writeframes(bytes(frames))
print('bgm.wav written', N, 'samples')

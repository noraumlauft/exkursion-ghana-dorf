"""Erzeugt die Hintergrundgeräusche als Schleifen in assets/audio/:

  ambient-gespraech.mp3  undeutliches Gespräch weniger Menschen (aus der Ferne, gedämpft)
  ambient-pumpe.mp3      Handpumpe: Schwengel-Klacken, leichtes Quietschen, Wasserschwall

Benötigt: pip install edge-tts numpy, ffmpeg; Netz zu speech.platform.bing.com.
Aufruf:   python3 tools/generate-ambient.py [pumpe|gespraech]
Die Sätze werden stark tiefpassgefiltert – man hört Stimmen, versteht aber keine Wörter.
"""
import asyncio, os, random, subprocess, tempfile
from pathlib import Path
import numpy as np
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/audio"
SR = 44100
rng = np.random.default_rng(7)
random.seed(7)

def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(SR), "pipe:1"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def encode(x, path, kbps=96):
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype(np.int16).tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0",
                    "-codec:a", "libmp3lame", "-b:a", f"{kbps}k", str(path)], input=pcm, check=True)

def lowpass(x, fc, order=3):
    """Tiefpass über ffmpeg (order × 2-poliger Filter)."""
    chain = ",".join([f"lowpass=f={fc}:p=2"] * order)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0",
                          "-af", chain, "-f", "f32le", "pipe:1"], input=x.astype(np.float32).tobytes(),
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()

def reverb(x, amount=.25):
    y = x.copy()
    for d, g in [(0.029, .5), (0.047, .4), (0.071, .3), (0.113, .22), (0.167, .15)]:
        n = int(d * SR); y[n:] += amount * g * x[:-n]
    return y

def fade_loop(x, seconds=2.0):
    """Ende weich in den Anfang überblenden, damit die Schleife nahtlos ist."""
    n = int(seconds * SR); head, body, tail = x[:n], x[n:-n] if len(x) > 2 * n else x[n:], x[-n:]
    t = np.linspace(0, 1, n)
    return np.concatenate([tail * (1 - t) + head * t, body])

# ---------------- Gespräch ----------------
SPEAKERS = [("en-NG-AbeoNeural", "-6%", "-4Hz", .9), ("en-NG-EzinneNeural", "-4%", "+0Hz", 1.0),
            ("en-KE-ChilembaNeural", "-8%", "-8Hz", .75), ("en-TZ-ImaniNeural", "-2%", "+4Hz", .85)]
LINES = [
    "Good morning, how is your family?", "They are fine, thank you. And yours?", "The rain did not come yesterday.",
    "My brother went to the market early today.", "Did you see the new goats?", "Yes, yes, they are very small.",
    "We will harvest the cocoa next week.", "The children are already at school.", "Ah, that is true, my sister.",
    "I need more water for the cooking.", "Tomorrow we go to town together.", "Hmm, maybe in the afternoon.",
    "The price for cocoa is still too low.", "Come and sit with us a little.", "I will bring the basket later.",
    "Have you eaten already?", "Not yet, the soup is still cooking.", "Okay, I am coming back soon.",
]

async def speak(voice, rate, pitch, text, path):
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, proxy=proxy).save(str(path))

async def chatter(seconds=60):
    total = np.zeros(int((seconds + 6) * SR), np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        t = 0.5; i = 0
        lines = LINES[:]; random.shuffle(lines)
        while t < seconds:
            voice, rate, pitch, vol = SPEAKERS[i % len(SPEAKERS)] if random.random() < .7 else random.choice(SPEAKERS)
            text = lines[i % len(lines)]; p = Path(tmp) / f"{i}.mp3"
            await speak(voice, rate, pitch, text, p)
            x = decode(p) * vol
            start = int(t * SR); end = min(len(total), start + len(x))
            total[start:end] += x[:end - start]
            # nächste Person setzt nach kurzer Pause ein, manchmal fällt sie ins Wort
            t += len(x) / SR + random.choice([random.uniform(-.6, -.1), random.uniform(.2, 1.4), random.uniform(1.5, 4)])
            i += 1
    x = total[:int(seconds * SR) + int(2 * SR)]
    x = lowpass(x, 650, 3)            # Wörter unverständlich machen
    x = reverb(x, .35)
    x = fade_loop(x, 2.0)
    return x / (np.abs(x).max() + 1e-9) * .5

# ---------------- Handpumpe ----------------
def biquad_bp(x, f0, q):
    """Resonanzfilter (Bandpass, konstante Spitzenverstärkung 0 dB)."""
    w = 2 * np.pi * f0 / SR; al = np.sin(w) / (2 * q); a0 = 1 + al
    b0, b2 = al / a0, -al / a0; a1, a2 = -2 * np.cos(w) / a0, (1 - al) / a0
    y = np.zeros_like(x); x1 = x2 = y1 = y2 = 0.0
    for i, v in enumerate(x):
        o = b0 * v + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, v, y1, o; y[i] = o
    return y

def smooth_noise(n, rate):
    """Langsam schwankende Zufallskurve (für Lautstärke- und Tonhöhenschwankungen)."""
    k = max(2, int(n / SR * rate) + 2)
    return np.interp(np.arange(n), np.linspace(0, n, k), rng.standard_normal(k))

def squeak(dur, f_start, f_end, loud):
    """Quietschen wie Metall auf Metall: Haft-Gleit-Reibung (stick-slip).
    Unregelmäßige Impulsfolge mit schwankender Tonhöhe, kurzen Aussetzern und
    metallischen Resonanzen – kein reiner Sinuston."""
    n = int(dur * SR); x = np.zeros(n)
    jit = smooth_noise(n, 25) * .035; rough = np.clip(1 + .6 * smooth_noise(n, 18), 0, None)
    t = 0.0
    while t < dur:
        i = int(t * SR)
        if i >= n: break
        k = t / dur
        f = (f_start + (f_end - f_start) * k ** .7) * (1 + jit[i])
        if rng.random() > .04:                       # gelegentlich rutscht es kurz durch
            x[i] += rough[i] * rng.uniform(.7, 1.0)
        t += 1 / f * rng.uniform(.97, 1.03)
    res = (biquad_bp(x, 1180, 9) * 1.0 + biquad_bp(x, 2350, 14) * .7 +
           biquad_bp(x, 3450, 18) * .45 + biquad_bp(x, 5100, 22) * .2)
    tt = np.arange(n) / n
    env = np.minimum(1, tt / .12) * np.minimum(1, (1 - tt) / .25) * (.75 + .25 * np.sin(2 * np.pi * 7 * tt * dur))
    res *= env
    return loud * res / (np.abs(res).max() + 1e-9)

def bubble(f0, dur, decay):
    tt = np.arange(int(dur * SR)) / SR
    f = f0 * (1 + .9 * tt / max(tt[-1], 1e-9))       # Luftblase: Ton steigt beim Ablösen
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * decay)

def add(y, s, x):
    if s >= len(y): return
    e = min(len(y), s + len(x)); y[s:e] += x[:e - s]

def gush(dur, fill):
    """Wasserschwall aus dem Auslauf, der in einen Kanister prasselt.
    fill (0..1): je voller der Kanister, desto höher klingt er."""
    n = int(dur * SR); tt = np.arange(n) / SR
    env = np.minimum(1, tt / .04) * np.exp(-np.maximum(0, tt - .18) * 7)
    turb = np.clip(1 + .8 * smooth_noise(n, 45), 0, None)     # unruhiger Strahl
    noise = rng.standard_normal(n) * env * turb
    body = (biquad_bp(noise, 320 + 380 * fill, 3.5) * 1.0 +   # Hohlraum des Kanisters
            biquad_bp(noise, 900 + 500 * fill, 2.5) * .7 +
            biquad_bp(noise, 2600, 1.2) * .35)                # Spritzen
    body = lowpass(body.astype(np.float32), 3800, 2)               # kein Zischen in den Höhen
    y = body / (np.abs(body).max() + 1e-9) * .5
    # dichte Blasen und Spritzer im Strahl (das eigentliche „Plätschern“)
    for _ in range(int(dur * 260)):
        p = int(rng.beta(1.2, 2.2) * n)
        b = bubble(rng.uniform(350, 1100) * (1 + .6 * fill), rng.uniform(.012, .04), rng.uniform(60, 160))
        add(y, p, b * rng.uniform(.06, .22) * env[min(p, n - 1)])
    return y

def drips(dur, density, fill):
    """Nachtropfen und leises Plätschern in der Pfütze zwischen den Hüben."""
    n = int(dur * SR); y = np.zeros(n)
    for _ in range(int(dur * density)):
        p = int(rng.uniform(0, 1) * n); f = rng.uniform(700, 1900) * (1 + .3 * fill)
        add(y, p, bubble(f, .05, rng.uniform(55, 110)) * rng.uniform(.04, .14))
        if rng.random() < .3:  # kleiner Spritzer
            L = int(.02 * SR); s = rng.standard_normal(L) * np.exp(-np.arange(L) / SR * 220)
            add(y, p, biquad_bp(s, rng.uniform(2500, 4500), 2) * .08)
    return y

def clunk():
    L = int(.3 * SR); tt = np.arange(L) / SR
    c = sum(a * np.sin(2 * np.pi * fr * tt) * np.exp(-tt * d) for fr, a, d in [(110, 1, 26), (260, .55, 32), (640, .3, 40), (1520, .14, 55), (2890, .07, 70)])
    c += biquad_bp(rng.standard_normal(L) * np.exp(-tt * 180), 900, 2) * .6
    return c / np.abs(c).max()

def pump(seconds=14.0, strokes=7, period=.95):
    n = int(seconds * SR); y = np.zeros(n)
    for k in range(strokes):
        t0 = .4 + k * period + rng.uniform(-.03, .03); fill = k / (strokes - 1)
        # Schwengel hoch: deutliches Quietschen; Schwengel runter: kürzer und tiefer
        add(y, int(t0 * SR), squeak(rng.uniform(.26, .32), rng.uniform(560, 640), rng.uniform(760, 860), .32))
        add(y, int((t0 + .40) * SR), clunk() * .38)
        add(y, int((t0 + .36) * SR), squeak(.16, 470, 430, .12))
        add(y, int((t0 + .46) * SR), gush(.62, fill))
    end = .4 + strokes * period
    add(y, int(.9 * SR), drips(end - .5, 9, .5))                 # während des Pumpens
    add(y, int((end + .3) * SR), drips(2.6, 7, 1) * np.linspace(1, .2, int(2.6 * SR)))  # Nachtropfen
    y = lowpass(y.astype(np.float32), 7500, 1)
    y = reverb(y, .18)
    return y / (np.abs(y).max() + 1e-9) * .7

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    import sys
    only = sys.argv[1] if len(sys.argv) > 1 else None
    if only in (None, "pumpe"):
        encode(pump(), OUT / "ambient-pumpe.mp3", 128); print("erzeugt: assets/audio/ambient-pumpe.mp3")
    if only in (None, "gespraech"):
        encode(await chatter(), OUT / "ambient-gespraech.mp3", 64); print("erzeugt: assets/audio/ambient-gespraech.mp3")

if __name__ == "__main__":
    asyncio.run(main())

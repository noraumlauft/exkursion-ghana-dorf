"""Erzeugt die Hintergrundgeräusche als Schleifen in assets/audio/:

  ambient-gespraech.mp3  undeutliches Gespräch weniger Menschen (aus der Ferne, gedämpft)

(Die Handpumpe ambient-pumpe.mp3 ist eine echte Aufnahme, siehe README.)

Benötigt: pip install edge-tts numpy, ffmpeg; Netz zu speech.platform.bing.com.
Aufruf:   python3 tools/generate-ambient.py
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

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    encode(await chatter(), OUT / "ambient-gespraech.mp3", 64); print("erzeugt: assets/audio/ambient-gespraech.mp3")

if __name__ == "__main__":
    asyncio.run(main())

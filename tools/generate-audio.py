"""Erzeugt die Sprachaufnahmen der vier Stationen aus assets/audio/manifest.json.

Benötigt: pip install edge-tts (Netzwerkzugriff auf speech.platform.bing.com).
Aufruf:   python3 tools/generate-audio.py [--force]
Ohne --force werden nur fehlende Dateien erzeugt.
"""
import asyncio, json, os, sys
from pathlib import Path
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets/audio/manifest.json"

async def main(force: bool):
    m = json.loads(MANIFEST.read_text())
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    for clip in m["clips"]:
        target = MANIFEST.parent / clip["file"]
        if target.exists() and target.stat().st_size > 1000 and not force:
            continue
        com = edge_tts.Communicate(clip["text"], m["voice"], rate=m["rate"], pitch=m["pitch"], proxy=proxy)
        await com.save(str(target))
        print("erzeugt:", target.relative_to(ROOT))

if __name__ == "__main__":
    asyncio.run(main("--force" in sys.argv))

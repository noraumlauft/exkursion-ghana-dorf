"""Hängt an jede Asset-Adresse in index.html eine Versionsnummer (?v=…) aus dem Dateiinhalt.
So laden Browser und GitHub Pages nach einer Änderung sofort die neue Datei statt einer
zwischengespeicherten alten. Nach jedem Austausch eines Bildes oder Tons ausführen:
  python3 tools/update-versions.py
"""
import hashlib, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
page = ROOT / "index.html"
html = page.read_text()
def repl(m):
    path = m.group(1)
    v = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:8]
    return f'"{path}?v={v}"'
html = re.sub(r'"(assets/[^"?]+)(?:\?v=[0-9a-f]+)?"', repl, html)
page.write_text(html)
print("\n".join(re.findall(r'"assets/[^"]+"', html)))

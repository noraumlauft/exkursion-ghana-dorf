# Ein Dorf in Ghana – virtuelle 360°-Exkursion

360°-Rundgang durch ein Dorf in Ghana für die Grundschule (3. Klasse), als Ergänzung zur
[Exkursion Kakaoplantage](https://github.com/noraumlauft/exkursion-kakaoplantage).
Es gibt kein anschließendes Spiel. Die Kinder schauen sich um und besuchen vier Stationen.

**Online:** https://noraumlauft.github.io/exkursion-ghana-dorf/

## Stationen

Tippen die Kinder eine Station an, dreht sich die Ansicht dorthin. Der Text erscheint, und die
Tonaufnahme startet automatisch („Nochmal hören“ spielt sie erneut ab).

| Nr. | Station | Text |
|---|---|---|
| 1 | Der Brunnen | Wasser gibt es in unserem Dorf nur am Brunnen. Kein Haus hat einen Wasserhahn. Mein Cousin in der Stadt hat zu Hause einen Wasserhahn. |
| 2 | Der Weg ins Nachbardorf (beim Mädchen mit dem Kanister auf dem Kopf, Richtung Sonnenaufgang) | Bei uns fahren keine Schulbusse. Und die Eltern haben keine Zeit, ihre Kinder zur Schule zu fahren. Sie müssen arbeiten. |
| 3 | Die Feuerstelle | Die meisten Familien kochen mit Holz und Feuer, weil Holz am günstigsten ist. Man kann es sogar selbst sammeln. |
| 4 | Die Kakaobäume | Mit Kakaobohnen verdient man nicht viel Geld. Deshalb kann meine Familie keine Helfer bezahlen. |

Haben die Kinder alle vier Stationen besucht, erscheint die Frage „Was ist in diesem Dorf anders als bei dir?“.

## Ton

- **Sprachaufnahmen:** `assets/audio/station-*.mp3`, erzeugt mit der Sprachsynthese-Stimme
  `de-DE-KatjaNeural` (eine erwachsene Frauenstimme). Texte und Einstellungen stehen in
  `assets/audio/manifest.json`. Nach einer Textänderung neu erzeugen mit:
  `pip install edge-tts` und dann `python3 tools/generate-audio.py --force`.
  Eigene Aufnahmen können die MP3-Dateien einfach unter demselben Namen ersetzen.
- **Dorfgeräusche:** werden im Browser erzeugt (keine Dateien): Wind in den Blättern, Vögel,
  Tauben, Zikaden, gackernde Hühner, Wasser und Quietschen der Brunnenpumpe, knisterndes Feuer,
  entferntes Hämmern. Die Geräusche kommen aus der passenden Richtung: Schaut man zum Brunnen,
  hört man das Wasser lauter. Während eine Aufnahme läuft, werden sie leiser. Ein- und Ausschalten
  geht mit dem Lautsprecher-Knopf oben rechts.

## Technik

- Eine einzige Seite `index.html` ohne Bibliotheken; das Panorama wird mit WebGL dargestellt.
- Panorama: `assets/dorf-360.webp` (3548 × 1774, equirektangular, nahtlos). Es ist das
  2× hochskalierte Originalbild `assets/dorf-360-original.webp` (1774 × 887).
  Hochskaliert wurde mit Real-ESRGAN (Modell `RealESRGAN_x4plus`, Ergebnis auf 2× verkleinert),
  links und rechts umlaufend aufgefüllt, damit die 360°-Naht erhalten bleibt. Das Skript liegt in
  `tools/upscale-panorama.py` (benötigt `pip install spandrel` und die Modelldatei von den
  Real-ESRGAN-Releases auf GitHub). Das Verfahren schärft Kanten und Strukturen, erfindet aber
  keine neuen Details: Gesichter und Pflanzen werden nicht fotorealistischer.
- Positionen der Stationen, des Wegweisers und der Geräuschquellen stehen oben im Skript
  (`STATIONS`, `SRC`) als [Länge, Breite] in Grad.
- Bedienung: Ziehen (Finger/Maus), Pfeiltasten, Zoomen mit zwei Fingern, dem Mausrad oder +/−.
- Läuft auf iPad, Tablet, Handy und Computer.

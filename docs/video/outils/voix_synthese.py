"""Les 8 voix de la vidéo en SYNTHÈSE NEURONALE hors ligne → docs/video/voix-synthese/01.m4a … 08.m4a.

Moteur : Piper (VITS), voix française « siwis » qualité medium, exécutée par sherpa-onnx (hors ligne, gratuit).
Choix comparé le 04.10 sur la séquence 01 entre trois voix féminines : siwis-medium, upmc-medium (« jessica ») et
siwis-low ; voir docs/video/voix-synthese/CHOIX_DE_LA_VOIX.md.

    pip install sherpa-onnx soundfile numpy
    python3 docs/video/outils/voix_synthese.py [--modeles DOSSIER] [--vitesse 0.88] [--seulement 01,04]
    python3 docs/video/outils/voix_synthese.py --mac "Audrey (Premium)"      # plan B : la voix Premium de macOS

Rendu : débit 0,88 (0,95 donnait une vidéo trop courte) ; une vraie pause à chaque « / » ; une respiration entre les phrases. La prononciation est corrigée
par une graphie phonétique dans le texte ENVOYÉ AU MOTEUR seulement (jamais dans le script ni les sous-titres).

Licences : voix siwis — données SIWIS (Université d'Édimbourg), CC BY 4.0 ; modèle Piper converti par sherpa-onnx."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
VIDEO = ICI.parent
SORTIE = VIDEO / "voix-synthese"
sys.path.insert(0, str(ICI))
import video  # noqa: E402

VOIX = "vits-piper-fr_FR-siwis-medium"
URL = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/{VOIX}.tar.bz2"
VITESSE = 0.88        # plus posé que 0,95 : la vidéo doit durer 10 à 12 minutes (0,95 donnait 9 min 26 s)
PAUSE = 0.8           # « / » : une vraie pause
RESPIRATION = 0.5     # entre deux phrases
LIGNE = 0.9           # entre deux lignes du script

# Graphie phonétique, pour le moteur seulement. Vérifié phonème par phonème (espeak-ng, la même base que Piper).
PHONETIQUE = [
    (r"\bApertus\b", "Apertusse"),          # a-pèr-tusse (sinon « a-pèr-tu »)
    (r"\bClub Pulse\b", "Club Peulse"),     # peulse (sinon « pulse » à la française, « u »)
    (r"\bAnnecy\b", "Anne-ci"),             # sinon lu à l'anglaise
    (r"\bl'IA\b", "l'i a"),                 # i-a (sinon « ya »)
    (r"\bIA\b", "i a"),
]


def pour_le_moteur(texte: str) -> str:
    for motif, remplace in PHONETIQUE:
        texte = re.sub(motif, remplace, texte)
    return texte


def morceaux(seq: dict) -> list[tuple[str, float]]:
    """(texte, silence après) : chaque « / » donne une pause, chaque fin de phrase une respiration."""
    sortie = []
    for k, ligne in enumerate(seq["phrases"]):
        parts = [p.strip() for p in ligne.split("/") if p.strip()]
        for j, part in enumerate(parts):
            phrases = [p for p in re.split(r"(?<=[.?!])\s+", part) if p]
            for i, ph in enumerate(phrases):
                fin_part = i == len(phrases) - 1
                if not fin_part:
                    pause = RESPIRATION
                elif j < len(parts) - 1:
                    pause = PAUSE
                else:
                    pause = LIGNE if k < len(seq["phrases"]) - 1 else 0.0
                sortie.append((pour_le_moteur(ph), pause))
    return sortie


def modeles(dossier: Path) -> Path:
    d = dossier / VOIX
    if not (d / "tokens.txt").exists():
        dossier.mkdir(parents=True, exist_ok=True)
        archive = dossier / f"{VOIX}.tar.bz2"
        print(f"  téléchargement de la voix ({URL}) …")
        urllib.request.urlretrieve(URL, archive)
        with tarfile.open(archive) as t:
            t.extractall(dossier)
        archive.unlink()
    return d


def generer(dossier_modeles: Path, vitesse: float, seulement: set[str] | None) -> list[Path]:
    import numpy as np
    import sherpa_onnx
    import soundfile as sf
    d = modeles(dossier_modeles)
    onnx = next(d.glob("*.onnx"))
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=str(onnx), tokens=str(d / "tokens.txt"),
                                                   data_dir=str(d / "espeak-ng-data")), num_threads=4)))
    SORTIE.mkdir(parents=True, exist_ok=True)
    faits = []
    for s in video.lire_script():
        if seulement and s["num"] not in seulement:
            continue
        bouts, sr = [], 22050
        for texte, pause in morceaux(s):
            a = tts.generate(texte, sid=0, speed=vitesse)
            sr = a.sample_rate
            x = np.asarray(a.samples, dtype=np.float32)
            nz = np.nonzero(np.abs(x) > 0.01)[0]                    # le moteur ajoute un peu de blanc : on le règle nous-mêmes
            if len(nz):
                x = x[max(0, nz[0] - int(0.03 * sr)): nz[-1] + int(0.08 * sr)]
            bouts += [x, np.zeros(int(pause * sr), dtype=np.float32)]
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "v.wav"
            sf.write(wav, np.concatenate(bouts), sr)
            m4a = SORTIE / f"{s['num']}.m4a"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav), "-c:a", "aac", "-b:a", "128k",
                            "-ar", "44100", str(m4a)], check=True)
        faits.append(m4a)
        print(f"  {m4a.name} · {sum(len(b) for b in bouts) / sr:.1f} s")
    return faits


def generer_mac(nom_voix: str, mots_par_minute: int, seulement: set[str] | None) -> list[Path]:
    """PLAN B, sur le Mac : la voix française « Premium » de macOS (commande say), mêmes pauses, même graphie."""
    SORTIE.mkdir(parents=True, exist_ok=True)
    faits = []
    for s in video.lire_script():
        if seulement and s["num"] not in seulement:
            continue
        texte = " ".join(f"{t} [[slnc {int(p * 1000)}]]" for t, p in morceaux(s))
        with tempfile.TemporaryDirectory() as td:
            aiff = Path(td) / "v.aiff"
            subprocess.run(["say", "-v", nom_voix, "-r", str(mots_par_minute), "-o", str(aiff), texte], check=True)
            m4a = SORTIE / f"{s['num']}.m4a"
            subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "128000", str(aiff), str(m4a)], check=True)
        faits.append(m4a)
        print(f"  {m4a.name}")
    return faits


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--modeles", type=Path, default=Path.home() / ".cache" / "clubpulse-voix")
    p.add_argument("--vitesse", type=float, default=VITESSE)
    p.add_argument("--seulement", default="")
    p.add_argument("--mac", metavar="VOIX", help="plan B sur le Mac : say -v VOIX, par exemple « Audrey (Premium) »")
    p.add_argument("--mots-par-minute", type=int, default=165)
    a = p.parse_args(argv)
    seulement = {x.strip() for x in a.seulement.split(",") if x.strip()} or None
    if a.mac:
        generer_mac(a.mac, a.mots_par_minute, seulement)
    else:
        generer(a.modeles, a.vitesse, seulement)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

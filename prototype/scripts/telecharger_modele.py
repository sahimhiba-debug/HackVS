"""Télécharge le modèle d'embeddings local (multilingual-e5-large, ONNX, ~2,2 Go) dans var/modeles/.

Source : miroir public fastembed (Google Cloud Storage), accessible même quand Hugging Face est filtré.
Aucune clé, aucun compte, aucune donnée envoyée. Le modèle tourne ensuite hors ligne (onnxruntime, CPU).
Intégrité : empreintes SHA-256 vérifiées après extraction (valeurs relevées le 2026-09-28).

Usage : python scripts/telecharger_modele.py [--forcer]
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "var" / "modeles"
NOM = "fast-multilingual-e5-large"
URL = f"https://storage.googleapis.com/qdrant-fastembed/{NOM}.tar.gz"
SHA256 = {
    "model.onnx": "1c09780c907c8a91a77a6ab1fd231f79e090d2907ca431223703dfebeed3d36c",
    "tokenizer.json": "f59925fcb90c92b894cb93e51bb9b4a6105c5c249fe54ce1c704420ac39b81af",
}


def empreinte(f: Path) -> str:
    h = hashlib.sha256()
    with f.open("rb") as fh:
        for bloc in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--forcer", action="store_true", help="retélécharger même si le modèle est présent")
    a = ap.parse_args()
    cible = DOSSIER / NOM
    if (cible / "model.onnx").exists() and not a.forcer:
        print(f"Déjà présent : {cible}")
        return 0
    DOSSIER.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=DOSSIER) as tmp:
        archive = Path(tmp) / "modele.tar.gz"
        print(f"Téléchargement {URL} (≈ 2 Go)…")
        with urllib.request.urlopen(URL) as r, archive.open("wb") as out:
            shutil.copyfileobj(r, out, 1 << 20)
        with tarfile.open(archive) as t:
            membres = [m for m in t.getmembers() if m.isfile() and not Path(m.name).name.startswith("._")]
            for m in membres:
                if Path(m.name).parts[0] != NOM or ".." in Path(m.name).parts:
                    raise SystemExit(f"Archive inattendue : {m.name}")
            t.extractall(tmp, members=membres, filter="data")
        for fichier, attendu in SHA256.items():
            if empreinte(Path(tmp) / NOM / fichier) != attendu:
                raise SystemExit(f"Empreinte SHA-256 incorrecte pour {fichier} : modèle refusé.")
        if cible.exists():
            shutil.rmtree(cible)
        shutil.move(str(Path(tmp) / NOM), cible)
    print(f"Modèle installé et vérifié : {cible}")
    print("Ensuite : python scripts/calibrer_semantique.py (seuils) puis relancer le serveur.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

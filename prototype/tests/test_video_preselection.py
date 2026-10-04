"""La VIDÉO DE PRÉSÉLECTION (docs/video/) : un jury non technique, à huis clos, sans nous.

Le script tient en 8 séquences et 10 à 12 minutes film compris, ne dit aucun mot technique, ne suppose aucun public
présent, garde les chiffres de PREUVES et la phrase finale ; chaque image citée existe en 1920 × 1080 ; les sous-titres
se calent sur la voix ; monter.sh reste compatible avec le bash 3.2 de macOS."""
import importlib.util
import re
import shutil
import subprocess
from pathlib import Path

import pytest

VIDEO = Path(__file__).resolve().parents[2] / "docs" / "video"
_spec = importlib.util.spec_from_file_location("video_outils", VIDEO / "outils" / "video.py")
video = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(video)

FILM = 201                                                # le film : 3 min 21 s (05_FILM_INTEGRATION.md)
SEQS = video.lire_script()
DIT = " ".join(video.propre(p) for s in SEQS for p in s["phrases"])


def test_huit_sequences_numerotees_avec_leurs_images():
    assert [s["num"] for s in SEQS] == ["01", "02", "03", "04", "05", "06", "07", "08"]
    assert [s["titre"] for s in SEQS][2] == "Le film"
    assert all(s["phrases"] and s["images"] for s in SEQS)
    assert [i["nom"] for i in SEQS[2]["images"]].count("FILM") == 1


def test_la_duree_visee_tient_entre_10_et_12_minutes_film_compris():
    total = sum(s["cible"] for s in SEQS) + FILM
    assert 600 <= total <= 720, total
    mots = len(DIT.split())                               # lu posément (2 à 2,4 mots/s) : la voix tombe dans la fourchette
    assert 600 <= mots / 2.4 + FILM + 8 * 1.4 and mots / 2.0 + FILM + 8 * 1.4 <= 720, mots


def test_le_detecteur_attrape_le_jargon():
    assert video.mots_interdits(["On l'a testé sur notre serveur, via le tunnel, puis l'API JSON du CSCS."])
    assert video.mots_interdits(["Scannez le QR code."])
    assert video.mots_interdits(["Sur 26 tests, une fois."])
    assert not video.mots_interdits(["Une fois sur 26. Avec ou sans IA, le Club marche pareil."])


def test_aucun_mot_interdit_ni_public_suppose():
    assert video.mots_interdits([video.propre(p) for s in SEQS for p in s["phrases"]]) == []
    for absent in ("Levez la main", "Sortez vos téléphones", "scannez", "http", "127.0.0.1"):
        assert absent.lower() not in DIT.lower(), absent
    assert "Imaginez une salle" in DIT


def test_les_chiffres_de_preuves_et_la_phrase_finale():
    for chiffre in ("145 entreprises", "173 représentants", "huit sur neuf", "21 vraies demandes", "Une fois sur 26",
                    "24 demandes ont reçu 114 offres", "80 téléphones", "45 jours", "50 membres"):
        assert chiffre in DIT, chiffre
    assert "La Foire crée la rencontre. Club Pulse crée l'après. Si Jean-Marc dit oui, c'est que c'est oui." in DIT
    assert "Hier, Émilie nous a dit" in DIT and "ce matin" not in DIT.lower()


def test_chaque_image_citee_existe_en_1920x1080():
    noms = {i["nom"] for s in SEQS for i in s["images"]} - {"FILM"}
    manquantes = [n for n in noms if not (VIDEO / "images" / n).exists()]
    assert manquantes == []
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        pytest.skip("ffprobe absent : tailles non vérifiées")
    for n in sorted(noms):
        r = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height",
                            "-of", "csv=p=0", str(VIDEO / "images" / n)], capture_output=True, text=True)
        assert r.stdout.strip() == "h264,1920,1080", (n, r.stdout)


def test_les_sous_titres_suivent_la_voix_et_restent_lisibles(tmp_path):
    cartons = []
    t = 0.0
    for s in SEQS:
        cartons += video.cartons_sequence(s, t + 0.6, 40.0)
        t += 41.4
    assert all(a < b for a, b, _ in cartons)
    assert all(cartons[k][1] <= cartons[k + 1][0] for k in range(len(cartons) - 1))
    for _, _, c in cartons:
        lignes = c.split("\n")
        assert len(lignes) <= 2 and max(len(x) for x in lignes) <= 52, c
    srt = tmp_path / "x.srt"
    video.ecrire_srt(cartons, srt)
    assert re.match(r"1\n00:00:00,600 --> 00:00:0\d,\d{3}\n", srt.read_text(encoding="utf-8"))
    assert video.mots_interdits([c for _, _, c in cartons]) == []


def test_monter_sh_bash_32_et_conda():
    sh = (VIDEO / "monter.sh").read_text(encoding="utf-8")
    assert sh.startswith("#!/bin/bash")
    for bash4 in ("declare -A", "mapfile", "readarray", ",,}", "^^}", "&>>", "coproc", "${!"):
        assert bash4 not in sh, bash4
    assert "conda install -y -c conda-forge ffmpeg" in sh
    assert subprocess.run(["bash", "-n", str(VIDEO / "monter.sh")]).returncode == 0
    assert (VIDEO / "monter.sh").stat().st_mode & 0o111


def test_prompteur_et_resume_sans_rien_d_exterieur():
    page = video.prompteur().read_text(encoding="utf-8")
    assert page.count("<section") == 8 and "08.m4a" in page
    resume = video.resume().read_text(encoding="utf-8")
    for p in (page, resume):
        assert not re.search(r"""(src|href)=["']?https?:""", p)
    for titre in ("Le problème", "La solution", "Ce qu'y gagne le Club", "La demande", "L'équipe"):
        assert titre in resume, titre

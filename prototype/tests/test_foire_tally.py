"""FOIRE 2026 · H — PIPELINE TALLY + TAXONOMIE + HARNAIS, avec les règles de l'équipe (03.10) :
1. langue RÉELLE de chaque phrase, pas la page choisie ; 2. colonne `domaine` (club | hors_club) à remplir à la main,
les hors_club restent comme tests d'abstention ; 3. CONSENTEMENT : les phrases de la Foire ne passent QUE par Apertus,
jamais par un modèle frontière ; 4. aucune phrase individuelle publiée : agrégats seulement. Données FICTIVES."""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from eval import classification_metiers as cm
from intelligence import metiers

PROTO = Path(__file__).resolve().parents[1]
ENV = {"PATH": "/usr/bin:/bin", "HOME": "/tmp"}


def test_taxonomie_une_vingtaine_de_metiers_fr_de():
    ms = metiers.metiers()
    assert 18 <= len(ms) <= 25 and all(m["fr"] and m["de"] for m in ms)
    for attendu in ("transport", "salle", "hebergement", "traiteur", "interprete", "juridique", "comptabilite", "informatique",
                    "communication", "impression", "evenementiel", "construction", "agriculture", "logistique", "rh",
                    "formation", "finance", "immobilier", "energie", "sante", "autre"):
        assert attendu in metiers.ids()


@pytest.mark.parametrize("texte,langue", [
    ("Nous cherchons un transporteur pour la Foire avec un minibus.", "fr"),
    ("Wir suchen einen Dolmetscher für unsere Kunden aus Zürich.", "de"),
    ("We are looking for someone who can help with the logistics of our stand.", "en"),   # passée par la page française
    ("Cerchiamo qualcuno per la traduzione del nostro catalogo.", "it"),
    ("???", "inconnue"),
])
def test_langue_reelle_detectee_sur_le_texte(texte, langue):
    assert cm.detecter_langue(texte) == langue


def test_motifs_de_contact_detectes():
    assert cm.contient_contact("écrivez à jean.dupont@exemple.ch")
    assert cm.contient_contact("appelez le 079 123 45 67") and cm.contient_contact("+41 79 123 45 67")
    assert not cm.contient_contact("un minibus de 14 places le 09.10 entre 13h30 et 15h")


@pytest.mark.parametrize("fournisseur", ["openai", "claude"])
def test_consentement_les_phrases_de_la_foire_jamais_vers_un_modele_frontiere(fournisseur):
    with pytest.raises(PermissionError):
        cm.verifier_fournisseur(cm.SOURCE_FOIRE, fournisseur)
    cm.verifier_fournisseur(cm.SOURCE_FOIRE, "apertus")
    cm.verifier_fournisseur("cas-26", fournisseur)                   # les 26 cas et le synthétique : la comparaison reste possible


def test_validation_contrainte_abstention_permise_le_reste_rejete():
    assert cm.valider('{"metier": "transport", "abstention": false}') == ({"metier": "transport", "abstention": False}, None)
    assert cm.valider('{"metier": null, "abstention": true}') == ({"metier": None, "abstention": True}, None)
    assert cm.valider('{"metier": "astrologie", "abstention": false}')[1] == "métier hors taxonomie"
    assert cm.valider('{"metier": "transport", "abstention": true}')[1] == "abstention avec métier"
    assert cm.valider('{"metier": "transport", "abstention": false, "nom": "x"}')[1] == "hors schéma"
    assert cm.valider("pas du JSON")[1] == "JSON illisible"


def _csv(tmp_path):
    f = tmp_path / "tally.csv"
    with f.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(["Submission ID", "Submitted at", "Langue / Sprache / Language", "Un coup de main ? (FR)",
                    "Hilfe gesucht? (DE)", "Need a hand? (EN)"])
        w.writerow(["a", "2026-10-03 10:00:00", "Français", "Nous cherchons un traiteur pour 40 personnes.", "", ""])
        w.writerow(["b", "2026-10-03 10:05:00", "Français", "We are looking for someone who can help with our stand logistics.", "", ""])
        w.writerow(["c", "2026-10-03 10:06:00", "Deutsch", "", "Wir suchen einen Dolmetscher für Kunden.", ""])
        w.writerow(["d", "2026-10-03 10:07:00", "Français", "Nous cherchons un traiteur pour 40 personnes !", "", ""])   # doublon
        w.writerow(["e", "2026-10-03 10:08:00", "Français", "Appelez-moi au 079 123 45 67 pour un stand.", "", ""])       # contact
        w.writerow(["f", "2026-10-03 10:09:00", "Français", "", "", ""])                                                   # vide
    return f


def test_ingest_tally_colonnes_fusion_doublons_contacts(tmp_path):
    sortie = tmp_path / "phrases.jsonl"
    r = subprocess.run([sys.executable, "scripts/ingest_tally.py", "--csv", str(_csv(tmp_path)), "--sortie", str(sortie)],
                       cwd=PROTO, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr
    lignes = [json.loads(x) for x in sortie.read_text(encoding="utf-8").splitlines()]
    assert len(lignes) == 3
    assert {x["langue"] for x in lignes} == {"fr", "en", "de"}                 # « en » malgré la page française
    assert all(x["source"] == "foire-2026-qr" and x["date"] == "2026-10-03" for x in lignes)
    assert not any(cm.contient_contact(x["texte"]) for x in lignes)
    assert "Dolmetscher" not in r.stdout and "traiteur" not in r.stdout       # la console n'affiche que des agrégats
    assert "écartées (contact)" in r.stdout and "doublons" in r.stdout


def test_ingest_sans_csv_tourne_proprement(tmp_path):
    r = subprocess.run([sys.executable, "scripts/ingest_tally.py", "--csv", str(tmp_path / "absent.csv"), "--sortie",
                        str(tmp_path / "p.jsonl")], cwd=PROTO, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0 and "absent" in r.stdout and not (tmp_path / "p.jsonl").exists()


def test_eval_classification_factice_sur_les_26_cas_et_feuille_d_annotation(tmp_path):
    r = subprocess.run([sys.executable, "scripts/eval_classification.py", "--fournisseur", "factice", "--phrases", str(tmp_path / "absent.jsonl"),
                        "--rapport", str(tmp_path / "r.md"), "--feuille", str(tmp_path / "f.csv")],
                       cwd=PROTO, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr
    rapport = (tmp_path / "r.md").read_text(encoding="utf-8")
    assert "cas-26" in rapport and "| Phrases | 26 |" in rapport and "Aucune exactitude n'est revendiquée" in rapport
    cas = json.loads((PROTO / "eval" / "cas_comprendre_action.json").read_text(encoding="utf-8"))["cas"]
    assert not any(c["texte"] in rapport for c in cas)                        # agrégats seulement
    with (tmp_path / "f.csv").open(encoding="utf-8") as h:
        feuille = list(csv.DictReader(h))
    assert len(feuille) == 26 and {"metier_humain", "domaine"} <= set(feuille[0]) and feuille[0]["domaine"] == ""


def test_eval_classification_refuse_un_modele_frontiere_sur_les_phrases_de_la_foire(tmp_path):
    p = tmp_path / "phrases.jsonl"
    p.write_text(json.dumps({"texte": "Nous cherchons un traiteur.", "langue": "fr", "date": "2026-10-03", "source": "foire-2026-qr"}) + "\n",
                 encoding="utf-8")
    r = subprocess.run([sys.executable, "scripts/eval_classification.py", "--fournisseur", "openai", "--phrases", str(p),
                        "--rapport", str(tmp_path / "r.md"), "--feuille", str(tmp_path / "f.csv")],
                       cwd=PROTO, capture_output=True, text=True, env=ENV | {"OPENAI_API_KEY": "x", "OPENAI_MODEL": "x"})
    assert r.returncode != 0 and "consentement" in (r.stderr + r.stdout) and not (tmp_path / "r.md").exists()


def test_langues_des_26_cas_detectees_justes():
    """Mesure sur les 26 cas existants : 22 fr, c07 / c08 de (dont suisse allemand), c09 it, c10 en."""
    cas = json.loads((PROTO / "eval" / "cas_comprendre_action.json").read_text(encoding="utf-8"))["cas"]
    attendu = {"c07": "de", "c08": "de", "c09": "it", "c10": "en"}
    assert {c["id"]: cm.detecter_langue(c["texte"]) for c in cas} == {c["id"]: attendu.get(c["id"], "fr") for c in cas}

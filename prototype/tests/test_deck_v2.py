"""DECK v2 (docs/presentation/deck/v2.html) — chaque chiffre affiché vient d'une source du dépôt, et rien d'interdit
n'y est écrit. Les chiffres sont dans data/gel.json (bloc « v2 ») ; ce test les recalcule depuis le code et les fichiers."""
import json
import re
from collections import Counter
from pathlib import Path

from intelligence import assembler, club_cherche, feuille_de_route

RACINE = Path(__file__).resolve().parents[2]
DECK = RACINE / "docs" / "presentation" / "deck"
V2 = json.loads((DECK / "data" / "gel.json").read_text(encoding="utf-8"))["v2"]
HTML = (DECK / "v2.html").read_text(encoding="utf-8")
PREUVES = (RACINE / "docs" / "audit" / "club-pulse-pivot" / "PREUVES.md").read_text(encoding="utf-8")


def test_chiffres_du_club_viennent_de_la_liste():
    liste = club_cherche.entreprises_par_metier()
    a = assembler.calculer(liste["par_metier"])
    assert V2["club"]["entreprises"] == str(liste["lignes"]) == "145"
    assert V2["club"]["representants"] == str(assembler.REPRESENTANTS)
    assert (V2["club"]["assemblables"], V2["club"]["capacites"]) == (str(a["assemblables"]), str(a["total"]))
    assert V2["club"]["manque"] == next(x for x in a["capacites"] if not x["assemblable"])["manque"][0]


def test_statuts_de_la_feuille_de_route_viennent_d_etat_yaml():
    n = Counter(e["statut"] for e in feuille_de_route.charger())
    assert V2["etat"] == {"construit": str(n["construit"]), "valide": str(n["valide"]), "prevu": str(n["prevu"])}


def test_chiffres_mesures_sont_dans_preuves():
    assert "80, en parallèle" in PREUVES and "**0**" in PREUVES and "208,4" in PREUVES          # p95 ≤ 210 ms
    assert V2["charge"]["cible"].startswith("serveur local")
    assert "21 réponses" in PREUVES and V2["tally"]["reponses"] == "21"
    assert "1/26 modèle juste" in PREUVES and (V2["ia"]["justes"], V2["ia"]["cas"]) == ("1", "26")
    assert "CSCS" in V2["ia"]["source"]


def test_rien_d_interdit_dans_le_deck():
    texte = re.sub(r"<[^>]+>", " ", HTML)
    assert "Public AI" not in texte                                 # Apertus 1.5 est servi par le CSCS
    assert "certifié" not in texte
    assert texte.count("validé sur le terrain") == 1                # le seul libellé du statut, compté depuis etat.yaml
    assert "cinquantaine" not in texte
    assert "nouveaux liens tissés" in texte                         # construit (test_liens.py) : il peut être dit
    assert "Un pilote de 45 jours avec 50 membres volontaires parmi vos 173 représentants." in texte
    assert "La Foire crée la rencontre." in texte                   # la phrase finale, identique au v1


def test_qr_en_direct_jamais_fige_et_carte_conditionnelle():
    assert 'data-chemin="/qr/salle.svg"' in HTML and "data:image/svg+xml;base64" not in HTML and "data:image/png" not in HTML
    assert 'data-condition="carte"' in HTML and 'params.get("carte") === "1"' in HTML
    assert "review/constellation/" in HTML                          # plan B : la vidéo de la constellation

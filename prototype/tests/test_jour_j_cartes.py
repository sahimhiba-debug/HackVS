"""Les cartes imprimables du jour J (docs/presentation/outils/cartes.py) ne s'écartent jamais de la source : chaque
libellé de bouton est celui de la régie, chaque repère celui de 02_STRUCTURE_v2 (et du mode R du deck), chaque phrase
par cœur est dans le texte à dire."""
import importlib.util
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
PRES = RACINE / "docs" / "presentation"
_spec = importlib.util.spec_from_file_location("cartes", PRES / "outils" / "cartes.py")
cartes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cartes)


def test_les_boutons_de_la_carte_sont_ceux_de_la_regie():
    regie = (RACINE / "prototype" / "web" / "pulse" / "salle-regie.html").read_text(encoding="utf-8")
    boutons = re.findall(r"<button[^>]*>([^<]+)</button>", regie)
    assert [b for _, b, _ in cartes.BOUTONS] == boutons[:5]


def test_les_reperes_sont_ceux_de_la_structure_et_du_deck():
    structure = (PRES / "02_STRUCTURE_v2.md").read_text(encoding="utf-8")
    deck = (PRES / "deck" / "v2.html").read_text(encoding="utf-8")
    cibles = [int(x) for x in re.findall(r'cible: (\d+), coupe', deck)]
    for (t, repere, coupe), cible in zip(cartes.REPERES, cibles, strict=True):
        assert f"| {repere} | {t} | {coupe} |" in structure, repere
        m, s = t.split(":")
        assert int(m) * 60 + int(s) == cible, (repere, cible)


def test_les_phrases_par_coeur_sont_dans_le_texte_a_dire():
    a_dire = re.sub(r"\s+", " ", (PRES / "03b_SCRIPT_A_DIRE_v2.md").read_text(encoding="utf-8"))
    for p in cartes.PAR_COEUR:
        assert p.split("  (")[0] in a_dire, p


def test_les_cartes_disent_l_adresse_et_la_purge():
    assert cartes.URL_REGIE in cartes.carte_regie() and "2 - Arrêter et effacer" in cartes.carte_regie()
    assert "touche B" in cartes.carte_regie()


def test_chaque_carte_tient_sur_une_page():
    for nom in ("CARTE_REGIE_V2", "CARTE_V1"):
        pdf = (PRES / "livrables" / f"{nom}.pdf").read_bytes()
        assert len(re.findall(rb"/Type\s*/Page(?!s)", pdf)) == 1, nom

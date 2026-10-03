"""P3 n°13 — export du bilan pour le comité : CSV + Markdown, les mêmes chiffres (une seule liste de mesures), agrégats,
aucun nom ; « < 3 » en entreprises."""
import csv
import io

from app.taxonomy import charger_taxonomie
from intelligence import bilan
from intelligence.demo import Demo


def test_csv_et_markdown_disent_les_memes_chiffres(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_SECRET", "un-secret-de-test-assez-long-pour-32-octets!")
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    c = Demo(charger_taxonomie()).club
    lignes = list(csv.reader(io.StringIO(bilan.csv_texte(c, "demo")), delimiter=";"))
    assert lignes[0] == ["mesure", "valeur", "periode", "du", "au", "monde"]
    md = bilan.rediger(c, "demo")
    for mesure, valeur, *_ in lignes[1:]:
        assert f"| {mesure} | {valeur} |" in md
    assert any(l[0] == "Nouveaux liens tissés" for l in lignes) and all(l[5] == "monde de démonstration" for l in lignes[1:])
    noms = [p.nom for p in c.coffre._personnes.values()]
    assert not [n for n in noms if n in bilan.csv_texte(c, "demo")]

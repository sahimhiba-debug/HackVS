"""P3 n°11 — pipeline d'affinage : pondération par la liste du Club, tirage reproductible, filtre aller-retour,
configuration LoRA 8B présente et NON lancée. Aucun appel réseau dans ces tests."""
import json
from collections import Counter
from pathlib import Path

from finetune import donnees_synthetiques as ds


def test_poids_viennent_de_la_liste_sans_autre():
    p = ds.poids()
    assert "autre" not in p and p["construction"] == 18 and p["finance"] == 11


def test_tirage_reproductible_et_proportionne():
    a, b = ds.tirage(2000, 7), ds.tirage(2000, 7)
    assert a == b
    c = Counter(t["metier"] for t in a)
    assert c.most_common(1)[0][0] == "construction"                 # le métier le plus présent du Club
    assert c["construction"] > c["finance"] > c["logistique"]
    assert all(t["capacite"] is None or t["capacite"] in [x[1] for x in ds.assembler.CAPACITES] for t in a)


def test_filtre_aller_retour():
    ok = "Jeudi 8 octobre à 14h, il nous faut 2 électriciens pour rénover un atelier à Martigny."
    assert ds.garder(ok, "construction", lambda t: "construction") == (True, "gardé")
    assert ds.garder(ok, "construction", lambda t: "immobilier")[0] is False
    assert ds.garder("Il nous faut un électricien.", "construction", lambda t: "construction")[1].startswith("pas SMART")
    assert ds.garder(ok + " Écrivez à x@y.ch", "construction", lambda t: "construction")[1] == "contact"


def test_exemple_au_format_messages():
    e = ds.exemple_sft("texte", "finance")
    assert [m["role"] for m in e["messages"]] == ["system", "user", "assistant"]
    assert json.loads(e["messages"][2]["content"]) == {"metier": "finance", "abstention": False}


def test_dry_run_sans_appel(monkeypatch, tmp_path):
    monkeypatch.setattr(ds, "SORTIE", tmp_path)
    assert ds.main(["--n", "12", "--dry-run"]) == 0
    assert len((tmp_path / "consignes.jsonl").read_text(encoding="utf-8").splitlines()) == 12


def test_config_lora_8b_non_lancee():
    t = (Path(ds.__file__).parent / "lora_apertus_8b.yaml").read_text(encoding="utf-8")
    assert "lance: false" in t and "8B" in t and "r: 16" in t

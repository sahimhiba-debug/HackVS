"""ANNÉE 1 · LOT 6 — Les reçus alignés ISO/IEC TS 27560 n'emploient que des termes qui EXISTENT dans le vocabulaire DPV
2.1 (liste des noms extraite du fichier officiel du W3C DPVCG, docs/annee-1/conformite/dpv-2.1-termes.txt). Avant ce
lot, deux termes avaient été choisis sans accès à la spécification : `dpv:hasExpiryTime` et `dpv:hasWithdrawalTime`
n'existent pas. Données FICTIVES."""
import json
import re
from pathlib import Path

PROTO = Path(__file__).resolve().parents[1]
TERMES = {x.strip() for x in (PROTO.parent / "docs" / "annee-1" / "conformite" / "dpv-2.1-termes.txt").read_text(encoding="utf-8").splitlines()
          if x.startswith("dpv:")}


def test_la_liste_des_termes_est_bien_celle_du_dpv():
    assert len(TERMES) > 1000 and {"dpv:ConsentRecord", "dpv:hasConsentStatus", "dpv:ConsentGiven"} <= TERMES


def test_chaque_terme_dpv_du_code_existe():
    source = (PROTO / "intelligence" / "recu_27560.py").read_text(encoding="utf-8")
    employes = set(re.findall(r"dpv:[A-Za-z0-9_-]+", source))
    assert employes and sorted(employes - TERMES) == []


def test_chaque_terme_dpv_d_un_vrai_export_existe(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    from app.taxonomy import charger_taxonomie
    from intelligence import recu_27560
    from intelligence.demo import Demo
    demo = Demo(charger_taxonomie())
    demo.rejouer(9)
    c = demo.club
    vus = set()
    for p in c.r.profils:
        texte = json.dumps(recu_27560.export(c, p.id), ensure_ascii=False)
        vus |= set(re.findall(r"dpv:[A-Za-z0-9_-]+", texte))
    assert vus and sorted(vus - TERMES) == []

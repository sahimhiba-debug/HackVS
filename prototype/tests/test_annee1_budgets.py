"""ANNÉE 1 · LOT 11 — BUDGETS DE PERFORMANCE des pages (docs/annee-1/qualite/budgets.json) : chaque page servie,
chargée par un vrai Chromium, cache vide, tous interrupteurs allumés, reste sous son budget d'octets (non compressés),
de requêtes et de temps de chargement. Les budgets de l'API (p95 sous 500 et 1 000 membres simulés) sont vérifiés par
`scripts/charge_membres.py`, trop long pour la suite (activation au rythme de la limite d'accès)."""
import json
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

BUDGETS = json.loads((Path(__file__).resolve().parents[2] / "docs/annee-1/qualite/budgets.json").read_text(encoding="utf-8"))
PAGES = ("/app", "/console", "/etabli", "/projection", "/suivi", "/salle", "/salle/ecran", "/decouverte", "/reponse",
         "/confidentialite", "/feuille-de-route", "/espace", "/secretariat", "/borne", "/attestation", "/compte",
         "/desinscription")
TOUT_ALLUME = dict(HACKVS_FOIRE="1", HACKVS_COMPTES="1", HACKVS_ESPACE_MEMBRE="1", HACKVS_SECRETARIAT="1",
                   HACKVS_NOTIFICATIONS="1", HACKVS_MULTICLUB="1", HACKVS_FOIRE_ALLUMAGE="1", HACKVS_EID="1",
                   HACKVS_HORS_LIGNE="1")


def test_chaque_page_tient_son_budget(tmp_path):
    from playwright.sync_api import sync_playwright

    from tests.test_e2e_scene import _chromium, serveur
    b_ = BUDGETS["pages"]
    mesures, hors = {}, {}
    with serveur(**TOUT_ALLUME, HACKVS_ESSAIS_DB=str(tmp_path / "j.db")) as base, sync_playwright() as p:
        b = _chromium(p)
        for chemin in PAGES:
            ctx = b.new_context()
            pg = ctx.new_page()
            total = {"requetes": 0, "octets": 0}

            def compter(r, total=total):
                total["requetes"] += 1
                try:
                    total["octets"] += len(r.body())
                except Exception:                     # redirection ou corps indisponible : compté, sans octets
                    pass
            pg.on("response", compter)
            t0 = time.perf_counter()
            pg.goto(base + chemin, wait_until="load")
            charge_ms = (time.perf_counter() - t0) * 1000
            pg.wait_for_timeout(800)                  # les lectures de données lancées au chargement
            mesures[chemin] = total | {"chargement_ms": round(charge_ms)}
            if total["octets"] > b_["octets_max"] or total["requetes"] > b_["requetes_max"] or charge_ms > b_["chargement_ms_max"]:
                hors[chemin] = mesures[chemin]
            ctx.close()
        b.close()
    assert all(m["octets"] > 10_000 for m in mesures.values()), mesures      # contre-preuve : on a bien mesuré quelque chose
    assert not hors, hors


def test_les_budgets_d_api_sont_ecrits_pour_500_et_1000_membres():
    assert set(BUDGETS["api_p95_ms"]) == {"500", "1000"}
    for b in BUDGETS["api_p95_ms"].values():
        assert set(b) == {"lecture_membre", "reponse_demande", "console"} and all(v > 0 for v in b.values())

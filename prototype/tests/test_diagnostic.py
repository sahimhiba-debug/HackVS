"""Diagnostic d'organisation : boucle complète, aucune écriture, ne rien faire quand rien n'est prouvé."""
import json
from datetime import date

from adaptateurs.club import diagnostic as dg
from app.models import Profil
from app.taxonomy import DATA_DIR, charger_taxonomie
from plateforme.memoire import Memoire

TAX = charger_taxonomie()
P = [Profil(**p) for p in json.loads((DATA_DIR / "profils_demo.json").read_text(encoding="utf-8"))["profils"]]


def test_route_boucle_complete_sans_ecriture_et_bornee():
    from fastapi.testclient import TestClient

    from app import main
    c = TestClient(main.app)
    c.post("/api/demo/reinitialiser")
    c.get("/api/reseau/diagnostic")                       # 1er appel : projection du magasin
    avant = main.MEMOIRE.empreinte()
    r = c.get("/api/reseau/diagnostic?k=3&horizon=30")
    assert r.status_code == 200 and main.MEMOIRE.empreinte() == avant
    d = r.json()
    assert set(d) >= {"comprendre", "diagnostiquer", "voir_venir", "agir", "observer", "se_souvenir", "decision"}
    assert d["donnees_fictives"] and "@" not in r.text
    for q in ("k=0", "k=500", "horizon=1", "horizon=365"):
        assert c.get(f"/api/reseau/diagnostic?{q}").status_code == 422, q


def test_ne_rien_faire_quand_rien_n_est_prouve_ni_menace():
    fermes = [p.model_copy(update={"accepte_introductions": False}) for p in P]
    d = dg.diagnostic(Memoire(), fermes, [], TAX, date(2026, 10, 1))
    assert d["decision"] == "NE_RIEN_FAIRE" and d["agir"]["decision"] == "NE_RIEN_FAIRE"
    assert d["diagnostiquer"]["phenomenes"] == [] and "abstention" in d["diagnostiquer"]


def test_phenomenes_tries_par_priorite():
    from eval import reseaux_pathologiques as rp
    from adaptateurs.club import sante
    r = rp.pathologique("VIEILLISSEMENT", 0)
    ph = sante.phenomenes(r["g_hist"], r["g_act"], r["membres"], r["secteurs"], r["sollicitations"])["phenomenes"]
    ordre = sorted((p["phenomene"] for p in ph), key=dg.PRIORITE.index)
    assert ordre[0] == "ISOLEMENT" and ordre[-1] == "VIEILLISSEMENT"

"""Serveur MCP : un vrai client MCP (SDK officiel, transport en mémoire) pilote l'API du Club.

On vérifie que l'assistant IA ne peut RIEN contourner : les règles restent côté API, les actions engageantes
passent par une confirmation humaine (elicitation) et un refus n'envoie rien.
"""
from __future__ import annotations

import asyncio
import json
import os

os.environ.setdefault("HACKVS_DB", ":memory:")
os.environ.setdefault("HACKVS_SEMANTIQUE", "0")

import pytest
from fastapi.testclient import TestClient
from mcp import Client
from mcp import types as t

from app.main import PROFILS, app
from app.mcp_serveur import creer_serveur

http = TestClient(app)
BESOIN = "Je cherche un transporteur frigorifique qui livre Zurich deux fois par semaine, idéalement germanophone."


@pytest.fixture(autouse=True)
def _reinit():
    http.post("/api/demo/reinitialiser")


def _repondeur(accepter: bool, journal: list):
    async def cb(ctx, params: t.ElicitRequestParams):
        journal.append(params.message)
        return t.ElicitResult(action="accept", content={"confirmer": True}) if accepter else t.ElicitResult(action="decline")
    return cb


def appeler(outil: str, args: dict, membre="p00", elicitation=None):
    async def run():
        async with Client(creer_serveur(http, membre), elicitation_callback=elicitation) as c:
            r = await c.call_tool(outil, args)
            texte = "".join(x.text for x in r.content if isinstance(x, t.TextContent))
            if r.is_error:
                return True, texte
            sc = r.structured_content
            if sc is not None:  # sortie structurée : {"result": [...]} pour une liste
                return False, sc["result"] if set(sc) == {"result"} else sc
            return False, json.loads(texte)
    return asyncio.run(run())


def test_outils_exposes_et_annotations():
    async def run():
        async with Client(creer_serveur(http, "p00")) as c:
            return {x.name: x.annotations for x in (await c.list_tools()).tools}
    outils = asyncio.run(run())
    assert set(outils) == {"qui_suis_je", "chercher_membres", "expliquer_correspondance", "bourse", "mes_relations",
                           "publier_besoin", "mettre_en_relation", "repondre", "planifier_soiree"}
    for nom in ("chercher_membres", "bourse", "mes_relations", "qui_suis_je", "expliquer_correspondance", "planifier_soiree"):
        assert outils[nom].read_only_hint is True
    for nom in ("publier_besoin", "mettre_en_relation", "repondre"):
        assert outils[nom].read_only_hint is False


def test_recherche_avec_preuves_verbatim():
    err, r = appeler("chercher_membres", {"besoin": BESOIN})
    assert not err and r["suggestions"] and not r["abstention"]
    par_id = {p.id: p for p in PROFILS}
    for s in r["suggestions"]:
        p = par_id[s["membre_id"]]
        champs = " ".join([o.texte for o in p.offre] + [p.presentation, p.commune] + p.langues + p.zones_service)
        assert all(pr["extrait"] in champs for pr in s["preuves"])


def test_abstention_transmise_telle_quelle():
    err, r = appeler("chercher_membres", {"besoin": "Je cherche un spécialiste en droit maritime international."})
    assert not err and r["abstention"] and not r["suggestions"]


def test_publication_refusee_par_le_membre_rien_n_est_publie():
    vus = []
    err, r = appeler("publier_besoin", {"besoin": BESOIN}, elicitation=_repondeur(False, vus))
    assert err and "annulée" in r and vus and "Transport frigorifique" in vus[0]
    assert http.get("/api/besoins", headers={"X-Membre": "p00"}).json() == []


def test_publication_confirmee_puis_offre_d_aide_confirmee():
    err, r = appeler("publier_besoin", {"besoin": BESOIN}, elicitation=_repondeur(True, []))
    assert not err and r["statut"] == "publie" and "elicitation" in r["confirmation"]
    aidant = appeler("chercher_membres", {"besoin": BESOIN})[1]["suggestions"][0]["membre_id"]
    err, bourse = appeler("bourse", {}, membre=aidant)
    assert not err and any(b["besoin_id"] == r["besoin_id"] for b in bourse)
    vus = []
    err, rel = appeler("mettre_en_relation", {"besoin_id": r["besoin_id"]}, membre=aidant, elicitation=_repondeur(True, vus))
    assert not err and rel["etat"] and "Envoyer ce message" in vus[0]
    err, rels = appeler("mes_relations", {}, membre="p00")
    assert any(x["relation_id"] == rel["relation_id"] and x["je_dois_repondre"] for x in rels)


def test_l_assistant_ne_peut_pas_solliciter_un_membre_non_pertinent():
    r = appeler("publier_besoin", {"besoin": BESOIN}, elicitation=_repondeur(True, []))[1]
    proposes = {s["membre_id"] for s in appeler("chercher_membres", {"besoin": BESOIN})[1]["suggestions"]}
    intrus = next(p.id for p in PROFILS if p.id not in proposes | {"p00"} and p.type == "membre_club" and p.accepte_introductions)
    err, msg = appeler("mettre_en_relation", {"besoin_id": r["besoin_id"], "membre_id": intrus, "message": "Bonjour"},
                       elicitation=_repondeur(True, []))
    assert err and "409" in msg and "ne correspond pas" in msg


def test_besoin_anonyme_reste_anonyme_via_mcp():
    r = appeler("publier_besoin", {"besoin": BESOIN, "anonyme": True}, elicitation=_repondeur(True, []))[1]
    aidant = appeler("chercher_membres", {"besoin": BESOIN})[1]["suggestions"][0]["membre_id"]
    item = next(b for b in appeler("bourse", {}, membre=aidant)[1] if b["besoin_id"] == r["besoin_id"])
    assert item["anonyme"] and item["auteur"] == "Un membre du Club"


def test_besoin_ambigu_non_publie():
    err, msg = appeler("publier_besoin", {"besoin": "Je cherche de l'aide pour la sécurité."},
                       elicitation=_repondeur(True, []))
    assert err and "précisez" in msg


def test_expliquer_pourquoi_et_pourquoi_pas():
    s = appeler("chercher_membres", {"besoin": BESOIN})[1]["suggestions"][0]
    err, e = appeler("expliquer_correspondance", {"besoin": BESOIN, "membre_id": s["membre_id"]})
    assert not err and e["verdict"] == "propose" and any(c["statut"] == "verifie" and c["preuve"] for c in e["criteres"])
    # un membre sans offre de transport : non proposé, raison explicite
    autre = next(p for p in PROFILS if p.type == "membre_club" and p.accepte_introductions and p.disponible
                 and not any(o.concept and "transport" in o.concept for o in p.offre) and p.id != "p00")
    err, e = appeler("expliquer_correspondance", {"besoin": BESOIN, "membre_id": autre.id})
    assert not err and e["verdict"] == "non_propose" and not e["opaque"] and e["resume"].startswith("Non proposé")


def test_expliquer_ne_revele_pas_un_refus_d_introductions():
    http.post("/api/moi/consentement", json={"accepte": False}, headers={"X-Membre": "p01"})
    err, e = appeler("expliquer_correspondance", {"besoin": BESOIN, "membre_id": "p01"})
    assert not err and e["opaque"] and e["criteres"] == [] and "introductions" not in e["resume"]


def test_planifier_soiree_programme_individuel():
    err, r = appeler("planifier_soiree", {"tours": 3})
    assert not err and r["optimum_prouve"] and r["donnees_fictives"]
    qui = r["rencontres"][0]["entre"].split(" et ")[0]
    mid = next(p.id for p in PROFILS if p.nom == qui)
    err, moi = appeler("planifier_soiree", {"tours": 3, "membre_id": mid})
    assert not err and 1 <= len(moi["rencontres"]) <= 3 and all(qui in m["entre"] for m in moi["rencontres"])

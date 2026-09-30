"""Vues du registre (Établi, Passeport, animation) et CACHE de projection. Le cache est une optimisation, jamais une
source : il suit le journal, les profils, l'horloge et les patrons ; ce qu'il rend est une copie. Aucun nom, dans aucun
état. La page /etabli est servie avec sa politique de contenu. Données FICTIVES."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.capacites import Patron
from intelligence.demo import NICOLAS, Demo

TAX = charger_taxonomie()
A = "delegation_acheteurs"
NOMS = ("Pauline", "Darbellay", "Anna", "Zufferey", "Nicolas", "Roduit", "Markus", "Heinzmann", "distillerie", md.PAULINE, md.ANNA, NICOLAS)


@pytest.fixture
def club():
    return Demo(TAX).club


def _statut(c):
    return next(i.statut for i in c.projection_capacites() if i.finalite == A)


def test_le_cache_suit_le_journal_les_profils_l_horloge_et_les_patrons(club):
    assert _statut(club) == "ONE_AWAY"
    club.repondre_ask(md.PAULINE, club.asks_pour(md.PAULINE)[0][1], True, {"places": 14})
    assert _statut(club) == "ACTIVE"                                          # journal
    club.modifier_profil(md.ANNA, disponible=False)
    assert _statut(club) == "DEGRADED"                                        # profil
    club.modifier_profil(md.ANNA, disponible=True)
    assert _statut(club) == "ACTIVE"
    p = club.capacites.patron(A)
    club.capacites.patrons[A] = Patron(**(p.model_dump() | {"version": 2}))
    assert _statut(club) != "ACTIVE"                                          # patron
    club.capacites.patrons[A] = p
    club.avancer(5)
    assert _statut(club) == "EXTINCT"                                         # horloge


def test_le_cache_rend_une_copie(club):
    un = club.projection_capacites()
    un[0].titre = "modifié par un appelant"
    assert club.projection_capacites()[0].titre != "modifié par un appelant"


def test_vue_console_date_attention_et_aucun_nom(club):
    etats = []
    etats.append(club.vues_capacites.console())
    club.repondre_ask(md.PAULINE, club.asks_pour(md.PAULINE)[0][1], True, {"places": 14})
    etats.append(club.vues_capacites.console())
    club.retirer_consentement(md.PAULINE, A)
    v = club.vues_capacites.console()
    etats.append(v)
    titre = "Accueillir une délégation d'acheteurs germanophones"
    assert v["date"] == "2026-10-06" and titre in v["attention"]["bloque"] and titre in v["attention"]["decision"]
    assert v["attention"]["expire"] == ["Présenter un produit valaisan à des acheteurs germanophones (08.10 14:00–18:30)"]   # ≤ 2 jours
    c = next(x for x in v["capacites"] if x["finalite"] == A)
    assert c["jour"] == "2026-10-09" and c["fenetre"] == "09.10 13:00–18:00"
    assert all(p["fournie_par"] in (None, "une personne du Club") for p in c["pieces"])
    texte = json.dumps(etats, ensure_ascii=False)
    for x in NOMS:
        assert x not in texte, x


def test_la_page_etabli_est_servie_avec_sa_politique_de_contenu():
    r = TestClient(app).get("/etabli")
    assert r.status_code == 200 and "script-src 'self' 'sha256-" in r.headers["content-security-policy"]
    assert "innerHTML" not in r.text                                         # le DOM est construit par createTextNode

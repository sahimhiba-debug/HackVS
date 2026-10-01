"""Balayage d'autorisation de CHAQUE route de Club Pulse, énumérée depuis le routeur — pas d'une liste écrite à la main :
une route ajoutée demain sans garde fait échouer ce test.

Pour chaque route :
- PUBLIQUE : seulement `/acces` et `/jure` (activer un compte, activer un passe juré) — toute autre route publique échoue ;
- CONSOLE : sans l'en-tête → 403 ; avec l'en-tête mais depuis une autre machine → 403 ;
- MEMBRE : sans session, session mal formée, signature falsifiée, session EXPIRÉE (bien signée), session d'un compte EFFACÉ
  → 401 ; et la session d'un membre n'ouvre JAMAIS la console.
Contre-épreuve : les mêmes appels, correctement authentifiés, passent la garde (ni 401 ni 403) sur chaque route de lecture.
Données FICTIVES."""
import hashlib
import hmac
import re
import time

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.pulse_api import creer_routeur
from app.taxonomy import charger_taxonomie

TAX = charger_taxonomie()
SECRET = "b" * 8 + "-secret-du-balayage-d-autorisation-fictif"
CONSOLE = {"X-Pulse-Console": "1"}
PUBLIQUES = {("POST", "/api/pulse/acces"), ("POST", "/api/pulse/jure")}
VALEURS = {"n": "1", "index": "0", "etape": "0"}


def _signer(pid: str, exp: int) -> str:
    sig = hmac.new(SECRET.encode(), f"session|{pid}|{exp}".encode(), hashlib.sha256).hexdigest()[:32]
    return f"{pid}.{exp}.{sig}"


@pytest.fixture
def monde(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_SECRET", SECRET)
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    routeur = creer_routeur(TAX)
    app = FastAPI()
    app.include_router(routeur)
    routes = []
    for r in routeur.routes:
        assert isinstance(r, APIRoute)
        noms = {d.call.__name__ for d in r.dependant.dependencies}
        genre = "console" if "console" in noms else "membre" if "membre" in noms else "publique"
        chemin = re.sub(r"\{(\w+)\}", lambda m: VALEURS.get(m.group(1), "x1"), r.path)
        routes += [(m, chemin, genre) for m in sorted(r.methods)]
    return app, routes


def _appel(client, methode, chemin, entetes=None):
    return client.request(methode, chemin, headers=entetes or {}, json={} if methode != "GET" else None).status_code


def test_seules_l_activation_et_le_passe_jure_sont_publiques(monde):
    _, routes = monde
    assert {(m, c) for m, c, g in routes if g == "publique"} == PUBLIQUES
    assert len(routes) > 60                                          # le balayage voit bien toutes les routes


def test_la_console_refuse_sans_en_tete_et_hors_de_cette_machine(monde):
    app, routes = monde
    local, distant = TestClient(app), TestClient(app, client=("10.0.0.5", 40000))
    for m, c, g in routes:
        if g == "console":
            assert _appel(local, m, c) == 403, (m, c)
            assert _appel(distant, m, c, CONSOLE) == 403, (m, c)


def test_chaque_route_membre_refuse_toute_session_non_valide(monde):
    app, routes = monde
    client = TestClient(app)
    codes = {p["id"]: p["code"] for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    valide = client.post("/api/pulse/acces", json={"code": codes["n01"]}).json()["session"]
    pid, exp, sig = valide.split(".")
    mauvaises = {
        "absente": None,
        "mal formée": "pas-un-jeton",
        "signature falsifiée": f"{pid}.{exp}.{'0' * 32}",
        "expiration repoussée": f"{pid}.{int(exp) + 3600}.{sig}",      # la signature couvre l'expiration
        "expirée (bien signée)": _signer(pid, int(time.time()) - 1),
        "autre membre, même signature": f"s14.{exp}.{sig}",
    }
    for m, c, g in routes:
        if g != "membre":
            continue
        for nom, jeton in mauvaises.items():
            entetes = {} if jeton is None else {"X-Pulse-Session": jeton}
            assert _appel(client, m, c, entetes) == 401, (m, c, nom)


def test_une_session_d_un_compte_efface_ne_rouvre_rien(monde):
    app, routes = monde
    client = TestClient(app)
    code = next(p["code"] for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json() if p["id"] == "n01")
    s = {"X-Pulse-Session": client.post("/api/pulse/acces", json={"code": code}).json()["session"]}
    assert client.post("/api/pulse/moi/effacer", json={"confirme": True}, headers=s).status_code == 200
    for m, c, g in routes:
        if g == "membre":
            assert _appel(client, m, c, s) == 401, (m, c)


def test_la_session_d_un_membre_n_ouvre_jamais_la_console(monde):
    app, routes = monde
    client = TestClient(app, client=("10.0.0.5", 40000))           # un téléphone du point d'accès
    local = TestClient(app)
    code = next(p["code"] for p in local.get("/api/pulse/console/personas", headers=CONSOLE).json() if p["id"] == "n01")
    s = {"X-Pulse-Session": client.post("/api/pulse/acces", json={"code": code}).json()["session"]}
    for m, c, g in routes:
        if g == "console":
            assert _appel(client, m, c, s) == 403, (m, c)
            assert _appel(client, m, c, s | CONSOLE) == 403, (m, c)


def test_contre_epreuve_bien_authentifie_on_passe_la_garde(monde):
    app, routes = monde
    client = TestClient(app)
    code = next(p["code"] for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json() if p["id"] == "n01")
    s = {"X-Pulse-Session": client.post("/api/pulse/acces", json={"code": code}).json()["session"]}
    lectures = [(m, c, g) for m, c, g in routes if m == "GET"]
    assert lectures
    for m, c, g in lectures:
        statut = _appel(client, m, c, CONSOLE if g == "console" else s)
        assert statut not in (401, 403), (m, c, statut)


def _sessions(client):
    ps = client.get("/api/pulse/console/personas", headers=CONSOLE).json()
    return {p["id"]: {"X-Pulse-Session": client.post("/api/pulse/acces", json={"code": p["code"]}).json()["session"]} for p in ps}


def test_un_membre_ne_touche_jamais_les_ressources_d_un_autre(monde):
    """Matrice A → B sur les ressources nommées dans l'URL (offre, note, demande adressée à d'autres)."""
    app, _ = monde
    client = TestClient(app)
    s = _sessions(client)
    a, b = s["s01"], s["n01"]                                   # Pauline (A), Sophie (B)
    oid = client.post("/api/pulse/moi/offres", headers=a, json={"nature": "objet", "quoi": "Un présentoir fictif",
                                                                 "au": "2026-10-10"}).json()["offre"]
    assert client.patch(f"/api/pulse/moi/offres/{oid}", headers=b, json={"capacite": 2}).status_code == 403
    assert client.post(f"/api/pulse/moi/offres/{oid}/retirer", headers=b).status_code == 403
    note = client.post("/api/pulse/moi/notes", headers=a, json={"texte": "Note privée fictive de Pauline"}).json()["id"]
    assert client.post(f"/api/pulse/moi/notes/{note}/partager/0", headers=b).status_code == 404
    assert client.get("/api/pulse/moi/notes", headers=b).json() == []
    ask = client.get("/api/pulse/moi/asks", headers=a).json()[0]["id"]
    assert ask not in [x["id"] for x in client.get("/api/pulse/moi/asks", headers=b).json()]
    assert client.post(f"/api/pulse/moi/asks/{ask}/reponse", headers=b, json={"oui": True, "attributs": {"places": 14}}).status_code == 404
    finalite = ask.split(":", 1)[0]
    assert client.post(f"/api/pulse/moi/capacites/{finalite}/consentement", headers=b).status_code == 404
    assert client.post(f"/api/pulse/moi/capacites/{finalite}/retrait", headers=b).status_code == 404


def test_les_gestes_doubles_ne_s_appliquent_qu_une_fois(monde):
    """Double clic sur le téléphone : la seconde réponse ne réécrit rien, le second retrait est refusé, le second
    consentement ne crée pas de second accord."""
    app, _ = monde
    client = TestClient(app)
    s = _sessions(client)
    p = s["s01"]
    ask = client.get("/api/pulse/moi/asks", headers=p).json()[0]["id"]
    corps = {"oui": True, "attributs": {"places": 14}}
    assert [client.post(f"/api/pulse/moi/asks/{ask}/reponse", headers=p, json=corps).status_code for _ in range(2)] == [200, 404]
    finalite = ask.split(":", 1)[0]
    recus = lambda: [r for r in client.get("/api/pulse/moi/consentements", headers=p).json()]   # noqa: E731
    avant = recus()
    assert client.post(f"/api/pulse/moi/capacites/{finalite}/consentement", headers=p).status_code == 200
    assert recus() == avant                                      # déjà consenti par la réponse : rien de neuf
    assert [client.post(f"/api/pulse/moi/capacites/{finalite}/retrait", headers=p).status_code for _ in range(2)] == [200, 404]


def test_lire_ne_capte_rien_aucune_route_de_lecture_n_ecrit_au_journal(monde, tmp_path):
    """Claim du pitch (D1) : « Lire ne capte rien : aucune écriture sans geste ». CHAQUE route GET servie — téléphone,
    console, Établi, écran commun — est appelée (avec de vrais identifiants quand la route en prend), et le journal
    SQLite est compté AVANT et APRÈS, dans le fichier même : aucune ligne ne doit apparaître."""
    import sqlite3
    app, routes = monde
    client = TestClient(app)
    s = _sessions(client)
    a = s["s01"]
    oid = client.post("/api/pulse/moi/offres", headers=a, json={"nature": "objet", "quoi": "Un présentoir fictif",
                                                                 "au": "2026-10-10"}).json()["offre"]
    eid = client.post("/api/pulse/moi/essais", headers=a, json={"question": "Une question fictive ?",
                                                                 "echeance": "2026-10-09"}).json()["id"]

    def compter() -> int:
        with sqlite3.connect(tmp_path / "journal.db") as db:
            return db.execute("SELECT COUNT(*) FROM evenements").fetchone()[0]
    avant = compter()
    lectures = 0
    for m, c, g in routes:
        if m != "GET":
            continue
        for chemin in {c, c.replace("/x1", f"/{oid}") if "decouvertes" in c else c.replace("/x1", f"/{eid}")}:
            entetes = CONSOLE if g == "console" else a
            client.get(chemin, headers=entetes)
            lectures += 1
    assert lectures >= 20
    assert compter() == avant, f"{compter() - avant} fait(s) écrit(s) par une simple lecture"

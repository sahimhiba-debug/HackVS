"""Balayage d'autorisation de CHAQUE route de Club Pulse, énumérée depuis le routeur — pas d'une liste écrite à la main :
une route ajoutée demain sans garde fait échouer ce test.

Pour chaque route :
- PUBLIQUE : seulement `/acces`, `/jure`, `/decouverte/activer` et `/courriel/lire|repondre` (activer un compte, un
  passe juré, un passe découverte ; lire et utiliser un lien d'e-mail signé) — toute autre route publique échoue ;
- INVITÉ (passe découverte, Foire 2026) : sans en-tête, mal formé, signature falsifiée, passe jamais activé, session de
  membre à la place → 401 ;
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
PUBLIQUES = {("POST", "/api/pulse/acces"), ("POST", "/api/pulse/jure"), ("POST", "/api/pulse/decouverte/activer"),
             ("POST", "/api/pulse/courriel/lire"), ("POST", "/api/pulse/courriel/repondre"),   # liens d'e-mail : signés
             ("POST", "/api/pulse/salle/entrer"),                                                 # QR de la salle : signé
             ("GET", "/api/pulse/monde"), ("GET", "/api/pulse/feuille-de-route")}                 # publics, lecture seule
VALEURS = {"n": "1", "index": "0", "etape": "0"}


def _signer(pid: str, exp: int) -> str:
    sig = hmac.new(SECRET.encode(), f"session|{pid}|{exp}".encode(), hashlib.sha256).hexdigest()[:32]
    return f"{pid}.{exp}.{sig}"


@pytest.fixture
def monde(tmp_path, monkeypatch):
    monkeypatch.setenv("HACKVS_SECRET", SECRET)
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")                           # les routes de la Foire sont balayées allumées
    monkeypatch.setenv("HACKVS_ESPACE_MEMBRE", "1")                   # ANNÉE 1 · lot 3 : l'espace membre aussi
    monkeypatch.setenv("HACKVS_COMPTES", "1")                         # ANNÉE 1 · lot 4 : la console du secrétariat aussi
    monkeypatch.setenv("HACKVS_SECRETARIAT", "1")
    routeur = creer_routeur(TAX)
    app = FastAPI()
    app.include_router(routeur)
    app.state.routeur = routeur
    routes = []
    for r in routeur.routes:
        assert isinstance(r, APIRoute)
        noms = {d.call.__name__ for d in r.dependant.dependencies}
        genre = next((g for g in ("console", "membre", "invite", "participant", "secretariat") if g in noms), "publique")
        chemin = re.sub(r"\{(\w+)\}", lambda m: VALEURS.get(m.group(1), "x1"), r.path)
        routes += [(m, chemin, genre) for m in sorted(r.methods)]
    return app, routes


def _secretariat_eleve(app) -> str:
    """Un compte nominatif du secrétariat, double authentification active, session élevée (ANNÉE 1 · lots 2 et 4)."""
    from intelligence.comptes import code_totp
    cp = app.state.routeur.comptes()
    admin = cp.amorcer_administration("Administration (fictive)")
    pa = cp.preparer_totp(admin)
    cp.confirmer_totp(admin, code_totp(pa["secret"], time.time()))
    cp.elever(admin, code_totp(pa["secret"], time.time() + 30))
    s = cp.accepter(cp.inviter(admin, role="secretariat", etiquette="Secrétariat (fictif)", duree_s=600)["jeton"], appareil="x")
    prep = cp.preparer_totp(s)
    cp.confirmer_totp(s, code_totp(prep["secret"], time.time()))
    cp.elever(s, code_totp(prep["secret"], time.time() + 30))
    return s


def _appel(client, methode, chemin, entetes=None):
    return client.request(methode, chemin, headers=entetes or {}, json={} if methode != "GET" else None).status_code


def test_seules_les_activations_sont_publiques(monde):
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
    assert lectures and any(g == "invite" for _, _, g in lectures)
    inv = {"X-Pulse-Invite": _invite(client)}
    client.post("/api/pulse/console/salle/purger", headers=CONSOLE)
    jeton = client.post("/api/pulse/console/salle/ouvrir", headers=CONSOLE).json()["url"].split("#s=", 1)[1]
    part = {"X-Pulse-Salle": client.post("/api/pulse/salle/entrer", json={"jeton": jeton}).json()["passe"]}
    sec = {"X-Pulse-Compte": _secretariat_eleve(app)}
    for m, c, g in lectures:
        statut = _appel(client, m, c, CONSOLE if g == "console" else inv if g == "invite" else part if g == "participant"
                        else sec if g == "secretariat" else s)
        assert statut not in (401, 403), (m, c, statut)


def _invite(client):
    jeton = client.post("/api/pulse/console/decouverte", headers=CONSOLE, json={"origine": "stand"}).json()["jeton"]
    return client.post("/api/pulse/decouverte/activer", json={"jeton": jeton}).json()["invite"]


def test_chaque_route_invite_refuse_toute_session_non_valide(monde):
    app, routes = monde
    client = TestClient(app)
    valide = _invite(client)
    _, nonce, _ = valide.split(".")
    jamais = client.post("/api/pulse/console/decouverte", headers=CONSOLE, json={"origine": "stand"}).json()["nonce"]
    code = next(p["code"] for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json() if p["id"] == "n01")
    membre = client.post("/api/pulse/acces", json={"code": code}).json()["session"]
    mauvaises = {"absente": None, "mal formée": "pas-un-jeton", "signature falsifiée": f"i1.{nonce}.{'0' * 32}",
                 "passe d'émission au lieu de la session": f"d1.{nonce}.{'0' * 32}",
                 "jamais activé (signature inventée)": f"i1.{jamais}.{'1' * 32}", "session de membre": membre}
    n = 0
    for m, c, g in routes:
        if g != "invite":
            continue
        n += 1
        for nom, jeton in mauvaises.items():
            entetes = {} if jeton is None else {"X-Pulse-Invite": jeton}
            assert _appel(client, m, c, entetes) == 401, (m, c, nom)
    assert n >= 4


def test_chaque_route_participant_refuse_tout_passe_non_valide(monde):
    """MODE SALLE : sans passe, passe falsifié, passe d'une séance purgée, session de membre → 401 partout."""
    app, routes = monde
    client = TestClient(app)
    client.post("/api/pulse/console/salle/purger", headers=CONSOLE)
    jeton = client.post("/api/pulse/console/salle/ouvrir", headers=CONSOLE).json()["url"].split("#s=", 1)[1]
    ancien = client.post("/api/pulse/salle/entrer", json={"jeton": jeton}).json()["passe"]
    client.post("/api/pulse/console/salle/purger", headers=CONSOLE)
    code = next(p["code"] for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json() if p["id"] == "n01")
    membre = client.post("/api/pulse/acces", json={"code": code}).json()["session"]
    _, nonce, exp, _ = ancien.split(".")
    mauvaises = {"absent": None, "mal formé": "pas-un-passe", "signature falsifiée": f"p1.{nonce}.{exp}.{'0' * 32}",
                 "séance purgée": ancien, "session de membre": membre}
    n = 0
    for m, c, g in routes:
        if g != "participant":
            continue
        n += 1
        for nom, jeton in mauvaises.items():
            assert _appel(client, m, c, {} if jeton is None else {"X-Pulse-Salle": jeton}) == 401, (m, c, nom)
    assert n >= 4


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


def test_chaque_route_du_secretariat_exige_un_compte_nominatif_eleve(monde):
    """ANNÉE 1 · lot 4 : ni l'absence de session, ni le jeton « console » de la démo, ni une session de membre, ni une
    session de compte inventée n'ouvrent une route du secrétariat."""
    app, routes = monde
    client = TestClient(app)
    codes = {p["id"]: p["code"] for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    membre = client.post("/api/pulse/acces", json={"code": codes["n01"]}).json()["session"]
    essais = {"aucune": {}, "console démo": CONSOLE, "session de membre": {"X-Pulse-Session": membre},
              "compte inventé": {"X-Pulse-Compte": "abc.9999999999.0000"}}
    vues = [r for r in routes if r[2] == "secretariat"]
    assert len(vues) >= 10
    for m, c, _ in vues:
        for nom, entetes in essais.items():
            assert _appel(client, m, c, entetes) in (401, 403), (m, c, nom)

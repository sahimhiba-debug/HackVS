"""QR JURÉ : passe court, à usage unique, signé ; limitation par CODE et par SESSION, jamais par adresse IP.
Données FICTIVES (le passe ne désigne qu'un personnage du monde de démonstration)."""
import pytest
from fastapi.testclient import TestClient

from intelligence import monde_demo as md
from intelligence.acces import Sessions
from intelligence.erreurs import Conflit, NonAuthentifie
from intelligence.jure import PassesJure

SECRET = b"secret-de-test-du-qr-jure-32-octets!"


class Horloge:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


def test_expiration_nonce_unique_signature():
    h = Horloge()
    p = PassesJure(SECRET, h)
    j1, exp = p.emettre(md.MARKUS, 900)
    j2, _ = p.emettre(md.MARKUS, 900)
    assert j1.split(".")[0] != j2.split(".")[0]                                   # un nonce par passe
    assert p.utiliser(j1) == (md.MARKUS, exp)
    with pytest.raises(Conflit, match="déjà été utilisé"):
        p.utiliser(j1)                                                            # usage unique
    nonce, e, pid, sig = j2.split(".")
    for falsifie in (f"{nonce}.{e}.{md.PAULINE}.{sig}", f"{nonce}.{int(e) + 3600}.{pid}.{sig}", f"{nonce}.{e}.{pid}.{'0' * 32}", "n'importe quoi"):
        with pytest.raises(NonAuthentifie, match="invalide"):
            p.utiliser(falsifie)
    h.t += 901
    with pytest.raises(NonAuthentifie, match="expiré"):
        p.utiliser(j2)


def test_un_passe_d_un_autre_processus_ne_vaut_rien():
    ancien = PassesJure(SECRET)
    j, _ = ancien.emettre(md.MARKUS, 900)
    with pytest.raises(NonAuthentifie, match="inconnu"):                          # même secret, nonce jamais émis ici
        PassesJure(SECRET).utiliser(j)


def test_la_session_du_jure_meurt_avec_le_passe():
    h = Horloge()
    s = Sessions(SECRET, 12 * 3600, h)
    jeton = s.emettre(md.MARKUS, jusqu_a=int(h.t) + 600)
    assert s.verifier(jeton) == md.MARKUS
    h.t += 601
    with pytest.raises(NonAuthentifie, match="expirée"):
        s.verifier(jeton)


# ---------------------------------------------------------------------- par HTTP
CONSOLE = {"X-Pulse-Console": "1"}


@pytest.fixture
def client():
    from app.main import app
    t = TestClient(app)
    t.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    return t


def _passe(t, persona=md.MARKUS):
    r = t.post("/api/pulse/console/jure", json={"persona": persona, "minutes": 15}, headers=CONSOLE)
    assert r.status_code == 200, r.text
    return r.json()


def test_emission_console_seulement_avec_qr_local(client):
    assert client.post("/api/pulse/console/jure", json={"persona": md.MARKUS}).status_code == 403
    p = _passe(client)
    assert p["qr"].startswith("data:image/svg+xml;base64,") and "/app?jure=" in p["url"] and p["minutes"] == 15
    assert "jeton" not in p                                                       # seulement dans l'adresse du QR
    assert client.post("/api/pulse/console/jure", json={"persona": "inconnu"}, headers=CONSOLE).status_code == 404


def test_activation_unique_puis_session_de_personnage(client):
    jeton = _passe(client)["url"].split("jure=", 1)[1]
    r = client.post("/api/pulse/jure", json={"jeton": jeton})
    assert r.status_code == 200 and r.json()["jure"] is True and "FICTIF" in r.json()["regle"]
    h = {"X-Pulse-Session": r.json()["session"]}
    assert client.get("/api/pulse/moi/date", headers=h).status_code == 200
    assert client.post("/api/pulse/jure", json={"jeton": jeton}).status_code == 409          # rescanné : rien


def test_limite_par_code_et_non_par_adresse(client):
    """Cinq essais sur un même code, puis 429 ; un AUTRE code, depuis le même client (même adresse), reste utilisable."""
    j1 = _passe(client)["url"].split("jure=", 1)[1]
    nonce = j1.split(".")[0]
    for _ in range(5):
        assert client.post("/api/pulse/jure", json={"jeton": nonce + ".1.x.faux"}).status_code == 401
    assert client.post("/api/pulse/jure", json={"jeton": j1}).status_code == 429                # ce code est bloqué…
    j2 = _passe(client)["url"].split("jure=", 1)[1]
    assert client.post("/api/pulse/jure", json={"jeton": j2}).status_code == 200                # …pas le client


def test_limite_par_session_de_jure_pas_pour_les_membres(client):
    jeton = _passe(client)["url"].split("jure=", 1)[1]
    h = {"X-Pulse-Session": client.post("/api/pulse/jure", json={"jeton": jeton}).json()["session"]}
    codes = [client.get("/api/pulse/moi/date", headers=h).status_code for _ in range(92)]
    assert codes[:90] == [200] * 90 and codes[90:] == [429, 429]
    membre = {"X-Pulse-Session": next(p for p in client.get("/api/pulse/console/personas", headers=CONSOLE).json()
                                      if p["id"] == md.PAULINE)["session"]}
    assert all(client.get("/api/pulse/moi/date", headers=membre).status_code == 200 for _ in range(95))


def test_l_activation_est_journalisee_attribuable_au_jury():
    from app.taxonomy import charger_taxonomie
    from intelligence.demo import Demo
    from plateforme.affirmations import Statut
    c = Demo(charger_taxonomie()).club
    p = c.emettre_pass_jure(md.MARKUS, 15)
    assert not c.journal.evenements("PASSE_JURE")                                  # émettre n'écrit rien
    r = c.utiliser_pass_jure(p["jeton"])
    e = c.journal.evenements("PASSE_JURE")[-1]
    assert e.acteurs == [md.MARKUS] and e.statut == Statut.OBSERVE and e.donnees["jusqu_a"] == r["jusqu_a"] == p["expire"]

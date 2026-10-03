"""FOIRE 2026 · D — PASSE DÉCOUVERTE : signé, à usage unique à l'émission, 90 jours (horloge du monde), 3 demandes au
plus, révocable, limité en débit, compté dans Suivi (jamais « conversions »), nom d'entreprise jamais sur un écran du
Club. Scénario de démo : le juré devient « exposant invité d'Annecy ». Données FICTIVES."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy import charger_taxonomie
from intelligence.decouverte import DEMANDES_MAX
from intelligence.demo import Demo
from intelligence.erreurs import Conflit, Invalide, Limite, NonAuthentifie

TAX = charger_taxonomie()
CONSOLE = {"X-Pulse-Console": "1"}
client = TestClient(app)


@pytest.fixture
def c(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    return Demo(TAX).club


def _ask(c):
    return next(i.ask.id for i in c.projection_capacites() if i.ask is not None)


def test_emettre_activer_usage_unique(c):
    p = c.decouverte.emettre("stand")
    inv = c.decouverte.activer(p["jeton"])["invite"]
    assert c.decouverte.invite(inv)["nonce"] == p["nonce"]
    with pytest.raises(Conflit):                                       # rescanné : rien
        c.decouverte.activer(p["jeton"])


def test_passe_falsifie_ou_d_un_autre_monde(c, monkeypatch, tmp_path):
    p = c.decouverte.emettre("stand")
    _, nonce, _ = p["jeton"].split(".")
    for faux in ("", "d1.x", f"d1.{nonce}.{'0' * 32}", f"i1.{nonce}.{p['jeton'].split('.')[2]}"):
        with pytest.raises(NonAuthentifie):
            c.decouverte.activer(faux)
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "autre.db"))
    autre = Demo(TAX).club                                             # autre secret de processus ? même processus : autre journal
    with pytest.raises(NonAuthentifie):
        autre.decouverte.activer(p["jeton"])                          # inconnu de ce journal


def test_revoque_tue_la_session_et_l_activation(c):
    p = c.decouverte.emettre("stand")
    inv = c.decouverte.activer(p["jeton"])["invite"]
    c.decouverte.revoquer(p["nonce"])
    with pytest.raises(NonAuthentifie):
        c.decouverte.invite(inv)
    q = c.decouverte.emettre("stand")
    c.decouverte.revoquer(q["nonce"])
    with pytest.raises(NonAuthentifie):
        c.decouverte.activer(q["jeton"])
    with pytest.raises(Conflit):
        c.decouverte.revoquer(q["nonce"])


def test_expire_apres_90_jours_de_l_horloge_du_monde(c):
    p = c.decouverte.emettre("stand")
    inv = c.decouverte.activer(p["jeton"])["invite"]
    c.avancer(60)
    c.avancer(30)
    assert c.decouverte.invite(inv)                                    # le 90e jour vaut encore
    c.avancer(1)
    with pytest.raises(NonAuthentifie):
        c.decouverte.invite(inv)


def test_duree_configurable(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_DECOUVERTE_JOURS", "7")
    c = Demo(TAX).club
    assert c.decouverte.emettre("stand")["jours"] == 7


def test_declaration_recu_et_bornes(c):
    inv = c.decouverte.activer(c.decouverte.emettre("stand")["jeton"])["invite"]
    with pytest.raises(Conflit):
        c.decouverte.repondre(inv, _ask(c), True)                      # déclarer d'abord
    for e, m, z in (("X", "traiteur", "Vaud"), ("Exposant", "astrologie", "Vaud"), ("Exposant", "traiteur", "Lune")):
        with pytest.raises(Invalide):
            c.decouverte.declarer(inv, e, m, z)
    r = c.decouverte.declarer(inv, "Exposant invité d'Annecy", "traiteur", "Haute-Savoie")["recu"]
    assert r["revocable"] and "90 jours" in r["finalite"] and "aucun écran du Club" in r["finalite"]


def test_trois_demandes_au_plus(c):
    inv = c.decouverte.activer(c.decouverte.emettre("stand")["jeton"])["invite"]
    c.decouverte.declarer(inv, "Exposant invité d'Annecy", "traiteur", "Haute-Savoie")
    ask = _ask(c)
    c.decouverte.repondre(inv, ask, True)
    with pytest.raises(Conflit):
        c.decouverte.repondre(inv, ask, True)                          # deux fois la même : non
    p = c.decouverte.invite(inv)
    for i in range(DEMANDES_MAX - 1):                                  # on remplit le quota directement au journal
        c.banc._ecrire("DECOUVERTE_REPONSE", [], None, nonce=p["nonce"], ask=f"fictive-{i}", aide=False)
    with pytest.raises(Limite):
        c.decouverte.repondre(inv, ask, True)
    assert c.decouverte.demandes(inv)["demandes"] == [] and c.decouverte.demandes(inv)["reste"] == 0


def test_passe_lie_a_une_demande_la_montre_d_abord(c):
    ask = _ask(c)
    p = c.decouverte.emettre("demande", ask)
    inv = c.decouverte.activer(p["jeton"])["invite"]
    assert c.decouverte.demandes(inv)["demandes"][0]["id"] == ask
    with pytest.raises(Invalide):
        c.decouverte.emettre("demande", "inconnue:1")


def test_une_proposition_d_invite_ne_remplit_jamais_une_capacite(c):
    avant = {i.finalite: i.statut for i in c.projection_capacites()}
    inv = c.decouverte.activer(c.decouverte.emettre("stand")["jeton"])["invite"]
    c.decouverte.declarer(inv, "Exposant invité d'Annecy", "transport", "Haute-Savoie")
    c.decouverte.repondre(inv, _ask(c), True)
    assert {i.finalite: i.statut for i in c.projection_capacites()} == avant


def test_intention_et_statistiques_k3(c):
    inv = c.decouverte.activer(c.decouverte.emettre("stand")["jeton"])["invite"]
    c.decouverte.declarer(inv, "Exposant invité d'Annecy", "traiteur", "Haute-Savoie")
    c.decouverte.repondre(inv, _ask(c), True)
    r = c.decouverte.rejoindre(inv)
    assert r["simule"] == "simulé en démonstration" and r["prevu_ensuite"]
    s = c.decouverte.statistiques(None, 3)
    assert s == {"actifs": "< 3", "ont_contribue": "< 3", "intentions_adhesion": "< 3", "hors_valais": "< 3", "emis": 1}
    assert c.decouverte.statistiques(None, 1)["ont_contribue"] == 1


def test_redemarrage_rend_les_memes_passes(monkeypatch, tmp_path):
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "j.db"))
    monkeypatch.setenv("HACKVS_SECRET", "s" * 40)
    c = Demo(TAX).club
    p = c.decouverte.emettre("stand")
    inv = c.decouverte.activer(p["jeton"])["invite"]
    c.journal.fermer()
    c2 = Demo(TAX, reprendre=True).club
    assert c2.decouverte.invite(inv)["nonce"] == p["nonce"]
    with pytest.raises(Conflit):
        c2.decouverte.activer(p["jeton"])


# ------------------------------------------------------------------ par HTTP
@pytest.fixture
def http(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "1")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    yield
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)


def test_parcours_du_jure_exposant_invite_d_annecy(http):
    p = client.post("/api/pulse/console/decouverte", headers=CONSOLE, json={"origine": "stand"}).json()
    assert p["qr"].startswith("data:image/svg") or "<svg" in p["qr"]
    assert "/decouverte#passe=" in p["url"]
    inv = {"X-Pulse-Invite": client.post("/api/pulse/decouverte/activer", json={"jeton": p["jeton"]}).json()["invite"]}
    assert client.post("/api/pulse/decouverte/activer", json={"jeton": p["jeton"]}).status_code == 409
    ref = client.get("/api/pulse/decouverte/referentiel", headers=inv).json()
    assert len(ref["metiers"]) >= 20 and "Haute-Savoie" in ref["zones"]
    assert client.post("/api/pulse/decouverte/declaration", headers=inv, json={"entreprise": "Exposant invité d'Annecy",
                       "metier": "traiteur", "zone": "Haute-Savoie"}).status_code == 200
    moi = client.get("/api/pulse/decouverte/moi", headers=inv).json()
    assert moi["monde"] == "monde de démonstration" and moi["demandes"]
    ask = moi["demandes"][0]["id"]
    assert client.post(f"/api/pulse/decouverte/demandes/{ask}/reponse", headers=inv, json={"aide": True}).status_code == 200
    assert client.post("/api/pulse/decouverte/rejoindre", headers=inv).json()["simule"] == "simulé en démonstration"
    s = client.get("/api/pulse/console/suivi", headers=CONSOLE).json()
    assert s["invites"]["ont_contribue"] == "< 3" and s["invites"]["intentions_adhesion"] == "< 3"
    for ecran in (json.dumps(s, ensure_ascii=False), json.dumps(client.get("/api/pulse/console/decouverte", headers=CONSOLE).json()),
                  json.dumps(client.get("/api/pulse/console/capacites", headers=CONSOLE).json(), ensure_ascii=False)):
        assert "Annecy" not in ecran and "Exposant" not in ecran      # le nom déclaré : jamais sur un écran du Club
    assert "conversion" not in json.dumps(s, ensure_ascii=False).lower()
    assert client.get("/decouverte").status_code == 200


def test_activation_limitee_par_code(http):
    for _ in range(5):
        client.post("/api/pulse/decouverte/activer", json={"jeton": "d1.abc.0000"})
    assert client.post("/api/pulse/decouverte/activer", json={"jeton": "d1.abc.0000"}).status_code == 429


def test_interrupteur_eteint_404(monkeypatch):
    monkeypatch.setenv("HACKVS_FOIRE", "0")
    client.post("/api/pulse/demo/reinitialiser", headers=CONSOLE)
    assert client.post("/api/pulse/console/decouverte", headers=CONSOLE, json={"origine": "stand"}).status_code == 404
    assert client.post("/api/pulse/decouverte/activer", json={"jeton": "d1.a.b"}).status_code == 404

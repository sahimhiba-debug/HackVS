"""MODE SALLE — « le Club, c'est vous » : QR multi-usage → passes individuels (2 h, plafond, sans compte), accueil en
deux gestes avec reçu, demande à trois pièces, anneau, retrait anonyme et recomposition, écran en agrégats (k = 3),
bascule, purge totale. Données FICTIVES (personne ne donne son nom)."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from intelligence.erreurs import Conflit, Invalide, Limite, NonAuthentifie
from intelligence.salle import EFFACEMENT, Salle

CONSOLE = {"X-Pulse-Console": "1"}


class Horloge:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


@pytest.fixture
def h():
    return Horloge()


@pytest.fixture
def s(h):
    return Salle(b"s" * 32, plafond=5, minimum=3, horloge=h)


def _entrer(s, capacite=None):
    p = s.entrer(s.ouvrir()["jeton_salle"])["passe"]
    if capacite:
        s.declarer(p, capacite, True)
    return p


def test_qr_multi_usage_passes_individuels_plafond(s):
    q = s.ouvrir()["jeton_salle"]
    passes = {s.entrer(q)["passe"] for _ in range(5)}
    assert len(passes) == 5                                          # un passe par scan
    with pytest.raises(Limite):
        s.entrer(q)                                                  # plafond
    with pytest.raises(NonAuthentifie):
        s.entrer("s1." + "0" * 32)


def test_qr_refuse_tant_que_la_salle_n_est_pas_ouverte(h):
    s = Salle(b"s" * 32, horloge=h)
    with pytest.raises(NonAuthentifie):
        s.entrer("s1.x")


def test_accueil_en_deux_gestes_consentement_obligatoire_et_recu(s):
    p = _entrer(s)
    with pytest.raises(Invalide):
        s.declarer(p, "voiture", False)
    with pytest.raises(Invalide):
        s.declarer(p, "fusee", True)
    r = s.declarer(p, "voiture", True)["recu"]
    assert r["revocable"] and "rien d'autre" in r["finalite"] and r["simule"] == "simulé en démonstration"
    with pytest.raises(Conflit):
        s.declarer(p, "salle", True)


def test_passe_expire_falsifie_et_purge(s, h):
    p = _entrer(s, "voiture")
    with pytest.raises(NonAuthentifie):
        s.moi(p[:-1] + ("0" if p[-1] != "0" else "1"))
    h.t += 2 * 3600 + 1
    with pytest.raises(NonAuthentifie):
        s.moi(p)


def test_purge_totale_efface_tout_et_invalide_les_anciens_passes(s):
    p = _entrer(s, "voiture")
    q = s.ouvrir()["jeton_salle"]
    r = s.purger()
    assert r["message"] == EFFACEMENT
    assert s.participants == {} and s.fil == [] and s.ouverte_le is None
    with pytest.raises(NonAuthentifie):
        s.moi(p)
    s.ouvrir()
    with pytest.raises(NonAuthentifie):
        s.entrer(q)                                                  # l'ancien QR ne vaut plus rien


def test_anneau_reserve_retrait_recomposition(h):
    s = Salle(b"s" * 32, plafond=80, horloge=h)
    v1, v2, sa, de = _entrer(s, "voiture"), _entrer(s, "voiture"), _entrer(s, "salle"), _entrer(s, "allemand")
    autre = _entrer(s, "traiteur")
    assert s.moi(v1)["demande"] is None                              # pas encore lancée
    s.lancer()
    assert s.moi(autre)["demande"] is None                           # traiteur : pas concerné
    assert s.moi(v1)["demande"]["choix"] == ["oui", "non", "pas cette fois"]
    for p in (v1, sa, de):
        s.repondre(p, "oui")
    assert s.ecran()["demande"]["fermee"] is True
    assert s.repondre(v2, "oui")["recu"]["etat"] == "valable — en réserve"
    with pytest.raises(Conflit):
        s.repondre(v1, "non")                                        # une seule réponse
    r = s.retirer(v1)
    assert r["message"] == "Consentement retiré. Personne ne sera prévenu que c'est vous."
    e = s.ecran()
    assert e["demande"]["fermee"] is True                            # la réserve a repris la pièce
    assert any("recomposition" in f["texte"] for f in e["fil"])
    assert s.moi(v2)["recu"]["etat"].startswith("valable — votre pièce")


def test_role_masque_sous_trois_porteurs_dit_au_dela(h):
    s = Salle(b"s" * 32, plafond=80, horloge=h)
    v = _entrer(s, "voiture")
    for c in ("salle", "allemand"):
        _entrer(s, c)
    s.lancer()
    s.repondre(v, "oui")
    s.retirer(v)
    fil = " ".join(f["texte"] for f in s.ecran()["fil"])
    assert "un composant n'est plus disponible" in fil and "transport :" not in fil
    s2 = Salle(b"s" * 32, plafond=80, horloge=h)
    vs = [_entrer(s2, "voiture") for _ in range(3)]
    s2.lancer()
    s2.repondre(vs[0], "oui")
    s2.retirer(vs[0])
    assert "transport : ce composant n'est plus disponible" in " ".join(f["texte"] for f in s2.ecran()["fil"])


def test_ecran_en_agregats_k3_et_bascule(s, h):
    _entrer(s, "voiture")
    e = s.ecran()
    assert e["participants"] == "< 3" and next(c for c in e["capacites"] if c["id"] == "voiture")["n"] == "< 3"
    assert e["bascule"] is False
    h.t += 61
    assert s.ecran()["bascule"] is True                              # 1 < minimum (3) après 60 s
    for _ in range(2):
        _entrer(s, "salle")
    assert s.ecran()["participants"] == 3 and s.ecran()["bascule"] is False


def test_retrait_declenche_par_la_telecommande_est_etiquete_simule(h):
    s = Salle(b"s" * 32, plafond=80, horloge=h)
    p = _entrer(s, "voiture")
    s.lancer()
    with pytest.raises(Conflit):
        s.declencher_retrait()
    s.repondre(p, "oui")
    assert s.declencher_retrait()["simule"].endswith("simulé en démonstration")


def test_bilan_en_cinq_minutes(h):
    s = Salle(b"s" * 32, plafond=80, horloge=h)
    ps = [_entrer(s, c) for c in ("voiture", "salle", "allemand")]
    s.lancer()
    for p in ps:
        s.repondre(p, "oui")
    h.t += 300
    b = s.bilan()
    assert b["possible"] and b["phrase"].startswith("En 5 minute(s), cette salle a rendu possible")


# ------------------------------------------------------------------ par HTTP
def test_parcours_http_complet_et_rien_de_nominatif():
    c = TestClient(app)
    c.post("/api/pulse/console/salle/purger", headers=CONSOLE)
    o = c.post("/api/pulse/console/salle/ouvrir", headers=CONSOLE).json()
    assert "/salle#s=s1." in o["url"] and o["qr"].startswith("data:image/svg")
    jeton = o["url"].split("#s=", 1)[1]
    p = {"X-Pulse-Salle": c.post("/api/pulse/salle/entrer", json={"jeton": jeton}).json()["passe"]}
    assert c.post("/api/pulse/salle/declarer", headers=p, json={"capacite": "voiture", "consentement": True}).status_code == 200
    assert c.post("/api/pulse/console/salle/lancer", headers=CONSOLE).status_code == 200
    assert c.get("/api/pulse/salle/moi", headers=p).json()["demande"]["piece"] == "transport"
    assert c.post("/api/pulse/salle/repondre", headers=p, json={"choix": "oui"}).status_code == 200
    e = c.get("/api/pulse/console/salle", headers=CONSOLE).json()
    assert e["message"] == EFFACEMENT and e["monde"] == "monde de démonstration"
    assert "passe" not in json.dumps(e) and p["X-Pulse-Salle"] not in json.dumps(e)
    assert c.get("/api/pulse/salle/moi").status_code == 401
    assert c.post("/api/pulse/console/salle/purger", headers=CONSOLE).json()["message"] == EFFACEMENT
    assert c.get("/api/pulse/salle/moi", headers=p).status_code == 401
    for page in ("/salle", "/salle/ecran", "/salle/regie"):
        assert c.get(page).status_code == 200, page


def test_qr_salle_part_de_public_base_url(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://pulse.exemple.ch")
    c = TestClient(app)
    c.post("/api/pulse/console/salle/purger", headers=CONSOLE)
    assert c.post("/api/pulse/console/salle/ouvrir", headers=CONSOLE).json()["url"].startswith("https://pulse.exemple.ch/salle#s=")


def test_interrupteur_salle_eteint(monkeypatch):
    monkeypatch.setenv("HACKVS_SALLE", "0")
    c = TestClient(app)
    assert c.get("/api/pulse/console/salle/etat", headers=CONSOLE).json() == {"actif": False}
    assert c.post("/api/pulse/console/salle/ouvrir", headers=CONSOLE).status_code == 404
    assert c.post("/api/pulse/salle/entrer", json={"jeton": "s1.x"}).status_code == 404


def test_ouverte_a_l_instant_zero_reste_ouverte():
    """Un horodatage 0 n'est pas « fermé » (bug trouvé par l'E2E : `if ouverte_le` au lieu de `is not None`)."""
    h = [0.0]
    s = Salle(b"x" * 32, minimum=2, horloge=lambda: h[0])
    s.ouvrir()
    h[0] = 61
    assert s.ecran()["depuis_s"] == 61 and s.ecran()["bascule"] is True


def test_la_vue_de_l_ecran_est_choisie_cote_serveur_et_purgee(s):
    assert s.ecran()["vue"] == "salle"
    s.afficher("bilan")
    assert s.ecran()["vue"] == "bilan"
    with pytest.raises(Invalide):
        s.afficher("autre")
    s.purger()
    assert s.ecran()["vue"] == "salle"

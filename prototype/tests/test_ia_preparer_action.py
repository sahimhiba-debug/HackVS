"""« Agir à plusieurs → Comprendre ma demande » (POST /moi/actions/preparer) avec un VRAI fournisseur Apertus (client HTTP
simulé, aucun réseau) : l'IA propose, le membre décide.

- sortie valide → exigences du modèle, dites « apertus » ; rien n'est écrit (le membre confirme ensuite) ;
- JSON invalide, hors schéma, incohérente, délai dépassé, panne → repli déterministe (règles), le parcours continue (200) ;
- le serveur ne gèle jamais pendant l'appel au modèle : les autres requêtes ne l'attendent pas ;
- l'attente totale est bornée (APERTUS_BUDGET_S) pour que le repli arrive avant l'abandon du téléphone (15 s) ;
- le scénario guidé de la régie reste en forme déterministe même si un modèle est configuré.
Données FICTIVES."""
import json
import threading
import time

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.pulse_api import creer_routeur
from app.taxonomy import charger_taxonomie
from intelligence import ia as ia_mod
from intelligence.demo import Demo
from intelligence.ia import Apertus, Intelligence

TAX = charger_taxonomie()
CONSOLE = {"X-Pulse-Console": "1"}
TEXTE = "Je voudrais présenter nos tisanes à des acheteurs germanophones jeudi après-midi, il me faut quelqu'un qui parle allemand."
VALIDE = {"objet": "tisanes", "langue_public": "de", "manquant": [],
          "fenetre": {"jour": "2026-10-08", "debut": "14:00", "fin": "17:00"},
          "exigences": [{"role": "voix", "nature": "competence", "concept": None, "geste": "Présenter les tisanes en allemand",
                         "duree_min": 60, "livrable": None}]}
ENV = {"APERTUS_BASE_URL": "https://apertus.test/v1", "APERTUS_API_KEY": "cle-fictive-" + "x" * 30, "APERTUS_MODEL": "swiss-ai/Apertus-test"}


def _reponse(contenu) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": contenu if isinstance(contenu, str) else json.dumps(contenu)}}]})


def _monde(tmp_path, monkeypatch, gerer):
    """API Club Pulse dont le fournisseur est l'Apertus du PRODUIT, branché sur un serveur HTTP simulé."""
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("HACKVS_ESSAIS_DB", str(tmp_path / "journal.db"))
    vus: list[dict] = []

    def transport(req: httpx.Request) -> httpx.Response:
        vus.append(json.loads(req.content))
        return gerer(req)
    client = httpx.Client(transport=httpx.MockTransport(transport))
    origine = Intelligence.depuis_environnement.__func__

    def depuis_env(cls, tax, journal=None, notes_privees_autorisees=False):
        ia = origine(cls, tax, journal, notes_privees_autorisees)
        assert isinstance(ia.f, Apertus)                      # la configuration choisit bien Apertus
        ia.f.http = client
        return ia
    monkeypatch.setattr(Intelligence, "depuis_environnement", classmethod(depuis_env))
    app = FastAPI()
    app.include_router(creer_routeur(TAX))
    c = TestClient(app)
    codes = {p["id"]: p["code"] for p in c.get("/api/pulse/console/personas", headers=CONSOLE).json()}
    s = {"X-Pulse-Session": c.post("/api/pulse/acces", json={"code": codes["n01"]}).json()["session"]}
    return c, s, vus


def _preparer(c, s):
    return c.post("/api/pulse/moi/actions/preparer", headers=s, json={"texte": TEXTE})


def test_sortie_valide_le_modele_propose_et_rien_n_est_ecrit(tmp_path, monkeypatch):
    c, s, vus = _monde(tmp_path, monkeypatch, lambda req: _reponse(VALIDE))
    avant = c.get("/api/pulse/moi/actions", headers=s).json()
    r = _preparer(c, s)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["ia"]["fournisseur"] == "apertus" and p["ia"]["repli"] is False and p["ia"]["modele"] == ENV["APERTUS_MODEL"]
    assert [x["role"] for x in p["exigences"]] == ["voix"] and p["fenetre"]["jour"] == "2026-10-08"
    assert len(vus) == 1 and vus[0]["response_format"]["json_schema"]["strict"] is True         # sortie contrainte
    assert "Sophie" not in json.dumps(vus[0])                                                   # aucun nom du coffre envoyé
    assert c.get("/api/pulse/moi/actions", headers=s).json() == avant                           # proposition, pas décision


@pytest.mark.parametrize("contenu, cas", [
    ("ceci n'est pas du JSON", "JSON invalide"),
    ({"objet": "tisanes"}, "hors schéma : champs manquants"),
    ({**VALIDE, "exigences": [{**VALIDE["exigences"][0], "role": "chef"}]}, "hors schéma : rôle inconnu"),
    ({**VALIDE, "exigences": [{**VALIDE["exigences"][0], "concept": "capacite-inventee"}]}, "incohérent : capacité hors catalogue"),
    ({**VALIDE, "exigences": [{**VALIDE["exigences"][0], "duree_min": 900}]}, "incohérent : durée hors bornes"),
    ({**VALIDE, "fenetre": {"jour": "2020-01-01", "debut": "14:00", "fin": "17:00"}}, "incohérent : jour passé"),
    ({**VALIDE, "objet": "voir MEMBRE-007"}, "incohérent : identifiant de membre"),
])
def test_sortie_rejetee_repli_deterministe_et_le_parcours_continue(tmp_path, monkeypatch, contenu, cas):
    c, s, _ = _monde(tmp_path, monkeypatch, lambda req: _reponse(contenu))
    r = _preparer(c, s)
    assert r.status_code == 200, (cas, r.text)
    p = r.json()
    if cas == "incohérent : jour passé":                     # la fenêtre est corrigée par le produit, le reste est accepté
        assert p["fenetre"]["jour"] != "2020-01-01", cas
        return
    assert p["ia"]["repli"] is True and p["mode"] != "apertus", cas
    assert p["exigences"], cas                                # les règles proposent quand même (« allemand » reconnu)
    corps = {"question": "Présenter nos tisanes", "objet": p.get("objet") or "", "critere": "", "exigences": p["exigences"],
             "fenetre": {"jour": "2026-10-08", "debut": "14:00", "fin": "17:00"}, "duree_min_acceptable": 30}
    assert c.post("/api/pulse/moi/actions/nouvelle", headers=s, json=corps).status_code == 200, cas   # le membre continue


@pytest.mark.parametrize("panne", ["delai", "503", "401", "reseau"])
def test_panne_du_fournisseur_repli_deterministe(tmp_path, monkeypatch, panne):
    def gerer(req):
        if panne == "delai":
            raise httpx.ReadTimeout("lent", request=req)
        if panne == "reseau":
            raise httpx.ConnectError("injoignable", request=req)
        return httpx.Response(int(panne), json={"error": "x"})
    monkeypatch.setattr(ia_mod.time, "sleep", lambda s: None)
    c, s, vus = _monde(tmp_path, monkeypatch, gerer)
    r = _preparer(c, s)
    assert r.status_code == 200 and r.json()["ia"]["repli"] is True and r.json()["ia"]["statut"] == "INDISPONIBLE"
    assert 1 <= len(vus) <= 3


def test_l_attente_totale_est_bornee_par_le_budget(monkeypatch):
    """Un fournisseur qui répond trop lentement : on cesse de réessayer quand le budget est épuisé, et chaque tentative
    reçoit un délai qui tient dans ce qui reste — le repli arrive avant l'abandon du téléphone (15 s)."""
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("APERTUS_BUDGET_S", "1.2")
    delais: list[float] = []

    class Lent:
        def post(self, url, headers=None, json=None, timeout=None):
            delais.append(timeout.read if timeout is not None else float("inf"))
            time.sleep(0.5)
            raise httpx.ReadTimeout("lent")
    t = time.perf_counter()
    r = Intelligence(TAX, Apertus(http=Lent(), dormir=lambda s: None)).comprendre_action(TEXTE, Demo(TAX).club.jour)
    duree = time.perf_counter() - t
    assert r.appel.repli and r.appel.statut == "INDISPONIBLE"
    assert duree < 1.2 + 0.6, duree
    assert delais and all(d <= 1.2 for d in delais), delais


def test_le_serveur_ne_gele_pas_pendant_l_appel_au_modele(tmp_path, monkeypatch):
    """Pendant qu'Apertus réfléchit (1,5 s ici), l'écran commun et les autres téléphones répondent sans l'attendre."""
    def lent(req):
        time.sleep(1.5)
        return _reponse(VALIDE)
    c, s, _ = _monde(tmp_path, monkeypatch, lent)
    fini = {}
    t = threading.Thread(target=lambda: fini.setdefault("r", _preparer(c, s)))
    t.start()
    time.sleep(0.3)                                           # l'appel au modèle est en cours
    debut = time.perf_counter()
    assert c.get("/api/pulse/console/projection", headers=CONSOLE).status_code == 200
    assert c.get("/api/pulse/moi/actions", headers=s).status_code == 200
    attente = time.perf_counter() - debut
    t.join()
    assert fini["r"].status_code == 200 and fini["r"].json()["ia"]["repli"] is False
    assert attente < 0.8, f"les autres requêtes ont attendu {attente:.2f} s le modèle"


def test_le_scenario_guide_reste_deterministe_meme_avec_un_modele(monkeypatch):
    """Décision du 01.10 : la démonstration de scène (régie) ne dépend d'aucun modèle — même configuré."""
    appels = []

    class Modele:
        nom, modele = "apertus", "swiss-ai/Apertus-test"

        def completer(self, systeme_txt, message, schema):
            appels.append(message)
            return json.dumps(VALIDE)
    d = Demo(TAX, ia=Intelligence(TAX, Modele()))
    d.suivant()
    comp = d.ctx["comprehension"]
    assert appels == [] and comp["ia"]["fournisseur"] == "deterministe" and comp["ia"]["repli"] is False


def test_la_date_du_jour_parvient_au_modele_les_telephones_jamais():
    """Défaut trouvé le 01.10 en préparant le banc : le filtre des téléphones retirait aussi « 2026-10-06 » — le modèle
    ne recevait pas la date du jour et ne pouvait pas situer « jeudi ». Une date n'est pas un numéro ; un numéro reste retiré."""
    from intelligence.identite import nettoyer
    assert nettoyer("Date du jour : 2026-10-06 (mardi)", []) == "Date du jour : 2026-10-06 (mardi)"
    assert nettoyer("le 08.10.2026 à 14h", []) == "le 08.10.2026 à 14h"
    for tel in ["079 123 45 67", "+41 27 123 45 67", "0271234567", "027.123.45.67", "+41-79-123-45-67"]:
        assert "[retiré]" in nettoyer(f"appelez le {tel}", []) and "45" not in nettoyer(f"appelez le {tel}", [])[-12:], tel

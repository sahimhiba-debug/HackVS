"""Fournisseurs de langage interchangeables (Apertus, OpenAI, Claude) : sélection explicite, inactifs sans clé, AUCUN
appel réseau dans ces tests (transport HTTP simulé ; tout envoi réel ferait échouer le test), MÊME entrée et MÊME
validation du produit pour tous — un fournisseur ne peut jamais contourner le validateur — et aucune fuite de clé.
Clés FICTIVES."""
import json
import logging

import httpx
import pytest

from app.taxonomy import charger_taxonomie
from intelligence import ia
from intelligence.ia import Apertus, Claude, ErreurFournisseur, Intelligence, NonConfigure, OpenAI, choisir_fournisseur

TAX = charger_taxonomie()
JOUR = __import__("datetime").date(2026, 10, 6)
CLES = {"APERTUS_API_KEY": "cle-test-apertus-" + "a" * 24, "OPENAI_API_KEY": "cle-test-openai-" + "o" * 24,
        "ANTHROPIC_API_KEY": "cle-test-anthropic-" + "c" * 24}
CONFIG = {"apertus": {"APERTUS_API_KEY": CLES["APERTUS_API_KEY"], "APERTUS_BASE_URL": "https://apertus.test/v1",
                      "APERTUS_MODEL": "apertus-test"},
          "openai": {"OPENAI_API_KEY": CLES["OPENAI_API_KEY"], "OPENAI_MODEL": "openai-test"},
          "claude": {"ANTHROPIC_API_KEY": CLES["ANTHROPIC_API_KEY"], "ANTHROPIC_MODEL": "claude-test"}}
CLASSES = {"apertus": Apertus, "openai": OpenAI, "claude": Claude}
TEXTE = "Il me faut quelqu'un qui parle allemand pour présenter nos tisanes jeudi entre 14h et 16h."
VALIDE = {"objet": "tisanes", "langue_public": "de", "manquant": [], "fenetre": {"jour": "2026-10-08", "debut": "14:00", "fin": "16:00"},
          "exigences": [{"role": "voix", "nature": "competence", "concept": None, "geste": "Présenter en allemand",
                         "duree_min": 60, "livrable": None}]}


@pytest.fixture(autouse=True)
def sans_reseau(monkeypatch):
    """Garde-fou : un vrai envoi HTTP (hors transport simulé) fait échouer le test."""
    def interdit(*a, **k):
        raise AssertionError("appel réseau réel tenté")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", interdit)
    for k in ["LLM_PROVIDER", "HACKVS_ANTHROPIC_BASE_URL", "OPENAI_BASE_URL", "OPENAI_TEMPERATURE", "ANTHROPIC_TEMPERATURE",
              *(k for c in CONFIG.values() for k in c)]:
        monkeypatch.delenv(k, raising=False)


def _configurer(monkeypatch, *noms):
    for n in noms:
        for k, v in CONFIG[n].items():
            monkeypatch.setenv(k, v)


def _reponse(nom, contenu):
    """La réponse HTTP qu'enverrait l'API de ce fournisseur, avec ce contenu."""
    if nom == "claude":
        return {"content": [{"type": "tool_use", "name": "sortie", "input": contenu}]} if isinstance(contenu, dict) \
            else {"content": [{"type": "text", "text": contenu}]}
    return {"choices": [{"message": {"content": contenu if isinstance(contenu, str) else json.dumps(contenu)}}]}


def _fournisseur(monkeypatch, nom, gerer):
    _configurer(monkeypatch, nom)
    vus = []

    def transport(req):
        vus.append({"url": str(req.url), "entetes": dict(req.headers), "corps": json.loads(req.content)})
        return gerer(req)
    return CLASSES[nom](http=httpx.Client(transport=httpx.MockTransport(transport)), dormir=lambda s: None), vus


# ------------------------------------------------------------------ sélection
def test_par_defaut_le_comportement_d_origine_est_inchange(monkeypatch):
    assert choisir_fournisseur() is None                                 # rien de configuré : forme déterministe
    _configurer(monkeypatch, "openai", "claude")
    assert choisir_fournisseur() is None                                 # des clés OpenAI/Claude présentes ne changent RIEN
    _configurer(monkeypatch, "apertus")
    assert isinstance(choisir_fournisseur(), Apertus)                    # Apertus configuré : Apertus, comme avant


@pytest.mark.parametrize("nom", ["apertus", "openai", "claude"])
def test_selection_explicite(monkeypatch, nom):
    monkeypatch.setenv("LLM_PROVIDER", nom.upper())
    assert choisir_fournisseur() is None                                 # choisi mais sans clé : inactif, aucun autre à sa place
    _configurer(monkeypatch, *CONFIG)
    f = choisir_fournisseur()
    assert type(f) is CLASSES[nom] and f.nom == nom


@pytest.mark.parametrize("valeur", ["deterministe", "aucun"])
def test_aucun_modele_explicite(monkeypatch, valeur):
    _configurer(monkeypatch, *CONFIG)
    monkeypatch.setenv("LLM_PROVIDER", valeur)
    assert choisir_fournisseur() is None


@pytest.mark.parametrize("valeur", ["gpt", "anthropic", "apertus2", "mistral"])
def test_valeur_invalide_erreur_explicite(monkeypatch, valeur):
    monkeypatch.setenv("LLM_PROVIDER", valeur)
    with pytest.raises(ValueError, match="LLM_PROVIDER invalide.*apertus, openai, claude"):
        choisir_fournisseur()


@pytest.mark.parametrize("nom", ["openai", "claude"])
def test_sans_cle_le_fournisseur_ne_se_construit_pas(monkeypatch, nom):
    assert not CLASSES[nom].configure()
    with pytest.raises(NonConfigure):
        CLASSES[nom]()


def test_claude_ignore_anthropic_base_url_de_l_outillage(monkeypatch):
    _configurer(monkeypatch, "claude")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://passerelle-outillage.test")
    assert Claude().base == "https://api.anthropic.com"
    monkeypatch.setenv("HACKVS_ANTHROPIC_BASE_URL", "https://autre.test")
    assert Claude().base == "https://autre.test"


# ------------------------------------------------------------------ requêtes : même entrée pour tous
def test_meme_consigne_meme_message_meme_schema_pour_les_trois(monkeypatch):
    envoyes = {}
    for nom in CLASSES:
        f, vus = _fournisseur(monkeypatch, nom, lambda req, n=nom: httpx.Response(200, json=_reponse(n, VALIDE)))
        r = Intelligence(TAX, f).comprendre_action(TEXTE, JOUR)
        assert r.appel.fournisseur == nom and not r.appel.repli, (nom, r.appel)
        envoyes[nom] = vus[0]
    sys_a, msg_a = envoyes["apertus"]["corps"]["messages"][0]["content"], envoyes["apertus"]["corps"]["messages"][1]["content"]
    assert envoyes["openai"]["corps"]["messages"][0]["content"] == sys_a and envoyes["openai"]["corps"]["messages"][1]["content"] == msg_a
    assert envoyes["claude"]["corps"]["system"] == sys_a and envoyes["claude"]["corps"]["messages"][0]["content"] == msg_a
    schema = envoyes["apertus"]["corps"]["response_format"]["json_schema"]["schema"]
    assert envoyes["openai"]["corps"]["response_format"]["json_schema"]["schema"] == schema
    assert envoyes["claude"]["corps"]["tools"][0]["input_schema"] == schema
    assert envoyes["claude"]["corps"]["tool_choice"] == {"type": "tool", "name": "sortie"}
    # mêmes réglages
    assert envoyes["apertus"]["corps"]["temperature"] == envoyes["openai"]["corps"]["temperature"] == envoyes["claude"]["corps"]["temperature"] == 0
    assert envoyes["apertus"]["corps"]["max_tokens"] == envoyes["openai"]["corps"]["max_completion_tokens"] == envoyes["claude"]["corps"]["max_tokens"] == 900
    # points d'accès et en-têtes propres à chaque API
    assert envoyes["openai"]["url"] == "https://api.openai.com/v1/chat/completions"
    assert envoyes["openai"]["entetes"]["authorization"] == f"Bearer {CLES['OPENAI_API_KEY']}"
    assert envoyes["claude"]["url"] == "https://api.anthropic.com/v1/messages"
    assert envoyes["claude"]["entetes"]["x-api-key"] == CLES["ANTHROPIC_API_KEY"] and envoyes["claude"]["entetes"]["anthropic-version"]


def test_apertus_requete_inchangee(monkeypatch):
    f, vus = _fournisseur(monkeypatch, "apertus", lambda req: httpx.Response(200, json=_reponse("apertus", VALIDE)))
    f.completer("Consigne.", "Bonjour", {"type": "object"})
    c = vus[0]["corps"]
    assert vus[0]["url"] == "https://apertus.test/v1/chat/completions"
    assert set(c) == {"model", "temperature", "max_tokens", "messages", "response_format"} and c["temperature"] == 0
    assert f.contrainte == "serveur"


def test_openai_temperature_non_envoyee_sur_demande(monkeypatch):
    monkeypatch.setenv("OPENAI_TEMPERATURE", "defaut")
    f, vus = _fournisseur(monkeypatch, "openai", lambda req: httpx.Response(200, json=_reponse("openai", VALIDE)))
    f.completer("C.", "M", None)
    assert "temperature" not in vus[0]["corps"]


@pytest.mark.parametrize("nom", ["apertus", "openai", "claude"])
def test_contrainte_refusee_par_le_serveur_consigne_seule_et_dite(monkeypatch, nom):
    reps = iter([httpx.Response(400, json={"error": "unsupported"}), httpx.Response(200, json=_reponse(nom, json.dumps(VALIDE)))])
    f, vus = _fournisseur(monkeypatch, nom, lambda req: next(reps))
    assert json.loads(f.completer("C.", "M", {"type": "object"})) == VALIDE
    cle = "tools" if nom == "claude" else "response_format"
    assert cle in vus[0]["corps"] and cle not in vus[1]["corps"] and f.contrainte == "consigne"


def test_claude_reponse_texte_sans_outil(monkeypatch):
    f, _ = _fournisseur(monkeypatch, "claude", lambda req: httpx.Response(200, json=_reponse("claude", '{"a": 1}')))
    assert f.completer("C.", "M", None) == '{"a": 1}'


# ------------------------------------------------------------------ même validation : jamais contournée
HORS_SCHEMA = {**VALIDE, "exigences": [{**VALIDE["exigences"][0], "role": "chef"}]}
INCOHERENT = {**VALIDE, "exigences": [{**VALIDE["exigences"][0], "concept": "capacite-inventee", "duree_min": 180}]}


@pytest.mark.parametrize("nom", ["apertus", "openai", "claude"])
@pytest.mark.parametrize("contenu, accepte", [(VALIDE, True), ("pas du JSON", False), (HORS_SCHEMA, False), (INCOHERENT, False),
                                               ({**VALIDE, "objet": "voir MEMBRE-007"}, False)])
def test_un_fournisseur_ne_contourne_jamais_le_validateur(monkeypatch, nom, contenu, accepte):
    f, _ = _fournisseur(monkeypatch, nom, lambda req: httpx.Response(200, json=_reponse(nom, contenu)))
    r = Intelligence(TAX, f).comprendre_action(TEXTE, JOUR)
    assert (not r.appel.repli) is accepte, (nom, contenu, r.appel)
    if not accepte:
        assert r.appel.statut == "REJETE" and r.sortie.get("mode") != "apertus"          # repli déterministe
        assert "chef" not in json.dumps(r.sortie) and "capacite-inventee" not in json.dumps(r.sortie)


@pytest.mark.parametrize("nom", ["apertus", "openai", "claude"])
@pytest.mark.parametrize("panne", ["delai", "reseau", "503", "401", "corps illisible"])
def test_panne_repli_deterministe_et_aucune_fuite_de_cle(monkeypatch, caplog, nom, panne):
    def gerer(req):
        if panne == "delai":
            raise httpx.ReadTimeout("lent", request=req)
        if panne == "reseau":
            raise httpx.ConnectError("injoignable", request=req)
        if panne == "corps illisible":
            return httpx.Response(200, content=b"<html>erreur</html>")
        return httpx.Response(int(panne), json={"error": {"message": f"clé refusée : {CLES['OPENAI_API_KEY']}"}})
    f, vus = _fournisseur(monkeypatch, nom, gerer)
    caplog.set_level(logging.DEBUG)
    r = Intelligence(TAX, f).comprendre_action(TEXTE, JOUR)
    assert r.appel.repli and r.appel.statut == "INDISPONIBLE" and r.sortie["exigences"]       # les règles prennent le relais
    assert 1 <= len(vus) <= 3
    with pytest.raises(ErreurFournisseur) as e:
        f.completer("C.", "M", None)
    trace = caplog.text + str(e.value) + repr(f) + json.dumps(r.appel.model_dump()) + json.dumps(r.sortie)
    assert not [k for k, v in CLES.items() if v in trace]


def test_le_produit_choisit_le_fournisseur_par_l_environnement(monkeypatch):
    _configurer(monkeypatch, "claude")
    monkeypatch.setenv("LLM_PROVIDER", "claude")
    i = Intelligence.depuis_environnement(TAX)
    assert isinstance(i.f, Claude) and i.etat()["fournisseur"] == "claude" and i.etat()["configure"] is True
    monkeypatch.setenv("LLM_PROVIDER", "nimporte")
    with pytest.raises(ValueError):
        Intelligence.depuis_environnement(TAX)


def test_registre_des_fournisseurs():
    assert set(ia.FOURNISSEURS) == {"apertus", "openai", "claude"}

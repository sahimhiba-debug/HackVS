"""Les rôles EXTRACT / NORMALIZE / NARRATE derrière l'adaptateur : sortie acceptée seulement si le code la valide ;
rejet → UN nouvel essai (la raison est dite au modèle, jamais sa sortie) → forme déterministe ; enregistrement
REJOUÉ sans rappeler le modèle (même hors ligne), jamais quand l'IA est éteinte. Modèle SCRIPTÉ, données FICTIVES."""
import pytest
from fastapi.testclient import TestClient

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.club_pulse import ClubPulse
from intelligence.demo import Demo
from intelligence.ia import ErreurFournisseur, Intelligence
from tests.modele_scripte import ModeleScripte

TAX = charger_taxonomie()
A = "delegation_acheteurs"
TEXTE = "Oui, mon minibus a 14 places et il est libre vendredi après-midi."


def _club(modele):
    c = Demo(TAX, ia=Intelligence(TAX, modele)).club
    return c


def _ask(c, pid=md.PAULINE):
    return next(a for _, a in c.asks_pour(pid) if a.startswith(A))


# ---------------------------------------------------------------------- EXTRACT
def test_extract_accepte_est_model_called_et_ne_declare_rien():
    m = ModeleScripte(extraire_piece={"attributs": {"places": 14}})
    c = _club(m)
    avant = len(c.journal.evenements())
    sortie, ext, nor = c.proposer_reponse(md.PAULINE, _ask(c), TEXTE)
    assert sortie["attributs"] == {"places": 14} and ext.issue == "MODEL_CALLED" and ext.tentatives == 1 and nor is None
    nouveaux = c.journal.evenements()[avant:]
    # une proposition : rien déclaré, rien consenti — la trace de l'appel, et ce qui a été proposé à qui (F31)
    assert [e.type for e in nouveaux] == ["APPEL_IA", "PROPOSITION_IA"]
    assert next(i.statut for i in c.projection_capacites() if i.finalite == A) == "ONE_AWAY"


@pytest.mark.parametrize("hostile, raison", [
    ({"attributs": {"places": 16}}, "absente du texte"),                      # valeur inventée
    ({"attributs": {"places": 14, "chauffeur": 1}}, "attribut non demandé"),
    ({"attributs": {"places": 14}, "consentement": True}, "champs non demandés"),   # le modèle ne consent pas
    ({"attributs": {"places": 14}, "statut": "ACTIVE"}, "champs non demandés"),     # ni ne décide d'un état
    ({"attributs": {"places": 14}, "membre": "Pauline Darbellay"}, "champs non demandés"),
    ({"attributs": {"places": True}}, "hors bornes"),
    ("Bien sûr ! 14 places.", "Expecting value|JSON|objet"),
])
def test_extract_hostile_rejete_deux_fois_puis_formulaire(hostile, raison):
    m = ModeleScripte(extraire_piece=hostile)
    c = _club(m)
    sortie, ext, _ = c.proposer_reponse(md.PAULINE, _ask(c), TEXTE)
    assert sortie["attributs"] == {} and ext.issue == "FALLBACK_FORM" and ext.tentatives == 2 and len(ext.rejets) == 2
    assert m.appels("extraire_piece") == 2
    import re
    assert re.search(raison, ext.rejets[0])


def test_le_nouvel_essai_dit_la_raison_jamais_la_sortie_rejetee():
    m = ModeleScripte(extraire_piece=[{"attributs": {"places": 16}}, {"attributs": {"places": 14}}])
    c = _club(m)
    sortie, ext, _ = c.proposer_reponse(md.PAULINE, _ask(c), TEXTE)
    assert sortie["attributs"] == {"places": 14} and ext.issue == "MODEL_CALLED" and ext.tentatives == 2
    second = m.recus[1][2]
    assert "REJETÉE" in second and "absente du texte" in second and '"places": 16' not in second


def test_panne_du_modele_forme_deterministe_dite():
    c = _club(ModeleScripte(extraire_piece=ErreurFournisseur("HTTP 503")))
    _, ext, _ = c.proposer_reponse(md.PAULINE, _ask(c), TEXTE)
    assert ext.issue == "FALLBACK_FORM" and ext.erreur == "HTTP 503"
    assert "modèle indisponible : HTTP 503" in c.vues_capacites.ia(ext)["libelle"]


def test_proposition_pour_une_demande_qui_n_est_pas_la_sienne():
    from intelligence.erreurs import Introuvable
    c = _club(ModeleScripte(extraire_piece={"attributs": {"places": 14}}))
    with pytest.raises(Introuvable):
        c.proposer_reponse(md.PAULINE, "delegation_acheteurs:1:salle:x", TEXTE)


# ---------------------------------------------------------------------- rejeu
def test_rejeu_sans_rappeler_le_modele_meme_hors_ligne_jamais_ia_eteinte():
    m = ModeleScripte(extraire_piece={"attributs": {"places": 14}})
    c = _club(m)
    ask = _ask(c)
    _, premier, _ = c.proposer_reponse(md.PAULINE, ask, TEXTE)
    _, second, _ = c.proposer_reponse(md.PAULINE, ask, TEXTE)
    assert m.appels("extraire_piece") == 1                                   # pas rappelé
    assert second.issue == "CACHE_REPLAY" and second.rejoue == premier.trace and second.sortie == {"attributs": {"places": 14}, "incertitudes": []}
    c.ia.f = None                                                            # hors ligne : l'enregistrement suffit
    _, hors_ligne, _ = c.proposer_reponse(md.PAULINE, ask, TEXTE)
    assert hors_ligne.issue == "CACHE_REPLAY" and hors_ligne.modele == "modele-scripte-1"
    c.basculer_ia(False)                                                     # IA éteinte : jamais un rejeu
    sortie, eteinte, _ = c.proposer_reponse(md.PAULINE, ask, TEXTE)
    assert eteinte.issue == "FALLBACK_FORM" and sortie["attributs"] == {} and "interrupteur" in (eteinte.politique or "")


def test_un_rejet_ou_une_panne_ne_sont_jamais_rejoues():
    m = ModeleScripte(extraire_piece=[{"attributs": {"places": 16}}, {"attributs": {"places": 16}}, {"attributs": {"places": 14}}])
    c = _club(m)
    ask = _ask(c)
    assert c.proposer_reponse(md.PAULINE, ask, TEXTE)[1].issue == "FALLBACK_FORM"
    assert c.proposer_reponse(md.PAULINE, ask, TEXTE)[1].issue == "MODEL_CALLED"   # le modèle est rappelé
    assert m.appels("extraire_piece") == 3


def test_la_cle_de_rejeu_ne_se_devine_pas_sans_le_secret():
    a = ClubPulse(TAX, ia=Intelligence(TAX, None))
    b = ClubPulse(TAX, ia=Intelligence(TAX, None))
    assert a.ia.empreinte("v1", "x") != b.ia.empreinte("v1", "x")             # secrets de processus distincts


# ---------------------------------------------------------------------- NORMALIZE
def test_normalize_concept_du_vocabulaire_avec_extrait_du_texte():
    r = Demo(TAX, ia=Intelligence(TAX, ModeleScripte(normaliser_offre={"concept": "traduction", "extrait": "je traduis"}))).club.roles_ia
    assert r.normaliser("Le soir, je traduis des fiches vers l'allemand.").sortie == {"concept": "traduction", "extrait": "je traduis"}
    for hostile in ({"concept": "chef_d_etat", "extrait": "je traduis"}, {"concept": "traduction", "extrait": "interprète assermentée"}):
        rr = Demo(TAX, ia=Intelligence(TAX, ModeleScripte(normaliser_offre=hostile))).club.roles_ia
        rep = rr.normaliser("Le soir, je traduis des fiches vers l'allemand.")
        assert rep.appel.issue == "FALLBACK_FORM" and rep.sortie["extrait"] is None       # règles simples


# ---------------------------------------------------------------------- NARRATE
def _faits(c):
    carte = next(x for x in c.vues_capacites.console()["capacites"] if x["finalite"] == A)
    return c.roles_ia.faits(carte)


def test_narrate_cite_ses_faits_et_la_fenetre_passe_le_filtre():
    ok = {"phrases": [{"texte": "Il manque une pièce : le transport.", "faits": ["F1", "F4"]},
                      {"texte": "Fenêtre : 09.10 13:00–18:00.", "faits": ["F2"]}]}
    c = _club(ModeleScripte(raconter_capacite=ok))
    faits = _faits(c)
    assert faits[0]["texte"] == "état : il manque une pièce" and faits[1]["texte"] == "fenêtre : 09.10 13:00–18:00"
    rep = c.roles_ia.raconter(faits)
    assert rep.appel.issue == "MODEL_CALLED" and rep.sortie == ok


@pytest.mark.parametrize("phrase, faits", [
    ("Il manque une pièce.", []),                                             # aucune citation
    ("Il manque une pièce.", ["F99"]),                                        # fait inexistant
    ("Il manque 2 pièces.", ["F1"]),                                          # nombre inventé
    ("Le Club peut le faire dès maintenant.", ["F2"]),                        # état non porté par les faits
    ("Pauline Darbellay apporte le minibus.", ["F4"]),                        # une personne désignée
    ("MEMBRE-0042 apporte la salle.", ["F3"]),
])
def test_narrate_infidele_rejete_puis_gabarit_des_faits(phrase, faits):
    c = _club(ModeleScripte(raconter_capacite={"phrases": [{"texte": phrase, "faits": faits}]}))
    f = _faits(c)
    rep = c.roles_ia.raconter(f)
    assert rep.appel.issue == "FALLBACK_FORM" and rep.appel.tentatives == 2
    assert rep.sortie["phrases"][0] == {"texte": "État : il manque une pièce.", "faits": ["F1"]}


def test_routes_proposition_recit_interrupteur():
    from app.main import app
    t = TestClient(app)
    h = {"X-Pulse-Console": "1"}
    t.post("/api/pulse/demo/reinitialiser", headers=h)
    pauline = {"X-Pulse-Session": next(p for p in t.get("/api/pulse/console/personas", headers=h).json() if p["id"] == md.PAULINE)["session"]}
    assert t.post(f"/api/pulse/console/capacites/{A}/recit").status_code == 403
    r = t.post(f"/api/pulse/console/capacites/{A}/recit", headers=h).json()
    assert r["ia"]["issue"] == "FALLBACK_FORM" and r["phrases"][0]["faits"] == ["F1"]          # aucun modèle ici : dit
    assert t.post("/api/pulse/console/ia", json={"actif": False}, headers=h).json()["actif"] is False
    assert t.get("/api/pulse/console/ia", headers=h).json()["actif"] is False
    t.post("/api/pulse/console/ia", json={"actif": True}, headers=h)
    ask = t.get("/api/pulse/moi/asks", headers=pauline).json()[0]["id"]
    assert t.post(f"/api/pulse/moi/asks/{ask}/proposition", json={"texte": TEXTE}).status_code == 401           # sans session
    p = t.post(f"/api/pulse/moi/asks/{ask}/proposition", json={"texte": TEXTE}, headers=pauline).json()
    assert p["attributs"] == {} and p["ia"]["issue"] == "FALLBACK_FORM" and "aucun modèle configuré" in p["ia"]["libelle"]

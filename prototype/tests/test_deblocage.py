"""Demande débloquée : plan, garde-fous, transitions, confidentialité, mémoire vérifiée. Données FICTIVES (scène)."""
import json
from datetime import date, timedelta

import pytest

from adaptateurs.club import deblocage as db
from app.models import Profil
from app.parser_rules import analyser
from app.taxonomy import DATA_DIR, charger_taxonomie
from plateforme.memoire import Memoire

TAX = charger_taxonomie()
D = json.loads((DATA_DIR / "stage_reseau.json").read_text(encoding="utf-8"))
S = D["sophie"]
SOPHIE = Profil(id="n01", nom=S["nom"], fonction=S["fonction"], entreprise=S["entreprise"], commune=S["commune"],
                type="membre_club", secteurs=["boissons"], offre=S["offre"], recherche=S["recherche"], langues=S["langues"],
                zones_service=S["zones_service"], accepte_introductions=True)
PROFILS = [Profil(**p) for p in D["profils"]] + [SOPHIE]
PAR_ID = {p.id: p for p in PROFILS}
T0 = date(2026, 11, 3)
PHRASE = ("Pour le salon de Munich, je dois faire traduire mes étiquettes en allemand et décrocher un rendez-vous avec "
          "un distributeur en Allemagne, pas un concurrent, qui parle français.")


def _plan(texte=PHRASE, demandeur=SOPHIE, occupes=None):
    b = analyser(texte, TAX)
    return b, db.plan(b, demandeur, PROFILS, TAX, occupes)


def _autorises(pl, etape_id):
    e = next(x for x in pl["etapes"] if x["id"] == etape_id)
    return {x["id"] for x in (e["principal"], e["reserve"]) if x}


def _jusqu_a_contribution(m, reutilisation="club", attribution=True):
    b, pl = _plan()
    did = db.ouvrir(m, T0, SOPHIE, PHRASE, "fiche traduite + un rendez-vous au salon", b)
    trad = next(e for e in pl["etapes"] if e["concept"] == "traduction")
    anna = trad["principal"]["id"]
    db.solliciter(m, T0, did, trad["id"], anna, _autorises(pl, trad["id"]))
    db.repondre(m, T0, did, trad["id"], anna, True)
    cid = db.contribuer(m, T0, did, trad["id"], anna, "ressource", "Fiche : étiquette alimentaire en allemand",
                        "Mentions obligatoires, vocabulaire, pièges fréquents.", reutilisation, attribution)
    return did, pl, trad, anna, cid


# ------------------------------------------------------------------ comprendre et planifier
def test_demande_composite_devient_deux_etapes_et_deux_personnes_seulement():
    b, pl = _plan()
    assert [e["concept"] for e in pl["etapes"]] == ["traduction", "export_allemagne"]
    assert all(e["extrait"] for e in pl["etapes"])                         # chaque étape cite le mot qui la justifie
    assert pl["couverture"] == "2/2" and pl["personnes_sollicitees"] == 2
    noms = {e["concept"]: e["principal"]["nom"] for e in pl["etapes"]}
    assert noms == {"traduction": "Anna Zufferey", "export_allemagne": "Markus Heinzmann"}
    assert pl["membres_non_derange"] == len([p for p in PROFILS if p.type == "membre_club"]) - 1 - 2
    assert all(e["principal"]["preuve"] for e in pl["etapes"])             # une preuve citée, pas un score
    assert "n01" not in pl["personnes"]                                     # jamais soi-même


def test_plan_deterministe_et_sans_ecriture():
    m = Memoire()
    avant = m.empreinte()
    assert _plan()[1] == _plan()[1] and m.empreinte() == avant


def test_personne_qui_refuse_les_introductions_n_est_jamais_proposee_ni_comptee():
    refus = {p.id for p in PROFILS if not p.accepte_introductions}
    assert refus                                                            # la scène contient bien un tel membre
    for t in (PHRASE, "Je cherche un emballage en allemand", "Je cherche un distributeur en Allemagne, en allemand"):
        b, pl = _plan(t)
        for e in pl["etapes"]:
            for x in (e["principal"], e["reserve"]):
                assert not x or x["id"] not in refus


def test_budget_d_attention_bascule_sur_la_reserve():
    _, pl = _plan(occupes={"s14": db.MAX_SOLLICITATIONS_OUVERTES})       # Markus déjà trop sollicité
    exp = next(e for e in pl["etapes"] if e["concept"] == "export_allemagne")
    assert exp["principal"]["id"] != "s14" and exp["principal"] is not None


def test_etape_non_couverte_dit_quelle_contrainte_et_la_plus_petite_levee():
    b, pl = _plan("Je cherche un emballage en allemand")
    e = pl["etapes"][0]
    assert e["principal"] is None and e["manque"]["levees"] == [{"sans": "langue : allemand", "personnes": 1}]
    assert "nom" not in json.dumps(e["manque"])                            # des comptes, jamais de noms avant accord


def test_manque_du_club_quand_aucune_levee_ne_suffit():
    _, pl = _plan("Je cherche un distributeur au Japon pour nos tisanes.")
    assert pl["couverture"] == "0/1" and pl["etapes"][0]["manque"]["levees"] == []
    assert "manque du Club" in pl["etapes"][0]["manque"]["raison"]


def test_question_posee_seulement_si_les_reponses_changent_le_plan():
    b = analyser("J'ai besoin d'aide pour la distribution de nos produits", TAX)
    q = db.question_decisive(b, SOPHIE, PROFILS, TAX)
    assert q and len({o["personnes"] for o in q["options"]}) > 1
    b = analyser("Je cherche un conseil en sécurité", TAX)                  # aucun sens n'est couvert : question inutile
    assert b.ambiguites and db.question_decisive(b, SOPHIE, PROFILS, TAX) is None
    assert db.question_decisive(analyser(PHRASE, TAX), SOPHIE, PROFILS, TAX) is None


# ------------------------------------------------------------------ transitions : chacun ne peut faire que sa part
def test_transitions_invalides_refusees():
    m = Memoire()
    b, pl = _plan()
    with pytest.raises(db.ErreurDeblocage):
        db.ouvrir(m, T0, SOPHIE, PHRASE, "  ", b)                            # pas de prochaine étape = pas de critère d'effet
    with pytest.raises(db.ErreurDeblocage):
        db.ouvrir(m, T0, SOPHIE, "bonjour", "x", analyser("bonjour", TAX))
    did = db.ouvrir(m, T0, SOPHIE, PHRASE, "rendez-vous", b)
    trad = pl["etapes"][0]
    ok = _autorises(pl, trad["id"])
    for membre in ("s01", "n01"):                                           # sans preuve ; soi-même
        with pytest.raises(db.ErreurDeblocage):
            db.solliciter(m, T0, did, trad["id"], membre, ok | {"n01"} if membre == "n01" else ok)
    anna = trad["principal"]["id"]
    with pytest.raises(db.ErreurDeblocage):
        db.repondre(m, T0, did, trad["id"], anna, True)                     # pas sollicitée
    db.solliciter(m, T0, did, trad["id"], anna, ok)
    with pytest.raises(db.ErreurDeblocage):
        db.solliciter(m, T0, did, trad["id"], anna, ok)                     # deux fois
    with pytest.raises(db.ErreurDeblocage):
        db.contribuer(m, T0, did, trad["id"], anna, "ressource", "t", "c")  # pas encore acceptée
    with pytest.raises(db.ErreurDeblocage):
        db.repondre(m, T0, did, trad["id"], "s14", True)                    # un autre membre
    db.repondre(m, T0, did, trad["id"], anna, True)
    with pytest.raises(db.ErreurDeblocage):
        db.repondre(m, T0, did, trad["id"], anna, False)                    # déjà répondu
    cid = db.contribuer(m, T0, did, trad["id"], anna, "ressource", "Fiche", "contenu")
    for qui, verdict in (("s10", "debloque"), ("n01", "génial")):          # seul le demandeur ; verdict connu
        with pytest.raises(db.ErreurDeblocage):
            db.confirmer(m, T0, did, cid, qui, verdict)
    db.confirmer(m, T0, did, cid, "n01", "debloque")
    with pytest.raises(db.ErreurDeblocage):
        db.confirmer(m, T0, did, cid, "n01", "debloque")                    # une seule fois


def test_budget_d_attention_empeche_une_troisieme_sollicitation_ouverte():
    m = Memoire()
    b, pl = _plan()
    exp = next(e for e in pl["etapes"] if e["concept"] == "export_allemagne")
    ok = _autorises(pl, exp["id"])
    for i in range(db.MAX_SOLLICITATIONS_OUVERTES):
        d = db.ouvrir(m, T0 + timedelta(days=i), SOPHIE, PHRASE, f"rdv {i}", b)
        db.solliciter(m, T0, d, exp["id"], "s14", ok)
    d = db.ouvrir(m, T0 + timedelta(days=9), SOPHIE, PHRASE, "rdv x", b)
    with pytest.raises(db.ErreurDeblocage, match="budget"):
        db.solliciter(m, T0, d, exp["id"], "s14", ok)
    assert db.charge(m)["s14"] == db.MAX_SOLLICITATIONS_OUVERTES


# ------------------------------------------------------------------ états : seul l'effet confirmé débloque
def test_etats_debloque_seulement_apres_confirmation_de_toutes_les_etapes():
    m = Memoire()
    did, pl, trad, anna, cid = _jusqu_a_contribution(m)
    assert db.etat(m, did)["etat"] == "EN_COURS"                            # une contribution n'est pas un effet
    db.confirmer(m, T0, did, cid, "n01", "debloque")
    assert db.etat(m, did)["etat"] == "PARTIELLEMENT_DEBLOQUEE"
    exp = next(e for e in pl["etapes"] if e["concept"] == "export_allemagne")
    markus = exp["principal"]["id"]
    db.solliciter(m, T0, did, exp["id"], markus, _autorises(pl, exp["id"]))
    db.repondre(m, T0, did, exp["id"], markus, True)
    c2 = db.contribuer(m, T0, did, exp["id"], markus, "introduction", "Introduction à un agent", "texte", "non")
    db.confirmer(m, T0, did, c2, "n01", "debloque")
    assert db.etat(m, did)["etat"] == "DEBLOQUEE"


def test_verdict_non_ne_debloque_pas_et_n_entre_pas_en_memoire():
    m = Memoire()
    did, *_, cid = _jusqu_a_contribution(m)
    db.confirmer(m, T0, did, cid, "n01", "non")
    assert db.etat(m, did)["etapes"][0]["statut"] == "NON_DEBLOQUEE" and db.memoire_verifiee(m) == []


# ------------------------------------------------------------------ confidentialité
def test_sollicite_ne_voit_que_son_etape_et_pas_qui_demande_avant_accord():
    m = Memoire()
    b, pl = _plan()
    did = db.ouvrir(m, T0, SOPHIE, PHRASE, "rdv", b, anonyme=False)
    trad = pl["etapes"][0]
    anna = trad["principal"]["id"]
    db.solliciter(m, T0, did, trad["id"], anna, _autorises(pl, trad["id"]))
    v = db.vue_sollicitation(m, did, anna, PROFILS)
    brut = json.dumps(v, ensure_ascii=False)
    assert "Sophie" not in brut and "Carron" not in brut and "Tisanes" not in brut
    assert [e["concept"] for e in v["vos_etapes"]] == ["traduction"] and "export" not in brut and "Markus" not in brut
    db.repondre(m, T0, did, trad["id"], anna, True)
    assert db.vue_sollicitation(m, did, anna, PROFILS)["qui_demande"] == SOPHIE.nom   # non anonyme : nommée après accord
    with pytest.raises(db.ErreurDeblocage):
        db.vue_sollicitation(m, did, "s14", PROFILS)                        # non sollicité : rien


def test_demande_anonyme_reste_anonyme_meme_apres_accord():
    m = Memoire()
    did, *_ = _jusqu_a_contribution(m)
    assert "Sophie" not in json.dumps(db.vue_sollicitation(m, did, "s10", PROFILS), ensure_ascii=False)


def test_un_refus_n_est_jamais_revele_au_demandeur():
    m = Memoire()
    b, pl = _plan()
    did = db.ouvrir(m, T0, SOPHIE, PHRASE, "rdv", b)
    exp = next(e for e in pl["etapes"] if e["concept"] == "export_allemagne")
    ok = _autorises(pl, exp["id"])
    db.solliciter(m, T0, did, exp["id"], exp["principal"]["id"], ok)
    db.repondre(m, T0, did, exp["id"], exp["principal"]["id"], False)
    db.solliciter(m, T0, did, exp["id"], exp["reserve"]["id"], ok)        # la réserve silencieuse prend le relais
    db.repondre(m, T0, did, exp["id"], exp["reserve"]["id"], True)
    v = json.dumps(db.vue_demandeur(m, did, "n01", PROFILS), ensure_ascii=False)
    assert PAR_ID[exp["principal"]["id"]].nom not in v and "declin" not in v.lower() and "refus" not in v.lower()
    assert PAR_ID[exp["reserve"]["id"]].nom in v                            # qui a accepté est nommé
    with pytest.raises(db.ErreurDeblocage):
        db.vue_demandeur(m, did, "s10", PROFILS)                            # personne d'autre ne voit le suivi


# ------------------------------------------------------------------ mémoire vérifiée : apprendre sans entraîner
def test_contribution_confirmee_repond_a_une_demande_semblable_sans_deranger_personne():
    m = Memoire()
    did, pl, trad, anna, cid = _jusqu_a_contribution(m)
    db.confirmer(m, T0, did, cid, "n01", "debloque")
    t2 = T0 + timedelta(days=7)
    pauline = PAR_ID["s01"]
    b2 = analyser("Je dois traduire mes étiquettes de vin en allemand pour un salon à Stuttgart.", TAX)
    trouve = db.chercher_en_memoire(m, b2, pauline)
    assert [x["contribution_id"] for x in trouve] == [cid] and trouve[0]["auteur"] == anna
    assert trouve[0]["confirmations"][0]["verdict"] == "debloque"
    assert any("à vérifier" in d for d in trouve[0]["differences"])          # contexte d'origine différent : dit
    assert "n01" not in json.dumps(trouve) and "Sophie" not in json.dumps(trouve, ensure_ascii=False)
    d2 = db.ouvrir(m, t2, pauline, "étiquettes de vin", "étiquettes traduites", b2)
    n_sollicitations = len(m.evenements("SOLLICITATION"))
    db.reutiliser(m, t2, d2, cid, pauline.id)
    db.confirmer(m, t2, d2, cid, pauline.id, "partiel")
    assert len(m.evenements("SOLLICITATION")) == n_sollicitations           # personne n'a été redérangé
    e = db.etat(m, d2)
    assert e["par_memoire"] and [x["statut"] for x in e["etapes"]] == ["PARTIELLE"]   # « vin » : contexte, pas une étape
    assert len(db.memoire_verifiee(m)[0]["confirmations"]) == 2             # la preuve s'accumule


def test_memoire_respecte_la_portee_et_l_attribution():
    m = Memoire()
    did, *_, cid = _jusqu_a_contribution(m, reutilisation="non")
    db.confirmer(m, T0, did, cid, "n01", "debloque")
    assert db.memoire_verifiee(m) == []                                     # réservée au demandeur : jamais réutilisée
    with pytest.raises(db.ErreurDeblocage):
        d2 = db.ouvrir(m, T0, PAR_ID["s01"], "x", "y", analyser(PHRASE, TAX))
        db.reutiliser(m, T0, d2, cid, "s01")
    m2 = Memoire()
    did, *_, cid = _jusqu_a_contribution(m2, attribution=False)
    db.confirmer(m2, T0, did, cid, "n01", "debloque")
    assert db.memoire_verifiee(m2)[0]["auteur"] is None                     # pas d'attribution sans accord


def test_memoire_ne_repond_pas_a_une_autre_competence():
    m = Memoire()
    did, *_, cid = _jusqu_a_contribution(m)
    db.confirmer(m, T0, did, cid, "n01", "debloque")
    assert db.chercher_en_memoire(m, analyser("Je cherche un emballage", TAX)) == []


def test_mot_de_sa_propre_activite_est_du_contexte_pas_une_etape():
    pauline = PAR_ID["s01"]
    b = analyser("Je dois faire traduire mes étiquettes de vin en allemand pour un salon à Stuttgart.", TAX)
    pl = db.plan(b, pauline, PROFILS, TAX)
    assert [e["concept"] for e in pl["etapes"]] == ["traduction"]
    assert pl["ecartees"] and "propre activité" in pl["ecartees"][0]["raison"]
    seul = db.plan(analyser("Je cherche un autre vigneron", TAX), pauline, PROFILS, TAX)
    assert seul["ecartees"] == [] and len(seul["etapes"]) == 1              # seule chose comprise : gardée


def test_un_mot_inconnu_isole_n_est_pas_declare_manque_du_club():
    _, pl = _plan("bonjour tout le monde")
    assert pl["etapes"][0]["manque"]["certain"] is False and "précisez" in pl["etapes"][0]["manque"]["raison"]
    _, pl = _plan("Je cherche un distributeur au Japon pour nos tisanes.")
    assert pl["etapes"][0]["manque"]["certain"] is True

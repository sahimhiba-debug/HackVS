"""Une action COLLECTIVE bornée dans le temps : quatre exigences, quatre personnes, et le moment où leurs
disponibilités DÉCLARÉES se recouvrent. Une condition change (une heure de disponibilité) : ce qui est invalidé, ce qui
peut s'adapter, qui doit reconfirmer ; sans solution, l'action reste bloquée — puis se débloque sur un fait nouveau,
jamais toute seule. Personnes, textes et horaires volontairement DIFFÉRENTS de la démonstration (aucune règle ne
dépend d'un personnage). Données FICTIVES."""
from datetime import date, timedelta

import pytest

from intelligence.erreurs import Conflit, Interdit, Invalide
from intelligence.essai import Banc, Creneau, Etape, Plage, Protocole
from plateforme.memoire import Memoire

J = date(2027, 3, 1)
JOUR = J + timedelta(days=6)
PORTEUR, VOIX, LIEU, PUBLIC, LIEU2, COLLEGUE = "p1", "p2", "p3", "p4", "p5", "p6"
ORGS = {PORTEUR: "fromagerie", COLLEGUE: "fromagerie"}


def plage(debut: str, fin: str) -> list[Plage]:
    return [Plage(jour=JOUR, debut=debut, fin=fin)]


class Scene:
    def __init__(self, voix=("09:30", "12:00")):
        self.jour = J
        self.b = Banc(Memoire(), lambda: self.jour, lambda pid: ORGS.get(pid, f"org-{pid}"))
        b = self.b
        self.voix = b.publier_offre(VOIX, "competence", "Présenter un produit en italien", 1, J, JOUR, duree_max_min=40,
                                    concept="traduction", plages=plage(*voix))
        self.lieu = b.publier_offre(LIEU, "lieu", "Une table haute près de l'entrée de la halle", 1, J, JOUR, plages=plage("08:00", "11:00"))
        self.public = b.publier_offre(PUBLIC, "competence", "Présenter deux acheteurs du Tessin", 1, J, JOUR, duree_max_min=60,
                                      concept="export_suisse_alemanique", plages=plage("09:00", "12:30"))
        b.publier_offre(COLLEGUE, "competence", "Traduction italienne", 1, J, JOUR, concept="traduction", plages=plage("08:00", "18:00"))
        b.publier_offre("p7", "competence", "Présenter en italien", 1, J, JOUR, concept="traduction")   # sans horaire : jamais retenu

    def protocole(self, **kw) -> Protocole:
        return Protocole(question="Présenter notre fromage à des acheteurs italophones", critere="les acheteurs repartent avec un contact",
                         echeance=JOUR, fenetre=Plage(jour=JOUR, debut="08:00", fin="13:00"), duree_min_acceptable=30, etapes=[
                             Etape(id="e1", nature="competence", geste="Présenter le produit en italien", duree_min=30, concept="traduction",
                                   livrable="Fiche produit en italien"),
                             Etape(id="e2", nature="lieu", geste="Prêter la table près de l'entrée", duree_min=30),
                             Etape(id="e3", nature="competence", geste="Amener les acheteurs", duree_min=30, concept="export_suisse_alemanique")],
                         **kw)

    def publier(self) -> tuple[str, int]:
        eid = self.b.brouillon(PORTEUR, self.protocole())
        a = self.b.assembler(PORTEUR, eid)
        sol = a["solution"]
        v = self.b.proposer(PORTEUR, eid, 0, {k: x for k, x in sol["choix"].items() if x}, sol["creneau"])
        for x in (VOIX, LIEU, PUBLIC):
            self.b.decider(x, eid, v, True)
        return eid, v


def test_la_proposition_n_existe_qu_au_recouvrement_des_disponibilites():
    s = Scene()
    eid = s.b.brouillon(PORTEUR, s.protocole())
    a = s.b.assembler(PORTEUR, eid)
    c = a["solution"]["creneau"]
    assert (c.debut, c.fin) == ("09:30", "10:00") or (c.debut, c.duree_min) == ("09:30", 30)   # voix 9:30, lieu fin 11:00
    assert a["solution"]["choix"] == {"e1": s.voix, "e2": s.lieu, "e3": s.public}               # ni la collègue, ni l'offre sans horaire
    assert all(x["offres"] for x in a["exigences"])
    assert s.b.etat(eid) == "BROUILLON"                                                      # assembler n'écrit rien


def test_sans_recouvrement_aucune_proposition_n_est_inventee():
    s = Scene(voix=("14:00", "16:00"))
    eid = s.b.brouillon(PORTEUR, s.protocole())
    a = s.b.assembler(PORTEUR, eid)
    assert a["solution"] is None and "ne se recouvrent" in a["blocage"]
    with pytest.raises(Invalide):
        s.b.proposer(PORTEUR, eid, 0, None, Creneau(jour=JOUR, debut="14:00", duree_min=30))   # hors de la fenêtre du porteur


def test_perturbation_une_heure_de_moins_ce_qui_tombe_ce_qui_s_adapte_qui_reconfirme():
    s = Scene()
    eid, v = s.publier()
    assert s.b.etat(eid) == "AUTORISE"
    s.b.modifier_offre(VOIX, s.voix, plages=plage("10:30", "12:00"))          # la personne, sur SON offre
    assert s.b.etat(eid) == "A_ADAPTER"
    raisons = s.b.raisons_gestes(eid)
    assert raisons["e1"].startswith("son offre ne couvre plus ce geste : pas disponible") and raisons["e2"] is None and raisons["e3"] is None
    alts = [a for a in s.b.alternatives(eid) if a["type"] == "decaler"]
    assert alts and all(Creneau(**a["creneau"]).debut >= "10:30" for a in alts)
    meme = next(a for a in alts if not a["remplaces"])                        # 10:30–11:00 : la table ferme à 11:00
    assert meme["creneau"]["debut"] == "10:30" and meme["creneau"]["duree_min"] == 30
    with pytest.raises(Conflit):
        s.b.lancer(PORTEUR, eid, s.b.version(eid))
    s.b.choisir_alternative(PORTEUR, eid, s.b.version(eid), meme["id"])
    cov = s.b.couverture(eid)
    assert {cov[x] for x in (VOIX, LIEU, PUBLIC)} == {"sa part a changé depuis son accord"}  # le MOMENT change : tous reconfirment
    for x in (VOIX, LIEU):
        s.b.decider(x, eid, s.b.version(eid), True)
    assert s.b.etat(eid) == "PROPOSE"                                         # le public n'a pas reconfirmé : rien n'est supposé
    s.b.decider(PUBLIC, eid, s.b.version(eid), True)
    assert s.b.etat(eid) == "AUTORISE" and s.b.protocole(eid).creneau.debut == "10:30"


def test_variante_plus_courte_jamais_sous_le_minimum_du_porteur():
    s = Scene()
    eid, v = s.publier()
    s.b.modifier_offre(VOIX, s.voix, plages=plage("10:45", "12:00"))          # 15 min avant la fermeture du lieu : trop court
    alts = [a for a in s.b.alternatives(eid) if a["type"] == "decaler"]
    assert all(a["creneau"]["duree_min"] >= 30 for a in alts)
    assert not any(a["creneau"]["debut"] == "10:45" and a["creneau"]["duree_min"] < 30 for a in alts)


def test_sans_solution_bloque_puis_debloque_par_un_fait_nouveau_jamais_seul():
    s = Scene()
    eid, v = s.publier()
    s.b.modifier_offre(VOIX, s.voix, plages=plage("16:00", "18:00"))          # plus aucun recouvrement dans la fenêtre
    assert s.b.etat(eid) == "IMPOSSIBLE"
    with pytest.raises(Conflit):
        s.b.lancer(PORTEUR, eid, s.b.version(eid))
    s.b.modifier_offre(VOIX, s.voix, plages=plage("09:30", "12:00"))          # un fait nouveau : la disponibilité revient
    assert s.b.etat(eid) == "A_ADAPTER"                                        # rouvert — pas relancé
    reprendre = next(a for a in s.b.alternatives(eid) if a["type"] == "reprendre")
    s.b.choisir_alternative(PORTEUR, eid, s.b.version(eid), reprendre["id"])
    assert s.b.etat(eid) == "AUTORISE"                                        # accords toujours valables : conservés, prouvés


def test_une_nouvelle_offre_publiee_debloque_une_action_bloquee():
    s = Scene()
    eid, v = s.publier()
    s.b.retirer_offre(LIEU, s.lieu)
    assert s.b.etat(eid) == "IMPOSSIBLE"
    s.b.publier_offre(LIEU2, "lieu", "Un coin de mon stand", 1, J, JOUR, plages=plage("09:00", "11:00"))
    assert s.b.etat(eid) == "A_ADAPTER"
    alt = next(a for a in s.b.alternatives(eid) if a["type"] == "remplacer")
    s.b.choisir_alternative(PORTEUR, eid, s.b.version(eid), alt["id"])
    assert s.b.couverture(eid)[LIEU2] == "en attente de sa réponse"          # la nouvelle personne décide elle-même


def test_livrable_transmis_n_est_pas_recu_et_la_presence_n_est_pas_constatee_avant_le_jour():
    s = Scene()
    eid, v = s.publier()
    with pytest.raises(Conflit):
        s.b.livrer(VOIX, eid, "e1", "Scheda prodotto")                       # rien avant que l'action soit engagée
    s.b.lancer(PORTEUR, eid, v)
    with pytest.raises(Conflit):
        s.b.constater(PORTEUR, eid, "e1")                                     # rien de transmis : rien de reçu
    with pytest.raises(Interdit):
        s.b.livrer(LIEU, eid, "e1", "faux")                                   # pas son geste
    s.b.livrer(VOIX, eid, "e1", "Scheda prodotto — formaggio d'alpeggio, 12 mesi.")
    assert s.b.etat(eid) == "EN_COURS"                                        # transmis ≠ reçu
    with pytest.raises(Conflit):
        s.b.constater(PORTEUR, eid, "e1")                                     # réception du livrable non confirmée
    s.b.recevoir(PORTEUR, eid, "e1")                                          # la FICHE est reçue…
    with pytest.raises(Conflit):
        s.b.constater(PORTEUR, eid, "e1")                                     # … la présentation, elle, n'a pas eu lieu
    with pytest.raises(Conflit):
        s.b.constater(PORTEUR, eid, "e2")                                     # la présence au créneau : pas avant le jour
    s.jour = JOUR
    s.b.constater(PORTEUR, eid, "e1")
    s.b.constater(PORTEUR, eid, "e2")
    s.b.constater(PORTEUR, eid, "e3")
    assert s.b.etat(eid) == "CONTRIBUTION_RECUE"


def test_un_retrait_apres_accord_bloque_le_lancement():
    s = Scene()
    eid, v = s.publier()
    s.b.retirer(PUBLIC, eid)
    assert s.b.etat(eid) in ("A_ADAPTER", "IMPOSSIBLE")
    with pytest.raises(Conflit):
        s.b.lancer(PORTEUR, eid, v)


def test_un_refus_n_est_jamais_garde_dans_une_adaptation():
    """Défaut trouvé : après un refus, « déplacer — même équipe » gardait la personne qui avait décliné."""
    s = Scene()
    eid = s.b.brouillon(PORTEUR, s.protocole())
    sol = s.b.assembler(PORTEUR, eid)["solution"]
    v = s.b.proposer(PORTEUR, eid, 0, {k: x for k, x in sol["choix"].items() if x}, sol["creneau"])
    s.b.decider(PUBLIC, eid, v, False)
    for a in s.b.alternatives(eid):
        assert PUBLIC not in {s.b.offre(o).auteur for o in (a.get("choix") or {}).values() if o}, a["texte"]
    assert s.b.etat(eid) == "IMPOSSIBLE"                                      # aucun autre public déclaré : bloqué, dit


def test_une_personne_n_est_jamais_engagee_deux_fois_au_meme_moment_quelle_que_soit_la_capacite():
    """Défaut trouvé par la revue « jury » : la capacité comptait des ESSAIS, pas des heures — une offre de capacité 2
    laissait autoriser deux actions au même créneau pour la même personne."""
    s = Scene()
    b = s.b
    b.modifier_offre(VOIX, s.voix, capacite=2)
    b.modifier_offre(LIEU, s.lieu, capacite=2)
    b.modifier_offre(PUBLIC, s.public, capacite=2)
    eid_a, _ = s.publier()                                                    # la voix est engagée 09:30–10:00
    autre = "p8"
    eid_b = b.brouillon(autre, s.protocole())
    sol = b.assembler(autre, eid_b)["solution"]
    assert sol is None or sol["choix"]["e1"] != s.voix or not b._chevauche(sol["creneau"], b.protocole(eid_a).creneau)
    with pytest.raises(Conflit):                                              # on force le même créneau, même personne
        b.proposer(autre, eid_b, 0, {"e1": s.voix, "e2": s.lieu, "e3": s.public}, b.protocole(eid_a).creneau)
    b.retirer(VOIX, eid_a)                                                    # libérée : elle peut de nouveau s'engager
    assert b.occupations(VOIX) == []

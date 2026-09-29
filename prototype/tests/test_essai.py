"""Banc d'essai partagé : parcours nominal, perturbation, refus, impossibilité, silence, capacité, versions, rejeu.
Données FICTIVES : un porteur (Sophie) et quatre offres volontaires déclarées pour le test."""
from datetime import date, timedelta

import pytest

from intelligence.erreurs import Conflit, Interdit, Introuvable, Invalide
from intelligence.essai import Banc, Etape, Protocole
from plateforme.memoire import Memoire

J = date(2026, 11, 3)
SOPHIE, MARKUS, LEA, PAULINE, ANNA = "n01", "s14", "d01", "s01", "s10"
ORGS = {SOPHIE: "tisanes", MARKUS: "bio-de", LEA: "imhof", PAULINE: "vins", ANNA: "tisanes"}   # Anna : même organisation que Sophie


class Monde:
    def __init__(self, memoire=None):
        self.jour = J
        self.b = Banc(memoire or Memoire(), lambda: self.jour, lambda pid: ORGS.get(pid, f"org-{pid}"))
        if memoire is None:
            self.markus = self.b.publier_offre(MARKUS, "temps", "Regard neuf de distributeur sur un emballage ou une étiquette", 2,
                                               J, J + timedelta(days=30), duree_max_min=15)
            self.lea = self.b.publier_offre(LEA, "temps", "Quelques minutes pour relire un support en allemand", 2, J, J + timedelta(days=30),
                                            duree_max_min=15)
            self.pauline = self.b.publier_offre(PAULINE, "lieu", "Un présentoir éclairé sur mon stand", 1, J, J + timedelta(days=30),
                                                duree_max_min=20)
            self.anna = self.b.publier_offre(ANNA, "temps", "Regard neuf sur une étiquette", 3, J, J + timedelta(days=30), duree_max_min=30)

    def essai(self, critere="Sur 3 personnes, combien nomment le produit après 10 s à 1 m ?") -> tuple[str, int]:
        p = Protocole(question="Notre nouvelle étiquette est-elle comprise en 10 secondes à 1 mètre ?", objet="étiquette de tisane",
                      critere=critere, echeance=J + timedelta(days=10),
                      etapes=[Etape(id="e1", nature="temps", geste="Regarder l'étiquette 10 s à 1 m puis dire ce que vous avez compris",
                                    duree_min=10),
                              Etape(id="e2", nature="lieu", geste="Présenter l'étiquette sous l'éclairage d'un stand", duree_min=15)])
        eid = self.b.brouillon(SOPHIE, p)
        return eid, self.b.proposer(SOPHIE, eid, 0)

    def contributeurs(self, eid):
        return {e.id: e.contributeur for e in self.b.protocole(eid).etapes}


def test_parcours_nominal_jusqu_a_une_observation_negative_gardee_telle_quelle():
    m = Monde()
    b = m.b
    eid, v = m.essai()
    assert b.etat(eid) == "PROPOSE" and m.contributeurs(eid) == {"e1": MARKUS, "e2": PAULINE}   # ni Sophie, ni sa collègue Anna
    b.decider(MARKUS, eid, v, True)
    assert b.etat(eid) == "PROPOSE"                                          # Pauline n'a pas répondu : rien n'est supposé
    b.decider(PAULINE, eid, v, True)
    assert b.etat(eid) == "AUTORISE"
    b.lancer(SOPHIE, eid, v)
    b.constater(SOPHIE, eid, "e1")
    assert b.etat(eid) == "EN_COURS"
    b.constater(SOPHIE, eid, "e2")
    assert b.etat(eid) == "CONTRIBUTION_RECUE"                               # reçu ≠ réussi : aucune observation n'existe
    rev = b.observer(SOPHIE, eid, "1 personne sur 3 a nommé le produit.", "negatif", "3 personnes, stand éclairé, 1 étiquette")
    assert b.etat(eid) == "OBSERVEE" and rev == 1
    obs = b._evs(eid, "OBSERVATION")[-1].donnees
    assert obs["qualification"] == "negatif" and obs["limites"].startswith("3 personnes")


def test_moins_de_temps_invalide_la_part_touchee_preserve_le_reste_et_propose_des_alternatives():
    m = Monde()
    b = m.b
    eid, v = m.essai()
    b.decider(MARKUS, eid, v, True)
    b.decider(PAULINE, eid, v, True)
    assert b.etat(eid) == "AUTORISE"
    touches = b.modifier_offre(MARKUS, m.markus, duree_max_min=5)           # perturbation : « je n'ai plus que 5 minutes »
    assert touches == [eid] and b.etat(eid) == "A_ADAPTER"
    cov = b.couverture(eid)
    assert "10 min" in cov[MARKUS] and cov[PAULINE] is None                 # Pauline : son accord couvre toujours sa part
    alts = {a["type"]: a for a in b.alternatives(eid)}
    assert set(alts) == {"remplacer", "raccourcir"} and alts["remplacer"]["membre"] == LEA   # pas Anna : même organisation
    with pytest.raises(Conflit):
        b.lancer(SOPHIE, eid, v)                                            # rien ne se lance sur un accord qui ne couvre plus
    diff = b.choisir_alternative(SOPHIE, eid, v, alts["remplacer"]["id"])
    assert diff["a_redemander"] == [LEA] and diff["preserves"] == [PAULINE]
    v2 = b.version(eid)
    assert b.couverture(eid)[LEA] == "en attente de sa réponse"             # l'accord de Markus ne vaut pas pour Léa
    assert b.etat(eid) == "PROPOSE"
    b.decider(LEA, eid, v2, True)
    assert b.etat(eid) == "AUTORISE"                                        # Pauline n'a rien eu à redonner
    b.lancer(SOPHIE, eid, v2)


def test_raccourcir_redemande_a_la_meme_personne_et_l_objectif_reste_au_porteur():
    m = Monde()
    b = m.b
    eid, v = m.essai()
    b.decider(MARKUS, eid, v, True)
    b.decider(PAULINE, eid, v, True)
    b.modifier_offre(MARKUS, m.markus, duree_max_min=5)
    alt = next(a for a in b.alternatives(eid) if a["type"] == "raccourcir")
    b.choisir_alternative(SOPHIE, eid, v, alt["id"])
    v2 = b.version(eid)
    assert b.protocole(eid).etapes[0].duree_min == 5 and b.protocole(eid).critere == b.protocole(eid, v).critere   # objectif inchangé
    assert b.couverture(eid)[MARKUS] == "sa part a changé depuis son accord" and b.couverture(eid)[PAULINE] is None
    b.decider(MARKUS, eid, v2, True)
    assert b.etat(eid) == "AUTORISE"


def test_aucune_alternative_arret_honnete():
    m = Monde()
    b = m.b
    eid, v = m.essai()
    b.decider(PAULINE, eid, v, True)
    b.retirer_offre(LEA, m.lea)
    b.decider(MARKUS, eid, v, False)                                        # Markus décline ; Léa n'offre plus ; Anna exclue
    assert b.etat(eid) == "IMPOSSIBLE"
    raison = b._evs(eid, "ESSAI_ETAT")[-1].donnees["raison"]
    assert "aucune alternative admissible" in raison and "Regarder l'étiquette" in raison


def test_un_refus_n_est_jamais_redemande():
    m = Monde()
    b = m.b
    eid, v = m.essai()
    b.decider(MARKUS, eid, v, False)
    assert b.etat(eid) == "A_ADAPTER"
    assert all(a["membre"] != MARKUS for a in b.alternatives(eid))
    b.choisir_alternative(SOPHIE, eid, v, next(a["id"] for a in b.alternatives(eid) if a["type"] == "remplacer"))
    with pytest.raises(Interdit):
        b.decider(MARKUS, eid, b.version(eid), True)                        # il n'a plus de part dans la version courante


def test_brouillon_sans_offre_pour_un_geste_n_est_pas_publie():
    m = Monde()
    b = m.b
    p = Protocole(question="Le flacon tient-il debout sur un comptoir incliné ?", critere="tient 1 minute", echeance=J + timedelta(days=5),
                  etapes=[Etape(id="e1", nature="objet", geste="Prêter un comptoir incliné", duree_min=20)])
    eid = b.brouillon(SOPHIE, p)
    with pytest.raises(Conflit, match="personne n'offre"):
        b.proposer(SOPHIE, eid, 0)
    assert b.etat(eid) == "BROUILLON"                                       # le porteur peut encore changer son essai


def test_silence_ni_accord_ni_succes():
    m = Monde()
    b = m.b
    eid, v = m.essai()
    b.decider(MARKUS, eid, v, True)
    m.jour = J + timedelta(days=11)
    assert b.echeances() == [eid] and b.etat(eid) == "EXPIRE"               # Pauline s'est tue : pas d'accord supposé
    m2 = Monde()
    eid2, v2 = m2.essai()
    for x in (MARKUS, PAULINE):
        m2.b.decider(x, eid2, v2, True)
    m2.b.lancer(SOPHIE, eid2, v2)
    m2.b.constater(SOPHIE, eid2, "e1")
    m2.b.constater(SOPHIE, eid2, "e2")
    m2.jour = J + timedelta(days=30)
    m2.b.echeances()
    assert m2.b.etat(eid2) == "RESULTAT_INCONNU"                            # reçu, mais rien d'observé : inconnu, pas réussi
    m2.b.observer(SOPHIE, eid2, "observé plus tard", "mitige", "2 personnes seulement")
    assert m2.b._evs(eid2, "OBSERVATION")[-1].donnees["tardive"] is True


def test_capacite_jamais_depassee():
    m = Monde()
    b = m.b
    eid1, v1 = m.essai()
    eid2, v2 = m.essai("Un autre critère : la couleur est-elle perçue comme « bio » ?")
    assert m.contributeurs(eid2)["e2"] == PAULINE
    b.decider(PAULINE, eid1, v1, True)                                      # capacité 1 : réservée par le premier essai
    with pytest.raises(Conflit, match="capacité"):
        b.decider(PAULINE, eid2, v2, True)


def test_version_perimee_double_clic_et_changement_d_avis():
    m = Monde()
    b = m.b
    eid, v = m.essai()
    b.modifier(SOPHIE, eid, v, critere="Sur 5 personnes, combien nomment le produit ?")
    with pytest.raises(Conflit, match="version"):
        b.decider(MARKUS, eid, v, True)                                     # il a lu l'ancienne version
    v2 = b.version(eid)
    b.decider(MARKUS, eid, v2, True)
    avant = len(b.m.evenements())
    b.decider(MARKUS, eid, v2, True)                                        # double clic : sans effet
    assert len(b.m.evenements()) == avant
    with pytest.raises(Conflit, match="déjà répondu"):
        b.decider(MARKUS, eid, v2, False)


def test_modification_cosmetique_ne_redemande_rien_substantielle_si():
    m = Monde()
    b = m.b
    eid, v = m.essai()
    b.decider(MARKUS, eid, v, True)
    b.decider(PAULINE, eid, v, True)
    d = b.modifier(SOPHIE, eid, v, pourquoi="Nous imprimons 5 000 étiquettes en décembre.")
    assert d["a_redemander"] == [] and b.etat(eid) == "AUTORISE"
    d = b.modifier(SOPHIE, eid, b.version(eid), critere="Sur 3 personnes, combien nomment la MARQUE ?")
    assert sorted(d["a_redemander"]) == sorted([MARKUS, PAULINE]) and b.etat(eid) == "PROPOSE"


def test_retrait_apres_contribution_recue_ne_l_efface_pas():
    m = Monde()
    b = m.b
    eid, v = m.essai()
    for x in (MARKUS, PAULINE):
        b.decider(x, eid, v, True)
    b.lancer(SOPHIE, eid, v)
    b.constater(SOPHIE, eid, "e1")
    r = b.retirer(MARKUS, eid)
    assert r["deja_fait"] == ["e1"] and r["irreversible"] and b.etat(eid) == "EN_COURS"


def test_retrait_avant_contribution_declenche_une_adaptation():
    m = Monde()
    b = m.b
    eid, v = m.essai()
    for x in (MARKUS, PAULINE):
        b.decider(x, eid, v, True)
    b.lancer(SOPHIE, eid, v)
    b.retirer(PAULINE, eid)
    assert b.etat(eid) == "IMPOSSIBLE"                                      # aucun autre lieu offert : on le dit


def test_droits_de_reutilisation_le_plus_restrictif_l_emporte():
    m = Monde()
    b = m.b
    eid, v = m.essai()
    for x in (MARKUS, PAULINE):
        b.decider(x, eid, v, True)
    b.lancer(SOPHIE, eid, v)
    b.constater(SOPHIE, eid, "e1")
    b.constater(SOPHIE, eid, "e2")
    b.observer(SOPHIE, eid, "2 sur 3 ont nommé le produit.", "positif", "3 personnes, 1 stand")
    assert b.niveau_partage(eid) == "participants"                          # personne n'a rien choisi : rien n'est élargi
    b.reutilisation(SOPHIE, eid, "club", "nom")
    b.reutilisation(MARKUS, eid, "club", "anonyme")
    assert b.niveau_partage(eid) == "participants"                          # Pauline n'a pas choisi
    b.reutilisation(PAULINE, eid, "club", "nom")
    assert b.niveau_partage(eid) == "club"
    b.aviser(MARKUS, eid, 1, "conteste", "j'étais à 2 m, pas à 1 m")
    assert b._evs(eid, "AVIS")[-1].donnees["avis"] == "conteste"            # la contestation reste, rien n'est effacé
    with pytest.raises(Interdit):
        b.reutilisation("x99", eid, "club", "nom")


def test_droits_par_role():
    m = Monde()
    b = m.b
    eid, v = m.essai()
    with pytest.raises(Interdit):
        b.lancer(MARKUS, eid, v)
    with pytest.raises(Introuvable):
        b.decider("x99", eid, v, True)                                      # un inconnu n'apprend pas que l'essai existe
    with pytest.raises(Invalide):
        b.reutilisation(SOPHIE, eid, "monde entier", "nom")


def test_rejeu_pur_et_redemarrage(tmp_path):
    chemin = str(tmp_path / "essais.db")
    m = Monde(Memoire(chemin))
    m.markus = m.b.publier_offre(MARKUS, "temps", "Regard neuf sur une étiquette", 2, J, J + timedelta(days=30), duree_max_min=15)
    m.b.publier_offre(PAULINE, "lieu", "Un présentoir éclairé", 1, J, J + timedelta(days=30), duree_max_min=20)
    eid, v = m.essai()
    m.b.decider(MARKUS, eid, v, True)
    avant = m.b.m.empreinte()
    relu = Monde(Memoire(chemin))                                           # redémarrage : on relit le fichier
    assert relu.b.etat(eid) == "PROPOSE" and relu.b.couverture(eid)[MARKUS] is None
    relu.b.alternatives(eid)
    relu.b.reservations(m.markus)
    assert relu.b.m.empreinte() == avant                                    # relire n'écrit rien (aucun effet rejoué)


def test_panne_au_milieu_d_une_commande_rien_d_ecrit_a_moitie(monkeypatch):
    """Tout ou rien : si la publication échoue après avoir écrit la nouvelle version (panne, redémarrage), ni la
    version, ni l'accord du porteur, ni la transition ne restent dans le journal."""
    m = Monde()
    b = m.b
    p = Protocole(question="Étiquette comprise en 10 s ?", critere="3 personnes", echeance=J + timedelta(days=10),
                  etapes=[Etape(id="e1", nature="temps", geste="Regarder l'étiquette 10 s", duree_min=10)])
    eid = b.brouillon(SOPHIE, p)
    avant = len(b.m.evenements())
    vraie = Banc._transition

    def panne(self, eid_, vers, par, raison):
        if vers == "PROPOSE":
            raise RuntimeError("coupure simulée")
        return vraie(self, eid_, vers, par, raison)
    monkeypatch.setattr(Banc, "_transition", panne)
    with pytest.raises(RuntimeError):
        b.proposer(SOPHIE, eid, 0)
    assert len(b.m.evenements()) == avant and b.etat(eid) == "BROUILLON" and b.version(eid) == 0


def test_retrait_puis_reacceptation_ne_consomme_pas_deux_fois_une_offre():
    """Pauline (capacité 1) accepte l'essai A, se retire, accepte l'essai B, puis tente de réaccepter A : refusé."""
    m = Monde()
    b = m.b
    b.publier_offre("s02", "lieu", "Un coin de vitrine éclairé", 1, J, J + timedelta(days=30), duree_max_min=20)  # A reste adaptable
    a, va = m.essai()
    bb, vb = m.essai("Un autre critère : la couleur est-elle perçue comme « bio » ?")
    assert m.contributeurs(a)["e2"] == PAULINE and m.contributeurs(bb)["e2"] == PAULINE
    b.decider(PAULINE, a, va, True)
    b.retirer(PAULINE, a)
    assert b.etat(a) == "A_ADAPTER" and b.reservations(m.pauline) == 0     # le retrait libère la place
    b.decider(PAULINE, bb, vb, True)
    assert b.reservations(m.pauline) == 1
    with pytest.raises(Conflit, match="capacité"):
        b.decider(PAULINE, a, va, True)                                     # réaccepter A dépasserait la capacité
    assert b.reservations(m.pauline) == 1

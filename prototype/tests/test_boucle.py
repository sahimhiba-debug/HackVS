"""LA BOUCLE Club Pulse, de bout en bout dans le domaine (sans HTTP) :
besoin déclaré → opportunité détectée et expliquée → le bénéficiaire propose un essai → la personne invitée déclare sa
disponibilité en acceptant → perturbation (60 → 20 min) → adaptation → essai → observation → confirmation → droits de
réutilisation → MÉMOIRE → une découverte SUIVANTE, pour un autre membre, qui n'existait pas avant.
Et les variantes où la mémoire ne doit PAS servir : contestée, non partagée, négative. Données FICTIVES."""
from datetime import timedelta

import pytest

from app.matching import organisation
from app.taxonomy import charger_taxonomie
from intelligence import memoire_club
from intelligence import monde_demo as md
from intelligence.detection import scanner
from intelligence.essai import Banc
from intelligence.explication import expliquer
from intelligence.observateur import observer
from intelligence.passerelle import CRITERE_SUGGERE, brouillon
from plateforme.memoire import Memoire

TAX = charger_taxonomie()
S, M, NICO, CLAUDIA = md.SOPHIE, md.MARKUS, md.NICOLAS, "s15"


class Monde:
    def __init__(self):
        self.r = md.construire(True, md.BESOIN_ALLEMAGNE, md.BESOINS_SUIVANTS)
        e = observer(self.r, TAX)
        par_id = self.r.par_id()
        self.b = Banc(Memoire(), lambda: self.r.aujourd_hui, lambda pid: organisation(par_id[pid]) or pid,
                      lambda porteur, cand: e.exclusion(par_id[porteur], par_id[cand], None, introduction=False))
        j = self.r.aujourd_hui
        self.b.publier_offre(CLAUDIA, "competence", "Conseil pour un lancement de produit en Allemagne", 2, j, j + timedelta(days=30),
                             duree_max_min=60)

    def opportunites(self, pour: str) -> list:
        mem = memoire_club.reutilisables_par_le_club(memoire_club.souvenirs(self.b))
        return [o for o in scanner(self.r, TAX, souvenirs=mem)["opportunites"] if o.beneficiaire == pour]

    def essai_jusqu_a_l_observation(self, qualification="positif"):
        o = self.opportunites(S)[0]
        p = brouillon(o, self.r, TAX, self.r.aujourd_hui)
        eid = self.b.brouillon(S, p)
        v = self.b.modifier_brouillon(S, eid, 0, p.model_copy(update={"critere": CRITERE_SUGGERE}))   # adoptée EXPLICITEMENT
        v = self.b.proposer(S, eid, v)
        self.b.decider(M, eid, v, True)
        offre = self.b.offre_de(eid, self.b.protocole(eid).etapes[0])
        self.b.modifier_offre(M, offre.id, duree_max_min=20)
        alt = next(a for a in self.b.alternatives(eid) if a["type"] == "raccourcir")
        self.b.choisir_alternative(S, eid, v, alt["id"])
        self.b.decider(M, eid, self.b.version(eid), True)
        self.b.lancer(S, eid, self.b.version(eid))
        self.b.constater(S, eid, "e1")
        self.b.observer(S, eid, "Markus m'a présenté deux distributeurs à contacter avant le salon.", qualification,
                        "un échange de 20 minutes, une seule gamme, avant le salon de Munich")
        return o, eid


def test_la_boucle_complete_rend_possible_une_decouverte_qui_n_existait_pas():
    m = Monde()
    assert m.opportunites(NICO) == []                                       # AVANT : aucun « pourquoi maintenant »
    o, eid = m.essai_jusqu_a_l_observation()
    assert o.type == "SUIVI" and {r.membre for r in o.roles} == {S, M}
    assert m.b.protocole(eid).origine["concepts"] == ["export_allemagne"]
    m.b.aviser(M, eid, 1, "confirme")
    m.b.reutilisation(S, eid, "club", "nom")
    assert m.opportunites(NICO) == []                                       # Markus n'a pas encore choisi : rien ne sort
    m.b.reutilisation(M, eid, "club", "nom")
    souv = memoire_club.souvenirs(m.b)[0]
    assert souv["statut"] == "confirmee" and souv["niveau"] == "club" and souv["contributeurs"] == [M]
    apres = m.opportunites(NICO)                                            # APRÈS : la mémoire rend la découverte possible
    assert len(apres) == 1 and {r.membre for r in apres[0].roles} == {NICO, M}
    assert any(s.source == "memoire" for s in apres[0].signaux) and "mémoire du Club" in apres[0].mecanismes
    pourquoi = expliquer(apres[0], m.r, TAX, {}, memoire_club.accessibles(memoire_club.souvenirs(m.b), NICO))
    assert any(x["statut"] == "CONFIRMÉ" for x in pourquoi["preuves"]) and pourquoi["confiance"]["effet_memoire"]


def test_stefan_n_est_jamais_propose_a_nicolas_aucune_langue_commune():
    m = Monde()
    _, eid = m.essai_jusqu_a_l_observation()
    m.b.aviser(M, eid, 1, "confirme")
    for x in (S, M):
        m.b.reutilisation(x, eid, "club", "anonyme")
    assert all("s16" not in {r.membre for r in o.roles} for o in m.opportunites(NICO))


@pytest.mark.parametrize("variante", ["contestee", "participants", "negative", "non_confirmee"])
def test_la_memoire_ne_sert_pas_hors_de_son_perimetre(variante):
    m = Monde()
    _, eid = m.essai_jusqu_a_l_observation("negatif" if variante == "negative" else "positif")
    if variante == "contestee":
        m.b.aviser(M, eid, 1, "conteste", "je n'ai présenté qu'un seul distributeur")
    elif variante != "non_confirmee":
        m.b.aviser(M, eid, 1, "confirme")
    m.b.reutilisation(S, eid, "club", "nom")
    m.b.reutilisation(M, eid, "participants" if variante == "participants" else "club", "nom")
    assert m.opportunites(NICO) == []                                       # aucune découverte fabriquée
    souv = memoire_club.souvenirs(m.b)
    # la personne aidée, elle, retrouve SA mémoire — et un essai négatif devient un RISQUE, pas une preuve
    o = m.opportunites(S)
    if o and variante == "negative":
        pourquoi = expliquer(o[0], m.r, TAX, {}, memoire_club.accessibles(souv, S))
        assert any("jugé « negatif »" in x for x in pourquoi["risques"])


def test_le_brouillon_n_ecrit_pas_le_critere_a_la_place_du_beneficiaire():
    m = Monde()
    o = m.opportunites(S)[0]
    p = brouillon(o, m.r, TAX, m.r.aujourd_hui)
    assert p.critere == "" and p.origine["critere_suggere"] == CRITERE_SUGGERE
    assert p.echeance == next(e.le for e in m.r.evenements if e.id == o.evenement)   # avant le salon de Munich
    assert all(e.invitation and e.offre_id is None for e in p.etapes)        # aucune disponibilité supposée
    eid = m.b.brouillon(S, p)
    from intelligence.erreurs import Invalide
    with pytest.raises(Invalide, match="critère"):
        m.b.proposer(S, eid, 0)                                             # publier sans critère : refusé

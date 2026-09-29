"""Invariants du banc d'essai (Activation Engine), vérifiés par MARCHES ALÉATOIRES — graines fixes, donc rejouables.
Portés de l'ancien moteur avant son retrait : des gestes humains et des perturbations au hasard (accepter, décliner,
avec une version à jour ou périmée ; se retirer ; réduire ou retirer une offre ; modifier le protocole ; choisir une
adaptation ; lancer ; constater ; observer ; confirmer ou contester ; partager ; annuler ; laisser passer le temps),
puis, après CHAQUE pas, les propriétés qui ne doivent jamais être violées — relues dans le JOURNAL, pas dans l'état
calculé par le banc. Un refus métier (ErreurMetier) est un comportement normal ; toute autre exception fait échouer.
Données FICTIVES (monde de démonstration)."""
import random
from datetime import timedelta

import pytest

from app.matching import organisation
from app.taxonomy import charger_taxonomie
from intelligence import memoire_club
from intelligence import monde_demo as md
from intelligence.detection import scanner
from intelligence.erreurs import ErreurMetier
from intelligence.essai import FINAUX, TRANSITIONS, Banc, Etape, Protocole
from intelligence.observateur import observer
from intelligence.passerelle import CRITERE_SUGGERE, brouillon
from plateforme.memoire import Memoire

TAX = charger_taxonomie()
ARRET = {"ANNULE", "EXPIRE", "IMPOSSIBLE"}
PORTEURS = ("s01", "d01", "s10", "s02")
OFFRES = [  # (auteur, nature, quoi, durée max, capacité, jours de validité, capacité déclarée) — fictives
    ("s15", "competence", "Conseil pour un lancement de produit en Allemagne", 60, 2, 30, "export_allemagne"),
    ("s14", "temps", "Regard neuf de distributeur sur une étiquette", 15, 2, 20, None),
    ("d01", "temps", "Relire un support imprimé en allemand", 15, 2, 20, None),
    ("s01", "lieu", "Un présentoir éclairé sur mon stand", None, 1, 10, None),
    ("s06", "competence", "Organiser un transport frigorifique", 30, 1, 25, "transport_frigorifique"),
    ("s07", "objet", "Des échantillons d'emballage", None, 2, 15, None),
    ("s11", "competence", "Regarder un tableau de ventes", 30, 3, 40, None),
]


class Monde:
    def __init__(self, rnd: random.Random):
        self.rnd = rnd
        self.r = md.construire(True, md.BESOIN_ALLEMAGNE, md.BESOINS_SUIVANTS)
        e = observer(self.r, TAX)
        par_id = self.r.par_id()
        self.b = Banc(Memoire(), lambda: self.r.aujourd_hui, lambda pid: organisation(par_id[pid]) or pid,
                      lambda porteur, cand: e.exclusion(par_id[porteur], par_id[cand], None, introduction=False))
        j = self.r.aujourd_hui
        for auteur, nature, quoi, duree, cap, jours, concept in OFFRES:
            self.b.publier_offre(auteur, nature, quoi, cap, j, j + timedelta(days=jours), duree_max_min=duree, concept=concept)
        o = next(o for o in scanner(self.r, TAX)["opportunites"] if o.beneficiaire == md.SOPHIE)   # le cas de la démo
        p = brouillon(o, self.r, TAX, j).model_copy(update={"critere": CRITERE_SUGGERE})
        self.b.brouillon(md.SOPHIE, p)

    def jour(self):
        return self.r.aujourd_hui

    def nouvel_essai(self) -> None:
        porteur = self.rnd.choice(PORTEURS)
        natures = self.rnd.sample(["temps", "competence", "lieu", "objet"], self.rnd.choice([1, 2]))
        p = Protocole(question=f"Question {len(self.b.essais())} de {porteur}", critere="ce qu'on observera", objet="un support",
                      echeance=self.jour() + timedelta(days=self.rnd.choice([3, 8, 12])),
                      etapes=[Etape(id=f"e{i + 1}", nature=n, geste=f"geste {n}", duree_min=self.rnd.choice([10, 15, 30]))  # type: ignore[arg-type]
                              for i, n in enumerate(natures)])
        self.b.brouillon(porteur, p)


def _geste(m: Monde, rnd: random.Random) -> None:
    b = m.b
    essais = b.essais()
    eid = rnd.choice(essais)
    porteur, p, v = b.porteur(eid), b.protocole(eid), b.version(eid)
    gens = [e.contributeur for e in p.etapes if e.contributeur]
    naturels = NATURELS.get(b.etat(eid), ())
    nom = rnd.choice(naturels) if naturels and rnd.random() < 0.7 else rnd.choices(list(POIDS), weights=list(POIDS.values()))[0]
    if nom == "proposer":
        b.proposer(porteur, eid, v)
    elif nom == "decider" and gens:
        b.decider(rnd.choice(gens), eid, v if rnd.random() < 0.85 else max(0, v - 1), rnd.random() < 0.75)
    elif nom == "retirer" and gens:
        b.retirer(rnd.choice(gens), eid)
    elif nom == "reduire_offre":                    # surtout une offre dont CET essai dépend (la perturbation qui compte)
        utilisees = [o for e in p.etapes if (o := b.offre_de(eid, e) if e.contributeur else None) is not None]
        o = rnd.choice(utilisees) if utilisees and rnd.random() < 0.7 else rnd.choice(b.offres())
        b.modifier_offre(o.auteur, o.id, **rnd.choice([{"duree_max_min": rnd.choice([5, 10, 20])}, {"capacite": 1},
                                                      {"au": m.jour() + timedelta(days=2)}]))
    elif nom == "retirer_offre":
        o = rnd.choice(b.offres())
        b.retirer_offre(o.auteur, o.id)
    elif nom == "modifier":
        e = rnd.choice(p.etapes)
        b.modifier(porteur, eid, v, **rnd.choice([{"durees": {e.id: rnd.choice([5, 20, 45])}}, {"critere": "un autre critère"},
                                                  {"pourquoi": "un mot du contexte"}]))
    elif nom == "adapter":
        alts = b.alternatives(eid) if b.etat(eid) == "A_ADAPTER" else []
        if alts:
            b.choisir_alternative(porteur, eid, v, rnd.choice(alts)["id"])
    elif nom == "lancer":
        b.lancer(porteur, eid, v)
    elif nom == "constater":
        b.constater(porteur, eid, rnd.choice(p.etapes).id)
    elif nom == "observer":
        b.observer(porteur, eid, "ce qui s'est passé", rnd.choice(["positif", "negatif", "mitige", "non_concluant"]), "une fois")
    elif nom == "aviser" and gens:
        obs = b._evs(eid, "OBSERVATION")
        b.aviser(rnd.choice(gens), eid, obs[-1].donnees["revision"] if obs else 1, rnd.choice(["confirme", "confirme", "confirme", "conteste"]),
                 "pas tout à fait")
    elif nom == "reutilisation":
        b.reutilisation(rnd.choice(sorted(b.participants(eid))), eid, rnd.choice(["moi", "participants", "club", "club", "club"]), "nom")
    elif nom == "annuler":
        b.annuler(porteur, eid, "le porteur arrête")
    elif nom == "avancer":
        m.r.aujourd_hui = m.jour() + timedelta(days=rnd.choice([1, 3, 9, 20]))
        b.echeances()
    elif nom == "nouvel":
        m.nouvel_essai()


# le plus souvent un geste qui a du sens dans l'état de l'essai (sinon la marche ne lancerait presque jamais rien),
# parfois n'importe lequel (les refus métier sont aussi à exercer)
NATURELS = {"BROUILLON": ("proposer",), "PROPOSE": ("decider", "decider", "modifier", "retirer"),
            "AUTORISE": ("lancer", "lancer", "decider", "retirer", "reduire_offre"), "A_ADAPTER": ("adapter", "adapter", "decider"),
            "EN_COURS": ("constater", "constater", "retirer", "reduire_offre"), "CONTRIBUTION_RECUE": ("observer",),
            "OBSERVEE": ("aviser", "aviser", "reutilisation", "reutilisation", "reutilisation"), "RESULTAT_INCONNU": ("observer",)}
POIDS = {"proposer": 3, "decider": 8, "retirer": 1, "reduire_offre": 1, "retirer_offre": 0.5, "modifier": 1.5, "adapter": 3,
         "lancer": 3, "constater": 3, "observer": 2, "aviser": 2, "reutilisation": 2, "annuler": 0.4, "avancer": 1, "nouvel": 1.5}


# ---------------------------------------------------------------------- les invariants, relus dans le journal
def _etats_dans_le_temps(b: Banc, eid: str) -> list[tuple[int, str]]:
    return [(e.seq, e.donnees["vers"]) for e in b._evs(eid, "ESSAI_ETAT")]


def _etat_avant(chrono: list[tuple[int, str]], seq: int) -> str:
    avant = [vers for s, vers in chrono if s < seq]
    return avant[-1] if avant else ""


def _verifier(b: Banc) -> None:
    for eid in b.essais():
        chrono = _etats_dans_le_temps(b, eid)
        de = ""
        for e in b._evs(eid, "ESSAI_ETAT"):                                 # I1 : transitions permises, chaîne continue
            assert e.donnees["de"] == de and e.donnees["vers"] in TRANSITIONS.get(de, set()), (eid, de, e.donnees)
            de = e.donnees["vers"]
        etat, p, porteur = b.etat(eid), b.protocole(eid), b.porteur(eid)
        if etat == "AUTORISE":                                              # I2 : autorisé ⇔ chaque accord couvre CETTE version
            assert all(x is None for x in b.couverture(eid).values()), (eid, b.couverture(eid))
        for x in b.participants(eid) - {porteur}:                           # I3 : le silence n'est jamais un accord
            assert any(a.acteurs == [x] and a.donnees["accepte"] for a in b._evs(eid, "ACCORD")), (eid, x)
        versions = b._evs(eid, "ESSAI_VERSION")
        for a in b._evs(eid, "ACCORD"):                                     # I4 : un accord porte sur la version vue
            assert a.donnees["version"] == [v.donnees["version"] for v in versions if v.seq < a.seq][-1], (eid, a.donnees)
        for r in b._evs(eid, "ACCORD", "RETRAIT"):                          # I5 : un refus, un retrait ne sont pas relancés
            if r.type == "ACCORD" and r.donnees["accepte"]:
                continue
            x = r.acteurs[0]
            if r.type == "ACCORD":
                assert not [a for a in b._evs(eid, "ACCORD") if a.acteurs == [x] and a.seq > r.seq and a.donnees["accepte"]], (eid, x)
            avant = {e["id"] for e in [v for v in versions if v.seq < r.seq][-1].donnees["protocole"]["etapes"] if e.get("contributeur") == x}
            for v in versions:
                if v.seq > r.seq:                                           # jamais redésigné(e) pour un nouveau geste
                    assert {e["id"] for e in v.donnees["protocole"]["etapes"] if e.get("contributeur") == x} <= avant, (eid, x)
        for e in b._evs(eid, "CONTRIBUTION"):                               # I6 : une contribution suppose un essai LANCÉ
            assert _etat_avant(chrono, e.seq) == "EN_COURS", (eid, _etat_avant(chrono, e.seq))
        for e in b._evs(eid, "OBSERVATION"):                                # … et une observation, des contributions reçues
            assert _etat_avant(chrono, e.seq) in ("CONTRIBUTION_RECUE", "RESULTAT_INCONNU", "OBSERVEE"), eid
        arret = next((s for s, vers in chrono if vers in ARRET), None)      # I7 : rien ne continue après un arrêt
        if arret is not None:
            assert not [e for e in b._evs(eid, "ACCORD", "CONTRIBUTION", "ESSAI_VERSION", "OBSERVATION") if e.seq > arret], eid
        fin = next((s for s, vers in chrono if vers == "OBSERVEE"), None)
        if fin is not None:
            assert not [e for e in b._evs(eid, "ACCORD", "CONTRIBUTION", "ESSAI_VERSION") if e.seq > fin], eid
        assert etat not in FINAUX or etat == de
    for o in b.offres():                                                    # I8 : une disponibilité déclarée EN acceptant
        if o.pour_essai:                                                    #      appartient à qui a accepté, pour cet essai
            assert any(a.acteurs == [o.auteur] and a.donnees["accepte"] for a in b._evs(o.pour_essai, "ACCORD")), o.id
        engages = recus = 0                                                 # I9 : jamais promise au-delà de sa capacité
        for eid in b.essais():
            etat, p = b.etat(eid), b.protocole(eid)
            recues = {x.donnees["etape"] for x in b._evs(eid, "CONTRIBUTION")}
            for e in p.etapes:
                od = b.offre_de(eid, e) if e.contributeur else None
                if od is None or od.id != o.id:
                    continue
                if e.id in recues:
                    recus += 1
                elif etat in ("AUTORISE", "EN_COURS"):
                    engages += 1
        assert engages == 0 or engages + recus <= o.capacite, (o.id, engages, recus, o.capacite)
    tous = memoire_club.souvenirs(b)                                        # I10 : la mémoire ne dit que ce qui est confirmé
    for s in tous:
        avis = {a.acteurs[0]: a.donnees["avis"] for a in b._evs(s["essai"], "AVIS") if a.donnees["revision"] == s["revision"]}
        if s["statut"] == "confirmee":
            assert s["contributeurs"] and all(avis.get(c) == "confirme" for c in s["contributeurs"]), s["essai"]
        if s["niveau"] == "club":
            assert all(b.droits(s["essai"]).get(x, {}).get("niveau") == "club" for x in b.participants(s["essai"])), s["essai"]
    for s in memoire_club.reutilisables_par_le_club(tous):
        assert s["statut"] == "confirmee" and s["niveau"] == "club" and s["qualification"] in ("positif", "mitige")


@pytest.mark.parametrize("graine", range(1, 13))
def test_marche_aleatoire_sur_le_banc(graine):
    rnd = random.Random(graine)
    m = Monde(rnd)
    for _ in range(3):
        m.nouvel_essai()
    faits = 0
    for _ in range(70):
        try:
            _geste(m, rnd)
            faits += 1
        except ErreurMetier:
            pass                                    # refus métier : attendu (transition interdite, version périmée…)
        _verifier(m.b)
    assert faits >= 10                              # la marche a réellement joué (pas seulement des refus)


def test_les_marches_atteignent_les_etats_interessants():
    """Sans cela, des invariants toujours vrais pourraient l'être parce que rien ne s'est passé."""
    vus: set[str] = set()
    for graine in range(1, 13):
        rnd = random.Random(graine)
        m = Monde(rnd)
        for _ in range(3):
            m.nouvel_essai()
        for _ in range(70):
            try:
                _geste(m, rnd)
            except ErreurMetier:
                pass
        vus |= {e.donnees["vers"] for e in m.b.m.evenements("ESSAI_ETAT")}
        vus |= {"alternative:" + a["type"] for e in m.b.m.evenements("ADAPTATION") for a in e.donnees["alternatives"]}
        vus |= {"invitation acceptée" for o in m.b.offres() if o.pour_essai}
        vus |= {f"mémoire {s['statut']}/{s['niveau']}" for s in memoire_club.souvenirs(m.b)}
    assert {"PROPOSE", "AUTORISE", "A_ADAPTER", "EN_COURS", "CONTRIBUTION_RECUE", "OBSERVEE", "IMPOSSIBLE", "EXPIRE", "ANNULE",
            "alternative:remplacer", "alternative:raccourcir", "invitation acceptée", "mémoire confirmee/club"} <= vus, vus


def test_une_mutation_de_la_regle_de_capacite_est_attrapee(monkeypatch):
    """Le filet a des mailles : si le banc oubliait les réservations, une offre à capacité 1 serait promise à deux
    essais autorisés en même temps — I9 le voit (vérifié ici sur le scénario minimal, sans hasard)."""
    monkeypatch.setattr(Banc, "reservations", lambda self, oid, sauf=None: 0)
    m = Monde(random.Random(0))
    lieu = next(o for o in m.b.offres() if o.nature == "lieu")
    for porteur in ("d01", "s10"):
        p = Protocole(question=f"Essai de {porteur}", critere="ce qu'on observera", echeance=m.jour() + timedelta(days=5),
                      etapes=[Etape(id="e1", nature="lieu", geste="un présentoir", duree_min=10)])
        eid = m.b.brouillon(porteur, p)
        v = m.b.proposer(porteur, eid, 0, {"e1": lieu.id})
        m.b.decider(lieu.auteur, eid, v, True)
        assert m.b.etat(eid) == "AUTORISE"
    with pytest.raises(AssertionError):
        _verifier(m.b)

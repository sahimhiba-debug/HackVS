"""F32 — un acquittement de l'animation (« vu, on vit avec cet état incertain ») tombe quand le MONDE change, pas sur
une trace qui ne change rien à ce que le Club peut faire. Avant (expérience E2) : activer un passe juré — ou raconter
une capacité, ou un « non » à une demande — remettait l'élément dans la file de l'animation. Données FICTIVES."""
from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo

TAX = charger_taxonomie()


def _acquitte():
    c = Demo(TAX).club
    c.banc.BUDGET_NOEUDS = 1                                     # recherche bornée : un état incertain à acquitter
    f = next(i.finalite for i in c.capacites.projeter() if i.recherche_bornee)
    assert c.acquitter_recherche(f).acquittee_le == c.jour
    return c, f


def _acquittee(c, f):
    return next(i for i in c.capacites.projeter() if i.finalite == f).acquittee_le


def test_un_passe_jure_un_recit_ou_un_non_ne_changent_pas_le_monde():
    c, f = _acquitte()
    p = c.emettre_pass_jure(md.MARKUS, 15)
    c.utiliser_pass_jure(p["jeton"])                             # scénario exact de l'audit (E2)
    c.raconter_capacite(f)                                       # une trace IA (forme déterministe ici)
    c.basculer_ia(False)                                         # l'interrupteur
    c.activer_compte(c.coffre.code_invitation(md.SOPHIE))        # un compte activé
    ask = next((a for _, a in c.asks_pour(md.PAULINE)), None)
    if ask:
        c.repondre_ask(md.PAULINE, ask, False)                   # un « non » : sans effet sur personne
    assert _acquittee(c, f) == c.jour


def test_un_fait_du_monde_fait_tomber_l_acquittement():
    """Contre-épreuve : une offre publiée change ce que le Club peut faire — l'état incertain est à revoir."""
    c, f = _acquitte()
    c.banc.publier_offre(md.PAULINE, "objet", "Un minibus de 14 places", 1, c.jour, c.jour, attributs={"places": 14})
    assert _acquittee(c, f) is None

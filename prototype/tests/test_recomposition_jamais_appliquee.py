"""Claim du README : « une recomposition est calculée, JAMAIS appliquée ». Jusqu'ici seulement implicite (la capacité
restait DÉGRADÉE jusqu'au consentement) : ce test l'affirme directement. Lire le registre, la console, les reçus et les
demandes autant de fois qu'on veut n'écrit AUCUN fait ; la pièce proposée ne devient pas consentie ; la capacité ne
redevient ACTIVE que par le geste de la personne qui offre cette pièce. Données FICTIVES."""
from datetime import timedelta

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.essai import Plage

TAX = charger_taxonomie()
A = "delegation_acheteurs"


def test_une_recomposition_proposee_n_est_jamais_appliquee_par_une_lecture():
    c = Demo(TAX).club
    ask = c.capacites.instance(c.capacites.patron(A)).ask
    c.repondre_ask(md.PAULINE, ask.id, True, {"places": 14})
    c.banc.publier_offre(md.MARKUS, "objet", "Bus de 20 places", 1, c.jour, c.jour + timedelta(days=3), attributs={"places": 20},
                         plages=[Plage(jour=md.JOUR_SCENE + timedelta(days=1), debut="13:00", fin="18:00")])
    inst = c.retirer_consentement(md.PAULINE, A)
    assert inst.statut == "DEGRADED" and inst.recomposition["type"] == "consentir"
    faits = len(c.journal.evenements())
    for _ in range(3):                                          # tout ce que les écrans lisent, plusieurs fois
        c.capacites.projeter()
        c.vues_capacites.instance(c.capacites.instance(c.capacites.patron(A)))
        c.capacites.recus(md.MARKUS)
        c.asks_pour(md.MARKUS)
    assert len(c.journal.evenements()) == faits                  # aucune lecture n'écrit
    i = c.capacites.instance(c.capacites.patron(A))
    assert i.statut == "DEGRADED"                                # proposée, pas appliquée
    assert [r for r in c.capacites.recus(md.MARKUS) if r["finalite"] == A] == []      # Markus n'a RIEN consenti
    assert c.consentir_capacite(md.MARKUS, A).statut == "ACTIVE"                       # seul son geste l'applique

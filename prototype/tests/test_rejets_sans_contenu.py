"""F33 — aucun fragment produit par le modèle ne sort par un message de rejet : ni dans les journaux applicatifs, ni
dans `APPEL_IA`, ni dans `erreur` / `rejets`, ni dans la consigne de nouvel essai renvoyée au modèle. Avant : « champs
non demandés : [clés inventées] », « concept hors vocabulaire : <concept inventé> »… Données FICTIVES."""
import json
import logging
import re
from pathlib import Path

from app.taxonomy import charger_taxonomie
from intelligence import monde_demo as md
from intelligence.demo import Demo
from intelligence.ia import Intelligence
from tests.modele_scripte import ModeleScripte

TAX = charger_taxonomie()
CANARI = "CANARIzq7f3a"
HOSTILES = {
    "cle_inventee": {"extraire_piece": {"attributs": {"places": 14}, CANARI: 1}},
    "concept_invente": {"extraire_piece": {"attributs": {"places": 14}}, "normaliser_offre": {"concept": CANARI, "extrait": None}},
    "pas_du_json": {"extraire_piece": f"{CANARI} ceci n'est pas du JSON"},
}


def test_un_rejet_ne_recopie_jamais_la_sortie_du_modele(caplog):
    caplog.set_level(logging.DEBUG)
    for nom, roles in HOSTILES.items():
        m = ModeleScripte(**roles)
        c = Demo(TAX, ia=Intelligence(TAX, m)).club
        ask = next(a for i, a in c.asks_pour(md.PAULINE) if a.startswith("delegation_acheteurs"))
        # la compétence d'une pièce passe aussi par NORMALIZE : on l'exerce directement sur le texte du membre
        c.proposer_reponse(md.PAULINE, ask, "Mon minibus a 14 places.")
        c.roles_ia.normaliser("Interprétation français allemand")
        rejets = [a for a in c.ia.appels if a.rejets or a.erreur]
        assert rejets, nom                                                             # non vacueux : il y a eu rejet
        traces = json.dumps([a.model_dump() for a in c.ia.appels], ensure_ascii=False)
        journal = json.dumps([e.donnees for e in c.journal.evenements("APPEL_IA")], ensure_ascii=False)
        relances = " ".join(msg for _, _, msg in m.recus)
        assert CANARI not in traces and CANARI not in journal, nom
        assert CANARI not in relances, nom                                             # jamais renvoyé au modèle
        assert CANARI not in caplog.text, nom


def test_aucun_message_de_rejet_n_est_construit_avec_la_sortie():
    """Garde structurelle : un rejet se lève avec une catégorie FIXE (aucune f-string), et ce qui est gardé passe par
    `raison_sans_contenu`."""
    racine = Path(__file__).resolve().parents[1] / "intelligence"
    for f in ("ia.py", "roles_ia.py"):
        src = (racine / f).read_text(encoding="utf-8")
        assert not re.search(r"raise (Rejet|ValueError)\(f[\"']", src), f
        assert "rejets.append(raison_sans_contenu(e))" in src or f != "ia.py"

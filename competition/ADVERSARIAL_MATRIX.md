# Matrice adversariale — les 30 scénarios du brief

| # | Scénario | Couvert | Où (test ou mesure) |
|---|---|---|---|
| 1 | Démarrage à froid | oui | `test_explications.py` (nouveau membre, réciprocité, « premier lien ») ; scène étape 2 |
| 2 | Correspondance réciproque | oui | `test_explications.py` (Nadia ↔ Inès) ; scène étape 4 (Markus) |
| 3 | Pas d'intérêt réciproque | oui | `test_explications.py` (financement : non établie, vérifié indépendamment) |
| 4 | Violation de confidentialité | oui | `test_confidentialite_reseau.py` (brouillons), `test_reseau.py` (intermédiaire), `test_scene.py` (champs privés, consentement dans le graphe) |
| 5 | Consentement manquant | oui | moteur (écarté, non nommé) ; scénarios S04–S05 ; `test_explications.py` |
| 6 | Relation ancienne | oui | `test_adversarial_reseau.py::test_relation_expiree_devient_a_raviver` |
| 7 | Profil ancien | oui | inconnue « profil non mis à jour » (dimensions, micro-cercle) ; `test_scene.py` |
| 8 | Preuves contradictoires | partiel | registre : un statut différent n'écrase jamais silencieusement (`test_plateforme.py`) ; pas de fusion de sources contradictoires |
| 9 | Membre sur-sollicité | partiel | budget par membre (solveur) ; le benchmark ne discrimine PAS ce biais (dit dans 06/16) |
| 10 | Membre isolé | oui | benchmark (isolés restants) ; simulation « premier lien » |
| 11 | Recommandations répétées | oui | relance refusée jamais reproposée (`test_cycle.py`) ; aucune paire répétée d'une soirée à l'autre |
| 12 | Chambre d'écho | oui (synthétique) | benchmark : similarité et ami d'ami créent moins de ponts |
| 13 | Opportunité par un lien faible | oui | présentation via un contact suivi (`test_cycle.py`, scène étape 11) |
| 14 | Pont | oui | simulation : pont = relie deux groupes existants (`test_scene.py`) |
| 15 | Capacité | oui | une rencontre par tour, budget par membre ; validateur L5 indépendant |
| 16 | Collision d'événements | **non** | pas de calendrier multi-événements dans le prototype |
| 17 | Aucun candidat | oui | S08, S09 ; « Japon » (scène étape 5) |
| 18 | Faux candidat très confiant | oui | preuve déduite → « partielle, à vérifier » (Claudia) ; profil ancien signalé |
| 19 | Rejet humain | oui | introduction déclinée, relance refusée (`test_reseau.py`, `test_cycle.py`) |
| 20 | Retrait d'un membre | oui | retrait du consentement : relations en attente annulées (`test_parcours.py`) |
| 21 | Membre indisponible | oui | contrainte « disponibilité » recalculée (validateur de domaine) |
| 22 | Consentement supprimé | oui | idem 20 ; invisible par défaut (`test_explications.py`) |
| 23 | Expiration de la relation | oui | idem 6 |
| 24 | Opportunité devenue ancienne | oui | `test_adversarial_reseau.py::test_opportunite_devenue_ancienne_est_signalee` |
| 25 | Suivi manqué | oui | état SUIVI_EN_ATTENTE à 10 jours (`test_reseau.py`, frontière 9/10) |
| 26 | Perturbation du réseau | oui | test de stress : retrait de N membres puis réparation (S14, S15) |
| 27 | Prompt malveillant visant des données privées | partiel | profils = données non fiables, injections signalées (`test_parcours.py`) ; aucune coordonnée n'existe à exfiltrer |
| 28 | Agent tentant un outil non autorisé | oui | MCP : 401 sans jeton, portée insuffisante refusée (`test_mcp.py`) |
| 29 | Preuve périmée | oui | S17 (blocage) |
| 30 | Historique contradictoire | oui | `test_adversarial_reseau.py` (refus ancien vs relation vivante) — défaut trouvé et corrigé (FAILURES #20) |

Couverts : 26 · partiels : 3 (8, 9, 27) · non couverts : 1 (16).

# 03 — Solution (ce qui existe dans le prototype)

| Capacité | Où la voir | Preuve |
|---|---|---|
| Adhésion : profil proposé puis validé, invisible par défaut | `/demo/stage` étape 2 ; `/api/demo/rejoindre` | `test_explications.py` |
| Candidats avec pourquoi / pourquoi maintenant / comment nous savons / inconnu | étape 4 ; onglet « Mes besoins » | `test_explications.py` (mutation) |
| Réciprocité PROUVÉE (même moteur en sens inverse) | étape 4 | `reciprocite_prouvee` |
| Abstention quand les preuves manquent | étape 5 | `test_scene.py`, scénarios S03/S08/S09 |
| Introduction en double accord, jamais de coordonnées | étapes 6–7 | `store.py`, `test_parcours.py` |
| Ligne de temps de la relation (une seule source de vérité) | étape 8 | `test_reseau.py` |
| Suivi seulement avec une raison nouvelle et prouvée | étape 9 | `test_cycle.py`, `test_reseau.py` |
| Opportunité ≠ résultat | étape 10 | états dérivés |
| Présentation via un intermédiaire, proposée d'abord à lui | étape 11 | `test_reseau.py` |
| Micro-cercle explicable avec inconnues | étape 11 | `cercles.py`, `test_scene.py` |
| Simulation avant / après | étape 12 | `reseau.simuler` |
| Boîte réseau (actions possibles maintenant) | onglet « Suivi » | `test_reseau.py` |
| Moteur de décision : spécification, solveur, validation L0–L8, critique, gardien, certificat, rejeu | `/decision` | `eval_decisions.py` (20/20) |
| Cycle des soirées : plan optimisé, relances à 10 jours, croissance | `/cycle` | `test_cycle.py` |

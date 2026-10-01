# ADR 0004 — Machine d'états explicite pour l'activation

> **REMPLACÉE (01.10.2026)** : le module décrit (`intelligence/activation.py`) a été retiré avec l'ancien moteur. Voir [ADR/README.md](README.md).

Statut : **accepté** (prototype). Date : 2026-09-29.

## Contexte
Une activation implique plusieurs personnes, des accords privés, des refus, des silences, des délais, des pauses et
des annulations. Un booléen « fait / pas fait » ne dit ni pourquoi, ni quoi faire ensuite.

## Décision
`intelligence/activation.py` : table `TRANSITIONS` explicite ; toute transition passe par `_transition`, qui refuse
une transition non listée (`Conflit`, 409). États de résultat distincts : CONFIRMÉ, PARTIEL, NÉGATIF, INCONNU (21 jours
sans déclaration → INCONNU, jamais « réussi »). Refus ou silence (4 jours) → BLOQUÉE → REPLANIFICATION →
ALTERNATIVE_PROPOSÉE ou ABANDONNÉE (avec la raison et la levée minimale). Budget d'attention : 2 sollicitations
ouvertes par personne. Chaque commande est atomique.

## Conséquences
+ Invariants I1–I7 vérifiés après chaque pas de 25 marches aléatoires rejouables (`tests/test_invariants.py`).
+ Replanification : complète et juste face à un oracle par force brute (198/198, 198/198 ; `eval/benchmark_pulse.py`).
− La table est le contrat : ajouter un état exige de revoir les invariants (documenté dans ARCHITECTURE § 5).

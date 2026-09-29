# ADR 0003 — Réseau pseudonymisé et rendu par spectateur

Statut : **accepté** (prototype). Date : 2026-09-29.

## Contexte
Un même fait (une opportunité, une activation) doit être montré différemment au bénéficiaire, à une personne
sollicitée, à un autre membre et au Club — sans dupliquer de logique.

## Décision
Le moteur calcule sur le réseau pseudonymisé. Chaque écran est une PROJECTION (`intelligence/vues.py`) rendue pour un
`Spectateur` par `politique.Rendu` (nom, organisation, contact, texte). La politique est déterministe : portées
`PRIVE`, `CLUB_DECOUVRABLE`, `RELATIONS`, `SUR_CONSENTEMENT`, `ACTIVATION`, `PUBLIC` ; consentement ORIENTÉ
(A a accepté d'être vu par B ≠ B par A) ; agrégats k-anonymes (k = 3). Qui a décliné n'est montré à personne.

## Conséquences
+ Une seule vérité, plusieurs vues ; la confidentialité se teste comme une propriété (tirages aléatoires).
+ Le banc de confidentialité a trouvé un vrai défaut (le graphe d'évolution nommait qui avait décliné) : corrigé.
− Toute nouvelle vue doit passer par `Rendu` : c'est une convention, pas une contrainte du typage (risque résiduel,
  couvert par l'audit des 754 écrans de `eval/benchmark_pulse.py`).

# ADR 0006 — Un seul point d'entrée IA, repli déterministe déclaré, sortie non fiable

Statut : **accepté** (prototype). Date : 2026-09-29.

## Contexte
L'IA doit améliorer la compréhension et la rédaction sans jamais décider, sans jamais voir une identité, et sans que
sa panne arrête le produit.

## Décision
`Intelligence` est l'unique point d'entrée des quatre tâches ; le fournisseur est choisi UNE fois
(`depuis_environnement`, seul endroit qui construit `Apertus`, vérifié par test). Chaque sortie est une ENTRÉE NON
FIABLE : schéma, vocabulaire fermé, extraits mot pour mot, fidélité aux faits, rejet de toute donnée personnelle ;
sinon repli déterministe, VISIBLE (`AppelIA.repli`). Nouvel essai borné (3, recul exponentiel + gigue), disjoncteur
(3 pannes → 60 s). Seule `ErreurFournisseur` est rattrapée : un bogue de notre code n'est pas déguisé en panne.
Prompts versionnés (`prompts/*_v1.md`), version tracée dans chaque appel.

## Conséquences
+ Le produit fonctionne sans clé, et le dit ; la maquette de test respecte le même contrat que le vrai client (test).
+ Relire une page ne rappelle pas le modèle (message mémorisé par sollicitation : défaut corrigé).
− Le repli par règles comprend moins bien les formulations libres (7/8 sur le banc : « cybersecurity » en anglais
  non reconnu) — c'est la valeur attendue d'Apertus, à mesurer.

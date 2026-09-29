# ADR 0005 — Journal d'événements comme source de vérité du cycle de vie

Statut : **accepté** (prototype). Date : 2026-09-29.

## Contexte
Le Club doit pouvoir dire ce qui s'est passé, qui l'a fait, quand et pourquoi — et la démonstration doit être
rejouable à l'identique.

## Décision
`plateforme/memoire.py` : table SQLite en ajout seul ; `seq` ordonne ; l'identifiant est l'empreinte du contenu
(un événement rejoué est ignoré : idempotence) ; l'état d'une activation est le repli de ses événements ; le plan est
versionné. Chaque transition porte son agent et sa raison. Les commandes écrivent dans une transaction (tout ou rien).

## Ce que ce n'est PAS (honnêtement)
- Pas un « event sourcing » complet : notes privées, préférences, coffre et sessions sont en mémoire du processus.
- Pas de numéro de schéma par événement : une évolution de format exigerait un « upcaster » (à ajouter avant tout
  stockage durable de production).
- Pas de chaînage cryptographique : l'accès au fichier SQLite permet de le modifier.
- Pas d'instantanés : les projections sont recalculées par repli (suffisant à l'échelle d'un club, non mesuré au-delà).

## Conséquences
+ Rejeu déterministe (même graine → même empreinte du journal) ; audit par activation dans la console.
+ La latence des appels IA est exclue du journal pour préserver le rejeu à l'octet.

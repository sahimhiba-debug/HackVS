# ADR 0002 — Coffre d'identités séparé du moteur

Statut : **accepté** (prototype). Date : 2026-09-29.

## Contexte
Le moteur doit raisonner sur « qui peut aider qui » sans qu'un bogue, un journal ou un modèle de langage puisse
divulguer une identité.

## Décision
`intelligence/identite.py::Coffre` détient seul noms, courriels, organisations. Il fournit des pseudonymes stables
pour un import (`MEMBRE-xxx`, numérotés dans l'ordre des identifiants internes, eux-mêmes opaques), des codes
d'invitation (HMAC-SHA256 du secret, 6 caractères), et `pseudonymiser(profil)` qui nettoie
aussi les textes libres (`nettoyer` : courriels, téléphones, URL, noms, mots de l'organisation). Le secret est
OBLIGATOIRE (≥ 16 octets ; ≥ 32 caractères par la configuration) : aucune valeur par défaut.

## Alternatives écartées
- Colonnes chiffrées dans les profils : le moteur verrait encore les champs, et les journaux aussi.
- Anonymisation au moment de l'affichage seulement : une fuite côté serveur (journal, modèle) resterait possible.

## Conséquences
+ Le moteur, le journal et l'IA ne voient que des pseudonymes (test : aucun nom ni courriel dans les profils du moteur).
+ Supprimer une personne = la supprimer du coffre (`Coffre.supprimer`) : le journal ne contient que son pseudonyme.
− Démonstration : coffre en mémoire du processus (perdu au redémarrage). Production : magasin séparé, chiffré, avec
  contrôle d'accès distinct.
− `nettoyer` repose sur les identités connues du coffre : un nom propre de tiers inconnu écrit en texte libre passe.

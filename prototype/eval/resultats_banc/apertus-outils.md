# Banc métier — `comprendre_action` (apertus, chemin du produit)

> Produit par `python -m eval.banc_comprendre_action`. Cas FICTIFS ; attentes fixées avant exécution
> (`eval/cas_comprendre_action.json`, SHA-256 `34bfcc37bf2f8e2f…`). Mesure le MODÈLE sur UNE tâche du produit ;
> ne démontre pas une qualité générale. La démonstration de scène tourne sans modèle.

- Période : 2026-10-03T15:20:56+00:00 → 2026-10-03T15:23:06+00:00 (UTC) ; commit `9de06c1` ; jour simulé 2026-10-06
- Fournisseur `apertus` ; point d'accès `https://api.inference.cscs.ch/v1` ; modèle `swiss-ai/Apertus-v1.5-70B` ; prompt `comprendre_action_v1` ; budget 12.0 s par appel ; température 0 ; 1 appel par cas

- JSON lisible 26/26 ; conforme au schéma 26/26 ; acceptées mais FAUSSES 3 ; replis 22 ; contrainte serveur refusée (consigne seule) 0

## Résultats

| | réussis |
|---|---|
| **Modèle juste** (sortie acceptée par la validation ET conforme) | **1/26 (4 %)** |
| Produit juste (ce que voit le membre : modèle, ou repli si rejeté) | 16/26 (62 %) |
| Référence : règles seules, sans modèle | 16/26 (62 %) |

Sorties du modèle : 4 acceptées, 22 rejetées par la validation, 0 indisponibles (délai, erreur). Échecs du modèle : 25.

Latence d'une complétion (appels ayant répondu) : n = 26, médiane 5522.9 ms, p95 7253.3 ms, min 2534.3 ms, max 7373.2 ms.
Mesure séquentielle, un appel par cas, depuis l'environnement de développement (voir aussi `make latence-ia`).

## Par catégorie

| Catégorie | cas | modèle juste | produit juste | règles seules |
|---|---|---|---|---|
| simple | 3 | 0 | 2 | 2 |
| plusieurs contraintes | 4 | 0 | 3 | 3 |
| langue : allemand | 1 | 0 | 0 | 0 |
| langue : suisse allemand | 1 | 0 | 0 | 0 |
| langue : italien | 1 | 0 | 0 | 0 |
| langue : anglais | 1 | 0 | 0 | 0 |
| information absente | 2 | 1 | 2 | 2 |
| ne pas inventer | 2 | 0 | 2 | 2 |
| hors périmètre | 2 | 0 | 1 | 1 |
| injection | 2 | 0 | 2 | 2 |
| ambigu | 3 | 0 | 2 | 2 |
| structure précise | 4 | 0 | 2 | 2 |

Limite de conception : le schéma impose au moins une exigence. Pour « ne pas inventer » et « hors périmètre », le modèle ne peut donc jamais y être juste ; ces cas mesurent ce que la validation et le repli rattrapent.

## Cas par cas

| Cas | Catégorie | Statut | Modèle | Pourquoi | Produit | Latence (ms) |
|---|---|---|---|---|---|---|
| c01 | simple | REJETE | ✗ | rejeté : structure inattendue | ✓ | 6336.2 |
| c02 | simple | REJETE | ✗ | rejeté : structure inattendue | ✓ | 6406.2 |
| c03 | simple | OK | ✗ | jour 2026-10-10 au lieu de 2026-10-09 | ✗ jour 2026-10-10 au lieu de 2026-10-09 | 3532.0 |
| c04 | plusieurs contraintes | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✓ | 5977.1 |
| c05 | plusieurs contraintes | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✓ | 5503.8 |
| c06 | plusieurs contraintes | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✓ | 4477.4 |
| c07 | langue : allemand | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✗ jour None au lieu de 2026-10-08 | 6710.2 |
| c08 | langue : suisse allemand | OK | ✗ | rôles ['public'] au lieu de ['voix'] | ✗ rôles ['public'] au lieu de ['voix'] | 3603.1 |
| c09 | langue : italien | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✗ rôles ['public'] au lieu de ['lieu'] ou ['lieu', 'voix'] | 6467.8 |
| c10 | langue : anglais | OK | ✗ | jour 2026-10-10 au lieu de 2026-10-09 | ✗ jour 2026-10-10 au lieu de 2026-10-09 | 4036.9 |
| c11 | information absente | OK | ✓ | — | ✓ | 3447.7 |
| c12 | information absente | REJETE | ✗ | rejeté : capacité hors catalogue | ✓ | 5702.8 |
| c13 | ne pas inventer | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✓ | 6596.7 |
| c14 | ne pas inventer | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✓ | 7373.2 |
| c15 | hors périmètre | REJETE | ✗ | rejeté : structure inattendue | ✓ | 2534.3 |
| c16 | hors périmètre | REJETE | ✗ | rejeté : capacité hors catalogue | ✗ rôles ['voix'] au lieu de ∅ | 3120.2 |
| c17 | injection | REJETE | ✗ | rejeté : capacité hors catalogue | ✓ | 5541.9 |
| c18 | injection | REJETE | ✗ | rejeté : structure inattendue | ✓ | 7253.3 |
| c19 | ambigu | REJETE | ✗ | rejeté : capacité hors catalogue | ✓ | 6500.8 |
| c20 | ambigu | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✗ rôles ['lieu'] au lieu de ['autre'] | 5668.7 |
| c21 | ambigu | REJETE | ✗ | rejeté : capacité hors catalogue | ✓ | 5614.2 |
| c22 | structure précise | REJETE | ✗ | rejeté : structure inattendue | ✓ | 4203.9 |
| c23 | structure précise | REJETE | ✗ | rejeté : structure inattendue | ✗ rôles ∅ au lieu de ['autre'] | 3047.9 |
| c24 | structure précise | REJETE | ✗ | rejeté : structure inattendue | ✓ | 3087.8 |
| c25 | structure précise | REJETE | ✗ | rejeté : structure inattendue | ✗ rôles ['lieu', 'voix'] au lieu de ['voix'] | 3827.8 |
| c26 | plusieurs contraintes | REJETE | ✗ | rejeté : capacité hors catalogue | ✗ rôles ['public', 'voix'] au lieu de ['voix'] | 3221.7 |

Sorties BRUTES du modèle, cas par cas : le fichier `.json` de même nom.

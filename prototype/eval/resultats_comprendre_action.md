# Banc métier — `comprendre_action` (Apertus, chemin du produit)

> Produit par `python -m eval.banc_comprendre_action`. Cas FICTIFS ; attentes fixées avant exécution
> (`eval/cas_comprendre_action.json`, SHA-256 `34bfcc37bf2f8e2f…`). Mesure le MODÈLE sur UNE tâche du produit ;
> ne démontre pas une qualité générale. La démonstration de scène tourne sans modèle.

- Période : 2026-10-01T19:45:11+00:00 → 2026-10-01T19:47:28+00:00 (UTC) ; commit `c11a386` ; jour simulé 2026-10-06
- Endpoint `https://api.inference.cscs.ch/v1/chat/completions` ; modèle `swiss-ai/Apertus-v1.5-70B` ; prompt `comprendre_action_v1` ; budget 12 s par appel ; 1 appel par cas

## Résultats

| | réussis |
|---|---|
| **Modèle juste** (sortie acceptée par la validation ET conforme) | **1/26 (4 %)** |
| Produit juste (ce que voit le membre : modèle, ou repli si rejeté) | 17/26 (65 %) |
| Référence : règles seules, sans modèle | 16/26 (62 %) |

Sorties du modèle : 1 acceptées, 25 rejetées par la validation, 0 indisponibles (délai, erreur). Échecs du modèle : 25.

Latence d'une complétion (appels ayant répondu) : n = 26, médiane 5756.4 ms, p95 7424.8 ms, min 2665.3 ms, max 7659.7 ms.
Mesure séquentielle, un appel par cas, depuis l'environnement de développement (voir aussi `make latence-ia`).

## Par catégorie

| Catégorie | cas | modèle juste | produit juste | règles seules |
|---|---|---|---|---|
| simple | 3 | 0 | 2 | 2 |
| plusieurs contraintes | 4 | 0 | 3 | 3 |
| langue : allemand | 1 | 0 | 0 | 0 |
| langue : suisse allemand | 1 | 1 | 1 | 0 |
| langue : italien | 1 | 0 | 0 | 0 |
| langue : anglais | 1 | 0 | 0 | 0 |
| information absente | 2 | 0 | 2 | 2 |
| ne pas inventer | 2 | 0 | 2 | 2 |
| hors périmètre | 2 | 0 | 1 | 1 |
| injection | 2 | 0 | 2 | 2 |
| ambigu | 3 | 0 | 2 | 2 |
| structure précise | 4 | 0 | 2 | 2 |

Limite de conception : le schéma impose au moins une exigence. Pour « ne pas inventer » et « hors périmètre », le modèle ne peut donc jamais y être juste ; ces cas mesurent ce que la validation et le repli rattrapent.

## Cas par cas

| Cas | Catégorie | Statut | Modèle | Pourquoi | Produit | Latence (ms) |
|---|---|---|---|---|---|---|
| c01 | simple | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✓ | 6151.3 |
| c02 | simple | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✓ | 6866.1 |
| c03 | simple | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✗ rôles ['lieu'] au lieu de ['public'] | 6889.2 |
| c04 | plusieurs contraintes | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✓ | 5931.7 |
| c05 | plusieurs contraintes | REJETE | ✗ | rejeté : capacité hors catalogue | ✓ | 5729.4 |
| c06 | plusieurs contraintes | REJETE | ✗ | rejeté : capacité hors catalogue | ✓ | 5451.4 |
| c07 | langue : allemand | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✗ jour None au lieu de 2026-10-08 | 6363.7 |
| c08 | langue : suisse allemand | OK | ✓ | — | ✓ | 3265.6 |
| c09 | langue : italien | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✗ rôles ['public'] au lieu de ['lieu'] ou ['lieu', 'voix'] | 5783.4 |
| c10 | langue : anglais | REJETE | ✗ | rejeté : capacité hors catalogue | ✗ jour None au lieu de 2026-10-09 | 3607.2 |
| c11 | information absente | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✓ | 3181.2 |
| c12 | information absente | REJETE | ✗ | rejeté : capacité hors catalogue | ✓ | 5841.3 |
| c13 | ne pas inventer | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✓ | 7659.7 |
| c14 | ne pas inventer | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✓ | 7171.3 |
| c15 | hors périmètre | REJETE | ✗ | rejeté : structure inattendue | ✓ | 2665.3 |
| c16 | hors périmètre | REJETE | ✗ | rejeté : capacité hors catalogue | ✗ rôles ['voix'] au lieu de ∅ | 3318.0 |
| c17 | injection | REJETE | ✗ | rejeté : capacité hors catalogue | ✓ | 7424.8 |
| c18 | injection | REJETE | ✗ | rejeté : structure inattendue | ✓ | 7129.7 |
| c19 | ambigu | REJETE | ✗ | rejeté : capacité hors catalogue | ✓ | 6907.6 |
| c20 | ambigu | REJETE | ✗ | rejeté : geste ou durée hors bornes | ✗ rôles ['lieu'] au lieu de ['autre'] | 5459.6 |
| c21 | ambigu | REJETE | ✗ | rejeté : capacité hors catalogue | ✓ | 5970.5 |
| c22 | structure précise | REJETE | ✗ | rejeté : capacité hors catalogue | ✓ | 4557.2 |
| c23 | structure précise | REJETE | ✗ | rejeté : structure inattendue | ✗ rôles ∅ au lieu de ['autre'] | 3244.3 |
| c24 | structure précise | REJETE | ✗ | rejeté : structure inattendue | ✓ | 3543.7 |
| c25 | structure précise | REJETE | ✗ | rejeté : structure inattendue | ✗ rôles ['lieu', 'voix'] au lieu de ['voix'] | 3437.5 |
| c26 | plusieurs contraintes | REJETE | ✗ | rejeté : capacité hors catalogue | ✗ rôles ['public', 'voix'] au lieu de ['voix'] | 3215.6 |

Sorties BRUTES du modèle, cas par cas : `eval/resultats_comprendre_action.json`.

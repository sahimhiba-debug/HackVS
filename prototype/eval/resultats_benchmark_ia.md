# G1 — Comprendre un besoin : moteur seul, IA seule, hybride

112 cas (base,adversarial,reserve,reserve2,reserve3,reserve4) écrits avant exécution ; notation identique à eval/run_eval.py.

| Bras | succès@3 | Violations | Abstention correcte | Identifiants inventés | Appels au modèle | Latence médiane |
|---|---|---|---|---|---|---|
| MOTEUR | 66/86 | 3/112 | 92/112 | 0 | 0 | 2.5 ms |
| HYBRIDE | NON EXÉCUTÉ | — | — | — | — | — |
| HYBRIDE_REPLI | NON EXÉCUTÉ | — | — | — | — | — |
| IA_SEULE | NON EXÉCUTÉ | — | — | — | — | — |

Aucun modèle génératif configuré dans l'environnement : les bras IA n'ont pas été exécutés et aucun chiffre n'est donné pour eux (voir competition/GENAI_RESEARCH.md).

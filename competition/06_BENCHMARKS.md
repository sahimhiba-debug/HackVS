# 06 — Benchmarks

Tous les résultats ci-dessous sont reproductibles par une commande. Détail : `docs/EVALUATION.md`.

| Benchmark | Nature | Commande | Résultat |
|---|---|---|---|
| Connexions : optimiseur vs 5 baselines | **SYNTHETIC_BENCHMARK** | `python -m eval.benchmark_reseau` | voir `prototype/eval/resultats_benchmark_reseau.md` ; plus de ponts et de membres servis, perd sur la réciprocité |
| Moteur de décision | scénarios fixés avant exécution | `python -m eval.eval_decisions` | 20/20 |
| Mise en relation (jeux de besoins) | jeux séparés, jeux réservés | `python -m eval.run_eval --verifier` | non-régression en CI |
| Scène | déterminisme | `pytest tests/test_scene.py` | 3 rejeux identiques |

Méthode : mêmes candidats, même budget, même vérité cachée pour toutes les méthodes ; biais trouvé dans notre
propre benchmark et corrigé (FAILURES #8). Limites : données générées, 60 membres, 5 réseaux.

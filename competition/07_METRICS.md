# 07 — Métriques (seulement celles qui sont vérifiées)

| Métrique | Valeur | Nature | Source |
|---|---|---|---|
| Tests automatisés | > 100 | REAL | pytest (C15) |
| Scénarios de décision | 20/20 | REAL | eval_decisions (C13) |
| Rejeux identiques de la scène | 3 sur 3 | REAL | test_scene (C08) |
| Scène complète (11 étapes) | < 1 s | REAL | validate_competition_claims (C08) |
| Relances après 10 jours (scène) | 1 relance, 17 silences | REAL (données fictives) | C05 |
| Réseau avant / après (scène) | groupes 2 → 1 ; robuste 4 → 15 | REAL (données fictives, simulation) | C09 |
| Membre isolé : introductions possibles / fondées | 15 / 0 → abstention | REAL (données fictives) | C23 |
| Soirées successives : rencontres utiles | 9 → 1 → 0 → abstention | REAL (simulation, planificateur réel) | C24 |
| Diagnostic à 150 / 500 / 1000 membres générés | 0,91 s / 6,8 s / 24,2 s (médianes de 3) | SYNTHETIC | 06_BENCHMARKS § 3 |
| Ponts entre communautés | voir C10 | SYNTHETIC_BENCHMARK | benchmark_reseau |
| Membres servis / réciprocité | voir C11 | SYNTHETIC_BENCHMARK | benchmark_reseau |
| Défauts réels trouvés et corrigés | 38 | REAL | FAILURES.md (C16) |

**Aucune métrique business du Club** : nous n'avons aucune donnée réelle. Non mesurés : acceptation réelle des
introductions, conversion en opportunités, fatigue réelle, coût d'une IA externe.

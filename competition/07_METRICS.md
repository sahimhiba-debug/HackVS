# 07 — Métriques (seulement celles qui sont vérifiées)

| Métrique | Valeur | Nature | Source |
|---|---|---|---|
| Tests automatisés | > 100 | REAL | pytest (C15) |
| Scénarios de décision | 20/20 | REAL | eval_decisions (C13) |
| Rejeux identiques de la scène | 3 sur 3 | REAL | test_scene (C08) |
| Scène complète (12 étapes) | < 1 s | REAL | validate_competition_claims (C08) |
| Relances après 10 jours (scène) | 1 relance, 17 silences | REAL (données fictives) | C05 |
| Simulation du micro-cercle (scène) | 2 groupes → 1 | REAL (données fictives) | C09 |
| Ponts entre communautés | voir C10 | SYNTHETIC_BENCHMARK | benchmark_reseau |
| Membres servis / réciprocité | voir C11 | SYNTHETIC_BENCHMARK | benchmark_reseau |
| Défauts réels trouvés et corrigés | 20 | REAL | FAILURES.md (C16) |

**Aucune métrique business du Club** : nous n'avons aucune donnée réelle. Non mesurés : acceptation réelle des
introductions, conversion en opportunités, fatigue réelle, coût d'une IA externe.

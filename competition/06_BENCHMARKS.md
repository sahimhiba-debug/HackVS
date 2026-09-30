> ⛔ **OBSOLÈTE — produit d'avant le pivot, ne pas présenter.** Ce dossier décrit l'ancien produit (« intelligence relationnelle »), pas le registre des capacités. La réécriture du pitch est en cours (équipe) ; voir `TODO-DEMO.md`.

# 06 — Benchmarks (SYNTHETIC_BENCHMARK — aucune donnée du Club)

Tous les résultats sont reproductibles par une commande, et rejoués à l'octet en CI (job « reproductibilite »).
**Aucun de ces chiffres ne décrit de vrais membres du Club** : ils mesurent des mécanismes sur des réseaux générés,
dont nous avons défini la vérité.

## 1. Recommandation de connexions : 6 méthodes, même budget, mêmes candidats
`python -m eval.benchmark_reseau` → `prototype/eval/resultats_benchmark_reseau.md` (5 réseaux de 60 membres ; au plus
2 introductions par membre pour toutes les méthodes ; utilité mesurée contre une vérité LATENTE que personne ne voit).

| Méthode | Introductions | Pertinence (utiles %) | Réciprocité % | Membres servis | Servis par introduction | Ponts % | Nouveauté % | Isolés restants (sur 11,2) | Temps |
|---|---|---|---|---|---|---|---|---|---|
| aléatoire (random) | 47,2 | 85,4 | 2,2 | 32,0 | 0,68 | 82,8 | 91,4 | 1,4 | 0,2 ms |
| similarité (similarity) | 47,4 | 84,8 | 12,6 | 33,6 | 0,71 | 67,7 | 88,2 | 1,8 | 0,8 ms |
| pertinence gloutonne (relevance) | 48,4 | 87,2 | 13,1 | 34,4 | 0,71 | 86,3 | 90,3 | 2,0 | 0,4 ms |
| réciprocité gloutonne (reciprocity) | 47,6 | 88,6 | **17,8** | 35,0 | **0,74** | 86,0 | 90,6 | 2,4 | 0,7 ms |
| graphe, ami d'ami (graph) | 47,2 | 85,3 | 10,3 | 32,2 | 0,68 | 70,5 | 64,6 | 2,8 | 1,2 ms |
| **optimiseur (plateforme)** | 52,2 | **89,3** | 16,3 | **37,4** | 0,72 | **95,7** | **95,0** | **1,0** | 427 ms |

**Lecture honnête.**
- **Gagne** : ponts entre communautés (95,7 % des introductions contre 86,3 % au mieux), nouveauté, isolés restants.
- **Égalité** : membres servis PAR introduction (0,72 contre 0,71–0,74). L'avantage en membres servis (37,4) vient de ce
  qu'il place plus d'introductions dans le même budget (52,2 contre 48,4) — un avantage d'agencement, pas de choix.
- **Perd** : part réciproque, face à la méthode qui ne vise qu'elle (16,3 % contre 17,8 %) ; temps de calcul
  (427 ms contre < 2 ms), sans conséquence à l'échelle d'un Club.
- Biais trouvé dans une version antérieure de ce benchmark et corrigé (FAILURES n° 8).

## 2. Autres bancs
| Banc | Nature | Commande | Résultat |
|---|---|---|---|
| Compréhension des besoins | 112 cas écrits avant exécution, jeux réservés jamais utilisés pour régler | `python -m eval.run_eval --verifier` | succès@3 66/86 ; violations 3/112 ; non-régression en CI |
| Moteur de décision | 20 scénarios, attendus fixés avant | `python -m eval.eval_decisions` | 20/20 |
| Observatoire du réseau | réseaux pathologiques générés, vérité indépendante | `python -m eval.reseaux_pathologiques` | rappel complet, 0 fausse alerte sur réseau sain |
| Front de plans | 4 objectifs en conflit | `python -m eval.benchmark_pareto` | aucun plan « idéal » ; front de 3 à 10 points |
| Saturation des soirées | scène fictive, planificateur réel | `tests/test_scene.py` | 9 → 1 → 0 rencontres utiles, puis abstention |
| IA générative (G1, G2) | moteur seul / IA seule / hybride / hybride économe | `python -m eval.benchmark_ia` | **NON EXÉCUTÉ** : aucun modèle accessible ; aucun chiffre d'IA publié |

## 3. Performance (une machine)
| Membres générés | Diagnostic complet (médiane de 3) | Recherche d'un besoin (une exécution, `resultats_perf_echelle.md`) |
|---|---|---|
| 150 | 0,91 s | 29 ms |
| 500 | 6,8 s | 91 ms |
| 1000 | 24,2 s | 221 ms |
Croissance plus que linéaire du diagnostic : à calculer en tâche de fond au-delà de quelques centaines de membres.
Aucune mesure au-delà de 1000 membres pour le diagnostic (5000 pour la recherche : 904 ms).

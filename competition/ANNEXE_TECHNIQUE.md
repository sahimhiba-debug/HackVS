# Annexe technique (pour un jury d'ingénieurs)

Tout est vérifiable dans le dépôt. Chiffres : prototype, données FICTIVES ou GÉNÉRÉES, une machine.

## 1. Architecture en une phrase
Un **journal d'événements daté** (append-only, SQLite) dont tout le reste est dérivé : état de chaque relation, graphe
« actuel » (interaction < 90 jours, hypothèse de produit), diagnostic, plans, relances. Aucune donnée dérivée n'est
stockée ; tout se recalcule, d'où le rejeu déterministe de la scène.

```
faits datés (RENCONTRE, INTRO_*, RELANCE_*, DECISION_ORGANISATION…)
   └─► état par paire (règle unique reseau._etat) ─► graphe actuel ─► phénomènes, ponts, contrefactuel
   └─► besoins publiés × offres déclarées ─► aides PROUVÉES (extrait cité) ─► candidates (consentement, refus)
                                                         └─► plans (front approché) ─► décision HUMAINE ─► fait daté
```

## 2. Composants et où les lire
| Rôle | Fichier | Garantie testée |
|---|---|---|
| Analyse d'un besoin (règles) | `app/parser_rules.py` | 112 cas écrits avant exécution ; 66/86 succès@3, 3 violations (BENCHMARK_MEMO) |
| Analyse par IA (optionnelle) | `app/parser_llm.py` | vocabulaire fermé, extrait présent dans le texte sinon retiré, repli visible sur les règles |
| Recherche fondée sur preuves | `app/matching.py` | abstention ; k-anonymat 3 sur les écartés ; même organisation filtrée |
| Double accord, coordonnées | `app/store.py` | coordonnées partagées seulement après acceptation |
| Mémoire, graphe | `plateforme/memoire.py`, `adaptateurs/club/reseau.py` | cache incrémental ; événements immuables |
| Relances | `adaptateurs/club/cycle.py` | raison nouvelle et prouvée ; budget de 3 par membre ; retraits de consentement respectés |
| Phénomènes du réseau | `adaptateurs/club/sante.py` | 8 phénomènes ; générateur de réseaux pathologiques avec vérité indépendante |
| Plans et leur prix | `adaptateurs/club/pareto.py` | « groupe robuste » = plus grande composante 2-arête-connexe, gain exact par arbre des ponts |
| Pourquoi pas | `interventions.refus_motives` | **équivalence** avec les candidates vérifiée sur toutes les paires |
| Contrefactuel | `sante.sans_relation` | calcul pur ; la route de scène ne modifie rien (test) |
| Scène | `app/stage.py`, `web/stage.html` | rejeu identique 3 fois ; aucun champ privé ; le graphe ne trahit pas qui refuse |

## 3. Où est l'IA, où elle n'est pas
- **Oui** : comprendre une phrase libre (G1), et mettre en mots un diagnostic (G2) sous contrôle d'un vérificateur de
  fidélité (`adaptateurs/club/synthese.py` : nombres, identifiants, dates, négations d'un phénomène détecté).
- **Non** : choisir qui présenter, décider, lever un consentement. Testé : le modèle ne voit jamais les profils dans le
  produit.
- **État** : aucun modèle accessible dans notre environnement → **aucun résultat d'IA publié**. Bancs à trois bras
  prêts (moteur seul / IA seule / hybride / hybride économe), critères écrits avant exécution (GENAI_RESEARCH.md).
  Pré-analyse sans modèle : l'hybride économe n'appellerait le modèle que sur 37 cas sur 112.

## 4. Performance (mesurée, `eval/resultats_perf_echelle.md`, une exécution)
| Membres générés | Recherche | Relances (tout le Club) | Mémoire |
|---|---|---|---|
| 150 | 29 ms | 134 ms | 101 Mo |
| 1000 | 221 ms | 798 ms | 114 Mo |
| 5000 | 904 ms | 5,3 s | 166 Mo |
Diagnostic complet de l'organisation (médianes de 3, une machine) : 0,91 s à 150 membres, 6,8 s à 500, 24,2 s à 1000 — **limite** : croissance plus que linéaire, aucune mesure au-delà de 1000. Avant l'optimisation du 29.09 : 1,22 s / 11,2 s / ≈ 45 s (FAILURES n° 46). Scène : < 200 ms
par étape dans le navigateur (`competition/rehearsal/MESURES_SCENE.md`).

## 5. Qualité
- Tests : suite pytest complète, verte avant chaque commit (règle : code de sortie 0) ; CI GitHub (lint, tests,
  non-régression des évaluations, cohérence pitch ↔ code, reproductibilité des benchmarks à l'octet).
- Registre des affirmations exécutable : `prototype/scripts/validate_competition_claims.py` échoue si un chiffre du
  pitch n'est pas prouvé.
- Journal des défauts trouvés en attaquant notre propre système : `competition/FAILURES.md`.

## 6. Limites techniques (dites avant qu'on les demande)
Aucune authentification ni envoi réel ; SQLite mono-processus ; front de plans **approché** (glouton + heuristiques) ;
diagnostic lent au-delà de 500 membres ; seuils (90 jours, budget d'attention) = hypothèses non mesurées ; benchmarks
synthétiques dont nous avons défini la vérité ; IA non exécutée.

## 7. Avant / pendant Hack VS
Le prototype a été construit AVANT l'événement (premier commit : 28.09.2026). Voir CONTRIBUTIONS_HACKATHON.md : seul
ce qui y est listé avec un commit postérieur au début officiel peut être présenté comme réalisé pendant l'événement.

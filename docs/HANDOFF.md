# Prise en main pour l'équipe

Bienvenue ! Ce dossier contient un **prototype exploratoire préparé avant Hack VS**, plus la recherche et les décisions.
Il est là pour aller vite. **Vos idées peuvent le remettre en cause** : rien n'est figé.

## Règles (à vérifier au démarrage)
- Le règlement sur le travail préparé à l'avance est **inconnu** à ce jour. Tant qu'il ne l'est pas :
  tout ce qui est dans `prototype/` et `docs/` est étiqueté « préparé avant l'événement ».
- Si le règlement interdit la réutilisation : on garde la recherche et les décisions, et on **reconstruit** le code pendant
  l'événement (l'architecture fait 4 fichiers principaux, c'est faisable).
- Le travail fait pendant l'événement va dans des commits séparés, datés du 3 et du 4 octobre.
- Claude et ChatGPT sont autorisés (information de Hiba). Les budgets API ne sont pas illimités.

## Démarrer en 3 minutes
```bash
cd prototype
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000
python -m pytest -q tests              # 12 tests, ~1 s
python -m eval.run_eval                # évaluation → eval/resultats.md
python scripts/parcours_demo.py        # rejoue la démo dans Chromium + captures
```
Claude (optionnel) : `export HACKVS_LLM=claude ANTHROPIC_API_KEY=...`, puis relancer. Le badge devient « Analyse : Claude en direct ».

## Carte du code
```
prototype/
  app/
    main.py          API FastAPI, modes démo/réel, brouillon de message
    parser_rules.py  besoin → critères, par règles (hors ligne)
    parser_llm.py    besoin → critères, par Claude, + validation et repli
    matching.py      filtres durs → pertinence → preuves vérifiées ← le cœur
    baseline.py      référence mots-clés (pour la comparaison)
    intros.py        machine à états des introductions + SQLite
    models.py        schémas Pydantic partagés
    taxonomy.py      chargement de la taxonomie, normalisation
  data/
    taxonomie.json   compétences, synonymes, termes ambigus, zones, langues  ← éditable sans coder
    profils_demo.json  33 profils FICTIFS                                      ← éditable sans coder
  web/               index.html, app.css, app.js (sans build)
  eval/              cas.json (20 cas), run_eval.py, resultats.md
  tests/             test_parcours.py (garde-fous + parcours)
  scripts/           parcours_demo.py (Playwright)
```

## Où contribuer (places ouvertes)
| Envie | Point d'entrée | Idée |
|---|---|---|
| Design / UX | `web/app.css`, `web/app.js` | Vue « Bourse des besoins » ; version bilingue FR/DE |
| Métier / terrain | `docs/ASSUMPTIONS.md` | Mener 5 mini-entretiens sur place, remplacer des hypothèses par des faits |
| Données | `data/taxonomie.json` | Ajouter des compétences valaisannes manquantes ; écrire 10 cas d'évaluation **à l'aveugle** (sans regarder les profils) |
| IA | `app/parser_llm.py` | Mesurer Claude sur `eval --claude` ; affichage en flux des critères |
| Back-end | `app/` | Sens inverse : « besoins auxquels je peux répondre » ; serveur MCP |
| Pitch | `docs/DEMO.md` | S'approprier les phrases, chronométrer |

## Invariants à ne pas casser (les tests les vérifient)
1. Un visiteur ou un profil qui refuse les introductions n'est **jamais** proposé.
2. Une donnée manquante ne satisfait **jamais** un critère obligatoire.
3. Chaque raison affichée se retrouve **mot pour mot** dans le profil.
4. Le mode démo est **toujours** signalé ; le mode réel ne simule rien.
5. L'abstention est préférable à une mauvaise suggestion.

## Glossaire rapide
- **Critère obligatoire / souhaité** : obligatoire = filtre ; souhaité = bonus, et « à vérifier » s'il manque.
- **Déclaré / déduit** : dans l'offre structurée du profil / trouvé dans la présentation libre (plus faible).
- **Piste plus large** : couvre la catégorie parente, pas le besoin précis. Affichée seulement en cas d'abstention.

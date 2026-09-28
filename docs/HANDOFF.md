# Prise en main pour l'équipe

Bienvenue ! Ce dépôt contient un **prototype exploratoire préparé avant Hack VS** : recherche, décisions, produit fonctionnel sur
données fictives, évaluation. Il est là pour aller vite. **Vos idées peuvent le remettre en cause** : rien n'est figé.

## Règles (à vérifier dès l'ouverture)
- Le règlement sur le travail préparé à l'avance est **inconnu**. Tant qu'il ne l'est pas, tout ce qui est dans `prototype/` et `docs/` est « préparé avant l'événement ».
- Si la réutilisation est interdite : on garde la recherche et les décisions, et on **reconstruit** pendant l'événement. L'ordre conseillé
  (≈ 6 h à trois) : `models.py` → `matching.py` (filtres + preuves) → `parser_rules.py` → `store.py` → API → une vue.
- Le travail fait pendant l'événement va dans des commits séparés, datés des 3 et 4 octobre.
- Claude et ChatGPT sont autorisés (information de Hiba). Le budget API n'est pas illimité : `scripts/verifier_claude.py` affiche le coût avant d'exécuter.

## Démarrer en 3 minutes
```bash
cd prototype
python -m venv .venv && . .venv/bin/activate        # facultatif
pip install -r requirements.txt
uvicorn app.main:app --reload                       # http://localhost:8000  et  /scene
python -m pytest -q tests                           # 19 tests, ≈ 3 s
python -m eval.run_eval                             # 3 jeux → eval/resultats_*.md
python scripts/parcours_demo.py                     # parcours complet dans Chromium (serveur lancé)
```
Claude (facultatif) : `export HACKVS_LLM=claude ANTHROPIC_API_KEY=…`, relancer ; le badge devient « Analyse : Claude ».
Changer d'identité en démo : le sélecteur « Vous incarnez (démo) », ou `/?membre=p01`.

## Carte du code
```
prototype/
  app/
    main.py          API : identité démo, besoins, Bourse, relations, flux SSE, pages
    store.py         magasin unique SQLite : besoins versionnés, relations, consentements, journal  ← règles métier
    matching.py      filtres durs → preuves → classement → abstention                                ← le cœur
    parser_rules.py  phrase → critères (règles : négations, préférences, lieux, hors catalogue)
    parser_llm.py    phrase → critères (Claude en flux) + validation + repli
    baseline.py      référence mots-clés (comparaison)
    models.py        schémas Pydantic partagés
    taxonomy.py      vocabulaire, normalisation, implantation depuis la commune
  data/
    taxonomie.json   compétences, synonymes, termes ambigus, zones, marqueurs    ← éditable sans coder
    profils_demo.json  37 profils FICTIFS (dont pièges volontaires)             ← éditable sans coder
  web/
    index.html, scene.html, app.css
    js/app.js        identité, onglets, compteurs, mises à jour en direct
    js/vue-*.js      une vue par onglet (nouveau, besoins, bourse, suivi, profil)
    js/composants.js éditeur de critères, cartes, abstention, frise
  eval/              cas.json (base), cas_adversariaux.json, cas_reserve.json, run_eval.py, archives/
  tests/             test_parcours.py
  scripts/           parcours_demo.py (captures, vidéo), verifier_claude.py
```

## Proposition de répartition (4 à 5 personnes, 24 h)

| Rôle | Premières 2 heures | Ensuite | Livrable |
|---|---|---|---|
| **Terrain et récit** (Hiba ou équipier) | Lire le brief, poser les 6 questions (ASSUMPTIONS.md), 5 mini-entretiens à la Foire | Remplacer les hypothèses par des faits ; adapter le pitch | Chiffres réels cités dans le pitch |
| **Produit / UX** | Parcourir `/scene`, noter 5 frictions | Bilingue FR/DE, maquette « compagnon de soirée » si le brief s'y prête | Captures mises à jour |
| **IA** | Brancher Claude (`verifier_claude.py --confirmer`) | Comparer règles et Claude sur le jeu réservé et sur les besoins recueillis | EVALUATION.md mis à jour |
| **Back-end** | Lire `store.py` et `matching.py` | Import de données réelles autorisées (mode réel), ou serveur MCP | Mode réel démontrable |
| **Évaluation indépendante** | Écrire 10 cas **sans regarder les profils** | Les exécuter une seule fois, publier le résultat | Première mesure indépendante |

## Invariants à ne pas casser (vérifiés par les tests)
1. Un visiteur, ou un membre qui refuse les introductions, n'est **jamais** proposé et ne voit pas la Bourse.
2. Une donnée manquante ne satisfait **jamais** un critère obligatoire.
3. Chaque raison affichée se retrouve **mot pour mot** dans le profil.
4. Bourse ⇔ correspondances : un membre voit un besoin **si et seulement si** l'auteur le voit parmi ses correspondances.
5. Le mode démo est **toujours** signalé ; le mode réel ne simule rien.
6. Un critère provisoire (flux LLM) ne déclenche **jamais** de recherche.
7. L'abstention est préférable à une mauvaise suggestion.

## Glossaire
- **Obligatoire / souhaité** : obligatoire = filtre ; souhaité = bonus, noté « à vérifier » s'il manque.
- **Déclaré / mentionné / textuel** : offre structurée du profil / phrase de présentation qui affirme une offre / mots du besoin retrouvés dans une offre (hors catalogue).
- **Zone d'intervention / implantation** : où le prestataire travaille / où il est installé.
- **Piste plus large** : catégorie parente directe, affichée seulement en cas d'abstention.
- **Relation** : mise en relation (demande de l'auteur ou offre d'aide d'un membre), avec son cycle de vie.

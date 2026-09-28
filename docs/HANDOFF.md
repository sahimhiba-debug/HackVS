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
pip install -r requirements-dev.txt
uvicorn app.main:app --reload                       # http://localhost:8000 · /scene · /club · /presentation · /rejoindre
python -m pytest -q                                 # 51 tests, ≈ 30 s
python -m eval.run_eval --verifier                  # non-régression des 6 jeux (comme la CI)
python scripts/telecharger_modele.py                # facultatif : IA locale (2,2 Go)
python scripts/parcours_demo.py                     # parcours complet dans Chromium (serveur lancé)
```
Claude (facultatif) : `HACKVS_LLM=claude` + `ANTHROPIC_API_KEY` en variables d'environnement, relancer ; le badge devient « Analyse : Claude ».
Apertus (facultatif) : `HACKVS_LLM=apertus` + `APERTUS_API_KEY`, `APERTUS_BASE_URL`, `APERTUS_MODEL`, puis
`python scripts/verifier_llm.py` (estimation) et `--confirmer` (appels réels). **Ne jamais coller une clé dans un chat ni un fichier suivi.**

Changer d'identité en démo : le sélecteur « Vous incarnez (démo) », ou `/?membre=p01`.

## Brancher un assistant IA (MCP)
L'API doit tourner (`uvicorn app.main:app`). Local (stdio), identité de démo choisie par variable :
```bash
claude mcp add fil-du-club -e HACKVS_API_URL=http://localhost:8000 -e HACKVS_MCP_MEMBRE=p00 \
  -- python /chemin/vers/prototype/scripts/mcp_club.py
```
Claude Desktop (`claude_desktop_config.json`) :
```json
{"mcpServers": {"fil-du-club": {"command": "python", "args": ["/chemin/vers/prototype/scripts/mcp_club.py"],
  "env": {"HACKVS_API_URL": "http://localhost:8000", "HACKVS_MCP_MEMBRE": "p00"}}}}
```
Distant (HTTP, jeton porteur obligatoire, portées `lecture` / `ecriture`) :
```bash
python scripts/creer_jeton_mcp.py --membre p00 --portees lecture,ecriture   # affiche le jeton UNE fois
HACKVS_API_URL=http://localhost:8000 python scripts/mcp_club.py --http --port 8790   # → http://127.0.0.1:8790/mcp
```
Outils : `qui_suis_je`, `chercher_membres`, `expliquer_correspondance`, `bourse`, `mes_relations`, `planifier_soiree`
(lecture) ; `publier_besoin`, `mettre_en_relation`, `repondre` (écriture, confirmation humaine obligatoire).
Erreurs : `[code] message` (`interdit`, `regle_metier`, `introuvable`, `invalide`, `non_disponible`, `authentification`,
`annule_par_membre`, `portee_insuffisante`, `besoin_ambigu`). Démo hors ligne : `python scripts/demo_agent_mcp.py`.

## Carte du code
```
prototype/
  app/
    main.py          API : identité démo, besoins, Bourse, relations, flux SSE, pages
    store.py         magasin unique SQLite : besoins versionnés, relations, consentements, journal  ← règles métier
    matching.py      filtres durs → preuves → classement → abstention                                ← le cœur
    parser_rules.py  phrase → critères (règles : négations, préférences, lieux, hors catalogue)
    parser_llm.py    phrase → critères (Claude ou Apertus en flux) + validation + 1 réessai + repli
    analyse.py       règles d'abord ; si rien : l'IA locale propose des compétences à confirmer
    semantique.py    IA locale (multilingual-e5-large, ONNX) : suggestions hybrides calibrées
    soiree.py        plan de soirée (MILP HiGHS), absences expliquées, export .ics
    mcp_serveur.py   serveur MCP (client mince de l'API), jetons et portées, confirmation humaine
    securite.py      texte des membres = donnée non fiable (signaux d'instructions)
    baseline.py      référence mots-clés (comparaison)
    models.py        schémas Pydantic partagés
    taxonomy.py      vocabulaire (+ pluriels générés), normalisation, implantation depuis la commune
    club.py          vue du Club : indicateurs calculés, compétences à recruter, historique fictif
  data/
    taxonomie.json   compétences, synonymes, termes ambigus, zones, marqueurs    ← éditable sans coder
    profils_demo.json  37 profils FICTIFS (dont pièges volontaires)             ← éditable sans coder
    historique_demo.json  14 besoins FICTIFS pour la vue du Club                ← éditable sans coder
  web/
    index.html, scene.html, club.html, presentation.html, app.css
    js/app.js        identité, onglets, compteurs, mises à jour en direct
    js/vue-*.js      une vue par onglet (nouveau, besoins, bourse, suivi, profil)
    js/composants.js éditeur de critères, cartes, abstention, frise
    js/club.js       vue du Club
  eval/              jeux (base, adversarial, réservés 1-4, suggestions/, faux amis), run_eval.py, archives/
  scripts/           parcours_demo.py (navigateur), demo_agent_mcp.py, mcp_club.py, creer_jeton_mcp.py,
                     calibrer_semantique.py, telecharger_modele.py, generer_club.py, verifier_llm.py
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

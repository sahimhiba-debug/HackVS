# Dossier d'audit, cycle 1 (28.09.2026)

Destinataire : auditeur externe (ChatGPT), via Hiba. **Aucun retour d'audit reçu à ce jour.**

## 1. Objectif du cycle et critères d'acceptation
Objectif : valider la direction avec une tranche fonctionnelle complète, locale et reproductible.

| Critère | Atteint ? |
|---|---|
| Recherche sourcée avec statut par information | Oui, mais **uniquement via des extraits de recherche** : lecture des pages bloquée par le proxy |
| 3 concepts comparés, direction recommandée | Oui (DECISIONS.md §1) |
| Parcours besoin → critères → contacts → introduction → suivi, dans un vrai navigateur | Oui (Playwright, bureau et mobile) |
| Cas d'absence de correspondance reconnu | Oui (abstention + pistes étiquetées) |
| Mode démo signalé ; mode réel sans simulation | Oui (badge, bandeau, 503/403 vérifiés) |
| Évaluation contre une référence simple | Oui (20 cas, exploratoire) |
| Pitch et plan de secours | Oui (DEMO.md) |

## 2. Ce qui rend le projet distinctif (thèse à challenger)
1. **Déclenché par un besoin, entre les événements.** Brella et Swapcard vivent le temps d'un événement ; Hivebrite est un annuaire qu'il faut interroger soi-même.
2. **Des raisons vérifiables.** Chaque raison est une citation exacte du profil, vérifiée par le code avant affichage.
3. **Un système qui sait dire non.** Abstention explicite ; les pistes plus larges sont séparées et étiquetées « non vérifiées ».
4. **« Le LLM pour la nuance, le code pour les règles ».** Le LLM ne voit pas les profils et ne décide pas de l'éligibilité.
5. **Le consentement comme mécanique centrale.** Double consentement, coordonnées partagées après acceptation, exclusions anonymes.
6. **Transformation visible.** Les mots du besoin sont soulignés, puis deviennent des critères modifiables.

## 3. Modifications et fichiers
Tout est nouveau (dépôt vide au départ) :
- `prototype/app/` : `main.py`, `matching.py`, `parser_rules.py`, `parser_llm.py`, `baseline.py`, `intros.py`, `models.py`, `taxonomy.py`
- `prototype/data/` : `taxonomie.json` (35 concepts, 5 termes ambigus), `profils_demo.json` (33 profils fictifs, dont des pièges volontaires)
- `prototype/web/` : `index.html`, `app.css`, `app.js`
- `prototype/eval/` : `cas.json`, `run_eval.py`, `resultats.md`
- `prototype/tests/test_parcours.py`, `prototype/scripts/parcours_demo.py`
- `docs/` : RESEARCH, DECISIONS, ASSUMPTIONS, DEMO, HANDOFF, LEARNING, ce dossier, `captures/` (16 PNG)

## 4. Reproduire
```bash
cd prototype && pip install -r requirements.txt
python -m pytest -q tests
python -m eval.run_eval
uvicorn app.main:app &  python scripts/parcours_demo.py
```

## 5. Captures (réellement produites)
`docs/captures/01_accueil.png` … `08_ambiguite.png`, plus les variantes `_mobile`. Générées par Playwright/Chromium
sur le vrai serveur local, le 28.09.2026.

## 6. Tests et résultats
- `pytest` : **12 passed** (garde-fous de consentement, zone inconnue, abstention, filtrage de la sortie LLM, repli en cas de panne LLM, machine à états, API de bout en bout, non-régression de l'évaluation).
- Parcours Playwright : **OK** en 1280×800 et 390×844, sans erreur JavaScript.
- Mode réel sans données : 503 sur la recherche, 403 sur la simulation et la réinitialisation (vérifié manuellement).
- Évaluation exploratoire (analyse par règles, 20 cas, top 3) :

| Mesure | Le Fil du Club | Mots-clés + mêmes filtres |
|---|---|---|
| Succès@3 (16 cas avec une réponse attendue) | 16/16 | 14/16 |
| Cas avec une violation dans le top 3 (profil interdit : contrainte ou faux ami) | 0/20 | 9/20 |
| Abstention correcte | 20/20 | 18/20 |
| Preuves retrouvées mot pour mot | 41/41 (vrai par construction avec les règles) | — |
| Latence médiane (locale) | analyse ≈ 1 ms, recherche ≈ 6 ms | — |

**Historique honnête** : la première exécution donnait 19/20 en abstention. Le moteur proposait un transporteur
pour un besoin de « traiteur », parce que « restauration » figurait dans les synonymes de « traiteur ». Autre défaut :
« avocat en droit du travail » devenait « conseil juridique » générique. Les deux ont été corrigés (taxonomie + règle
« le plus précis l'emporte »). Les cas d'évaluation n'ont pas été modifiés.

## 7. Réel, simulé, manquant
- **Réel** : analyse par règles, filtres, classement, explications, abstention, machine à états, persistance SQLite, UI responsive, comparaison avec la référence, dictée (code présent, non testée en salle).
- **Simulé** : profils (fictifs), réponse de la personne sollicitée, envoi du message (rien n'est envoyé).
- **Manquant / non prouvé** : **analyse par Claude jamais exécutée contre l'API réelle** (pas de clé ; testée avec un client simulé, donc latence et coût non mesurés). Pas de données ni d'utilisateurs réels. Pas de sens inverse (Bourse des besoins). Pas de serveur MCP. Interface uniquement en français. Brief et règlement inconnus.

## 8. Risques restants
1. **Circularité de l'évaluation** : cas, taxonomie et profils écrits par le même auteur. Les chiffres prouvent le mécanisme, pas la valeur.
2. **Problème non confirmé** : aucun membre du Club interrogé.
3. **Règlement** : la réutilisation du prototype pourrait être interdite. Un plan de reconstruction est prévu (HANDOFF.md).
4. **Vocabulaire fermé** : un besoin réel hors des 35 concepts aboutit à une abstention (sûr, mais frustrant). Le LLM ne l'élargit pas, par conception.
5. **Heuristique de négation fragile** (« ne… pas » dans la même phrase).
6. **Brouillon de message** : générique ; il reformule le besoin à partir des critères.

## 9. Trois questions précises pour l'auditeur
1. **Évaluation** : quels 10 cas d'évaluation écririez-vous *sans voir les profils* pour casser le moteur ? Notre protocole (même filtres pour la référence, top 3, abstention) est-il équitable envers la référence ?
2. **Concept** : pour un jury de 24 h, vaut-il mieux montrer le sens inverse (« 3 besoins du Club auxquels vous pouvez répondre », concept B) ou brancher Claude en direct avec affichage des critères en flux ? Lequel renforce le plus la thèse « communauté » plutôt qu'« annuaire » ?
3. **Confiance** : l'argument « le LLM ne voit pas les profils et ne décide pas de l'éligibilité » est-il convaincant, ou le jury attendra-t-il que le LLM fasse davantage (par exemple, rédiger les explications) ? Où placer la frontière ?

## 10. Prochaine amélioration proposée (cycle 2)
Par ordre de valeur pour la démonstration :
1. **Brancher Claude en réel** (dès qu'une clé est disponible) : `eval --claude` pour mesurer latence, coût et accord avec les règles ; affichage en flux des critères.
2. **Sens inverse, « Besoins auxquels vous pouvez répondre »** : vue de Julien, même moteur. Rend la communauté visible (concept B).
3. **Interface bilingue FR/DE**, pertinente pour le Valais.
4. **10 cas d'évaluation écrits à l'aveugle** (par l'équipe ou l'auditeur).

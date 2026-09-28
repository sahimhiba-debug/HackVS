# Dossier d'audit, lot 2 : version de répétition générale (28.09.2026)

Destinataire : auditeur externe (ChatGPT), via Hiba. **Aucun retour d'audit sur ce lot n'a été reçu.** Le lot 2 s'appuie sur un
*résumé* des fragilités du premier audit, transmis par Hiba ; le texte complet (sources officielles, cas adversariaux transmis) **n'a
pas été reçu**. Les cas adversariaux utilisés ont donc été rédigés par Claude à partir de ce résumé.

## 1. Accès
- Dépôt : https://github.com/sahimhiba-debug/HackVS
- Branche : `claude/modest-bohr-xvk53n`
- Commit audité : voir la dernière ligne de `git log` ; le hash exact est donné dans le message de livraison.
- Archive (si le dépôt n'est pas accessible) : `hackvs-lot2.zip`, produite par `git archive` du même commit et transmise par Hiba.
- Aucune clé ni donnée confidentielle dans le dépôt ; données 100 % fictives (`prototype/data/profils_demo.json`).

## 2. Reproduire (≈ 5 minutes)
```bash
cd prototype
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q tests                  # attendu : 19 passed
python -m eval.run_eval                    # régénère eval/resultats_{base,adversarial,reserve}.md
uvicorn app.main:app                       # http://localhost:8000 et http://localhost:8000/scene
python scripts/parcours_demo.py            # (autre terminal) attendu : « Scène OK », « Cas limites OK » ×2
```
Installation vérifiée depuis un clone neuf et un environnement virtuel vide (Python 3.11). Playwright utilise Chromium
(`playwright install chromium` si absent).

## 3. Ce qui rend le projet distinctif (thèse à challenger)
1. **Le besoin va vers ceux qui peuvent aider.** La Bourse d'un membre ne montre que les besoins qui correspondent à *son* offre, avec la raison. Même
   moteur et mêmes règles que la recherche de l'auteur : la symétrie est testée sur tous les membres.
2. **Pas de suggestion sans preuve exacte, et abstention assumée.** Trois niveaux de preuve (déclarée, mentionnée, textuelle) ; seule la preuve déclarée donne « forte ».
3. **« Le LLM pour la nuance, le code pour les règles ».** Critères provisoires en flux, jamais utilisés pour décider ; le modèle ne voit pas les profils.
4. **Entre les événements, pour une seule communauté**, et non une plateforme événementielle.

**Ce qui n'est plus revendiqué** (correction après vérification des sources officielles) : le double consentement (Brella le fait),
les recommandations expliquées (Swapcard le fait), le matching par intention (Brella).

## 4. Ce qui fonctionne réellement (vérifié)
| Élément | Preuve |
|---|---|
| Boucle : besoin → critères → clarification → visibilité (publique, privée, anonyme) → Bourse → proposition → acceptation → rencontre → clôture « résolu grâce à X » | `scripts/parcours_demo.py` (scène) ; `test_boucle_bourse_complete_avec_anonymat` ; captures 10 à 16 ; vidéo |
| Cas crédibles : information manquante, aucune correspondance, refus, retrait du consentement, besoin modifié, besoin clos | tests `test_retrait_du_consentement_en_cascade`, `test_modification_versionnee_et_cloture_sans_suite` ; captures 21 à 26 |
| Autorisations et machine à états (rôles, 403/409 par appel direct) | tests + sondage manuel de 15 tentatives de contournement (toutes bloquées après correction du critère inventé) |
| Moteur : négations, préférences, implantation ou zone d'intervention, citations non probantes, spécialités, hors catalogue | jeu adversarial (EVALUATION.md) |
| Interface : bureau, mobile (onglets en bas), projecteur (scène 1600 px) | captures ; axe-core : **0 violation** sur 4 vues × 2 tailles (animations désactivées pendant la mesure) |
| Mode réel : sans données → 503 ; aucune identité simulée → 501 ; journal non exposé → 501 | `test_mode_reel_ne_simule_rien` |

## 5. Simulé ou fictif (séparé explicitement)
- **Données** : 37 profils fictifs, dont des pièges volontaires (frigoriste qui « ne livre pas », client qui « cherche un transporteur », garage dont les « clients sont des transporteurs », profil incomplet, refus d'introduction, visiteur, exposant, concurrent).
- **Autres humains** : en démo, on *incarne* tour à tour chaque membre (sélecteur « Vous incarnez (démo) » ou `/scene`). Chaque action est faite par le rôle autorisé. Aucun bouton « simuler la réponse ».
- **Envois** : aucun message, aucune coordonnée réelle ; « coordonnées partagées » est un état.

## 6. Ce qui reste à prouver
- **Utilité** : aucun membre réel interrogé. Le problème (H1) est une hypothèse.
- **Claude en conditions réelles** : jamais exécuté contre l'API (pas de clé). Le schéma de sortie structurée n'a jamais été soumis ; latence, coût et qualité inconnus. Harnais prêt : `scripts/verifier_claude.py`.
- **Généralisation** : jeu réservé (14 cas, une exécution) : **0 violation, mais 3 fausses abstentions**. Aucun jeu indépendant.

## 7. Évaluation (détails et définitions : EVALUATION.md)

| Jeu (statut) | succès@3 | violations | abstention correcte | critères conformes |
|---|---|---|---|---|
| Base (régression) | 16/16 (réf. 14/16) | 0/20 (réf. 8/20) | 20/20 (réf. 17/20) | — |
| Adversarial **avant** corrections | 10/13 (réf. 12/13) | 2/20 (réf. 6/20) | 17/20 (réf. 15/20) | 12/18 |
| Adversarial **après** corrections (entraînement) | 13/13 (réf. 12/13) | 0/20 (réf. 5/20) | 20/20 (réf. 16/20) | 18/18 |
| **Réservé** (une exécution) | **9/12** (réf. 11/12) | **0/14** (réf. 4/14) | **11/14** (réf. 13/14) | — |

« réf. » = mots-clés avec les mêmes filtres durs. Historique : `eval/archives/` (v1 avant le lot 2 ; première exécution du jeu réservé).
Le texte « 33 profils » dans l'archive v1 est une coquille du gabarit de l'époque : 37 profils étaient chargés.
Chronologie vérifiable dans git : jeu adversarial commité (`829e956`) **avant** les corrections ; jeu réservé commité (`0b47ceb`) **avant** sa première exécution.

## 8. Problèmes connus (non corrigés à ce jour)
| # | Problème | Gravité | Piste |
|---|---|---|---|
| 1 | Claude non vérifié contre l'API réelle (schéma, latence, coût) | Haute pour la démo « IA » | Clé API + `verifier_claude.py --confirmer` |
| 2 | Couverture du vocabulaire : pluriels non reconnus (« photovoltaïques »), paraphrases (« des agents pour gérer l'entrée »), « épiceries fines zurichoises » | Moyenne | Claude ; racinisation des expressions ; volontairement **non corrigé** avant l'audit (jeu réservé) |
| 3 | Négation d'un lieu non gérée (« surtout pas à Sion » → zone Valais obligatoire) | Faible à moyenne | Exclusion de lieu |
| 4 | Zones à la granularité canton ou région (Sion = Valais) ; pas de rayon kilométrique | Moyenne en réel | Communes et distances |
| 5 | Détection des phrases de recherche par liste de verbes ; sans verbe, tout le texte compte | Faible | Claude |
| 6 | Hors catalogue : racinisation grossière (6 lettres), seuil fixe | Moyenne | Mesurer contre Claude ou des embeddings avec de vraies données |
| 7 | Anonymat : le **texte libre** du besoin, visible par les aidants, peut révéler l'identité | Moyenne | Avertissement à la publication, ou reformulation |
| 8 | Journal d'événements avec identités (démo seulement ; fermé en mode réel) | Faible en démo | Flux filtré par membre authentifié |
| 9 | Pas d'authentification ni d'édition de profil ; le consentement est le seul réglage | Attendu (prototype) | — |
| 10 | Après un « décliner », le besoin peut réapparaître dans la Bourse du membre qui a décliné, avec « Proposer mon aide » | Faible ; choix discutable | À trancher (question 3) |
| 11 | Un exposant incarné peut publier un besoin (politique non décidée) | Faible | Dépend du brief |
| 12 | Dictée vocale non testée en salle ; Chrome envoie l'audio à Google | Faible (bonus) | Ne pas l'utiliser en secours |
| 13 | Les notifications peuvent masquer le bas des panneaux étroits de la scène | Cosmétique | — |
| 14 | Interface uniquement en français | Moyenne en Valais | Bilingue FR/DE |

## 9. Fichiers principaux modifiés dans ce lot
`prototype/app/{store.py (nouveau), main.py, matching.py, parser_rules.py, parser_llm.py, models.py, taxonomy.py}` ;
`prototype/web/{index.html, scene.html (nouveau), app.css, js/*.js (nouveau)}` ; `prototype/data/{taxonomie.json, profils_demo.json}` ;
`prototype/eval/{cas_adversariaux.json, cas_reserve.json, run_eval.py, archives/}` ; `prototype/tests/test_parcours.py` ;
`prototype/scripts/{parcours_demo.py, verifier_claude.py (nouveau)}` ; `docs/*` ; `docs/captures/*` (captures et vidéo).
Supprimés : `prototype/app/intros.py` (remplacé par `store.py`), `prototype/web/app.js` (remplacé par les modules).

## 10. Captures et vidéo (réellement produites par Playwright sur le vrai serveur)
`docs/captures/` : 10 à 16 (scène, 1600×900), 20 à 26 (cas limites, 1280×800, plus variantes `_mobile` 390×844), `demo_scene.webm` (49 s).

## 11. Trois questions précises pour l'auditeur
1. **Preuve** : le jeu réservé montre un moteur qui ne se trompe jamais (0/14) mais se tait trop (3/14). Pour un jury, vaut-il mieux montrer cet arbitrage tel quel, ou activer Claude en démo **avant** d'avoir mesuré qu'il ne réintroduit pas de violations ? Quel seuil de mesure exigeriez-vous avant de l'activer ?
2. **Différenciation** : après correction de la veille concurrentielle (Brella, Swapcard, Hivebrite), la thèse « le besoin va vers ceux qui peuvent aider, avec preuve et abstention » vous paraît-elle distinctive, ou un Hivebrite configuré ferait-il de même ? Quelle vérification suggéreriez-vous ?
3. **Consentement et Bourse** : trois choix discutables : (a) publier un besoin vaut consentement à recevoir des offres pour ce besoin ; (b) le retrait du consentement annule les demandes en attente mais conserve les relations acceptées ; (c) après un « décliner », le besoin peut réapparaître dans la Bourse de la personne. Lesquels changeriez-vous ?

## 12. Décisions demandées à Hiba (regroupées)
1. **Clé API Anthropic** pour mesurer Claude (≈ 0,56 USD estimés, 40 appels). Sans elle, la démo reste en mode « règles locales », et il faut le dire.
2. **Accès réseau** aux sites officiels (paramètres réseau de l'environnement) pour lire les sources complètes, *ou* transmission du brief dès sa publication.
3. **Texte complet de l'audit précédent** (sources et cas adversariaux), à déposer dans `docs/audits/`.
4. **Arbitrage produit** (facultatif, réversible) : garder la Bourse comme cœur de la démo (recommandé), ou revenir au seul parcours « je cherche → je sollicite » si le brief l'exige.

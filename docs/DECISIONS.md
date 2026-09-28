# Décisions : choix, alternatives, compromis

Chaque décision importante suit la même structure : **problème → choix → pourquoi → compromis → pour la défendre devant le jury.**

## 0. Correctif de cadrage (28.09.2026)

Hiba a précisé que son profil ne doit **pas** limiter le produit. Nous avons réexaminé chaque choix :

| Choix initial | Limité par le profil ? | Ajustement |
|---|---|---|
| Analyse du besoin par règles comme mode principal | En partie. Les règles avaient aussi été retenues par prudence : pas de clé API dans l'environnement | **Claude devient le mode vitrine** (sortie structurée validée par le code) ; les règles deviennent le filet de secours hors ligne |
| Concept limité au matchmaking | Oui, par cadrage initial | Ajout de concepts plus ambitieux (§1) ; le moteur actuel devient le noyau commun |
| Backend Python/FastAPI | Non, après réexamen (voir §3) | Conservé, pour ses mérites propres |
| Front sans framework | Non (voir §3) | Conservé ; ajout de la saisie vocale et des View Transitions |
| Pas d'embeddings, pas de LangGraph ni de MCP | Non : aucune utilité démontrée à ce stade | MCP identifié comme extension à forte valeur (§4.4) |

## 1. Concept

### Trois concepts réellement distincts (+ une extension)

**A. « Le Fil du Club » : du besoin à l'introduction consentie** *(construit)*
Un membre écrit ou dicte un besoin. Le produit en tire des critères éditables, propose 1 à 3 membres
avec des raisons citées mot pour mot, demande une introduction avec double consentement, puis suit le résultat.

**B. « La Bourse des besoins » : le besoin circule vers ceux qui peuvent aider**
Le membre publie un besoin (avec consentement). Le système l'adresse aux seuls membres capables d'y répondre,
qui choisissent de se manifester. Un digest mensuel et un mur projeté lors des soirées du Club rendent visible
l'entraide (« 12 besoins ouverts, 7 résolus ce mois »). Le moteur est le même que A, en sens inverse.

**C. « Le Compagnon de soirée » : avant, pendant et après chaque événement du Club**
Avant la Soirée Wow ou le Rendez-vous économique, chaque inscrit reçoit « 3 personnes à rencontrer, et pourquoi ».
Pendant l'événement, un QR code enregistre la rencontre. Après, le produit relance et consigne le résultat. Il prolonge
les événements existants au lieu d'en créer.

### Comparaison (qualitative, sans score inventé)

| Critère | A. Fil du Club | B. Bourse des besoins | C. Compagnon de soirée |
|---|---|---|---|
| Intensité du besoin | Forte quand un besoin précis survient (fournisseur, partenaire) | Moyenne à forte ; dépend de la culture d'entraide | Moyenne ; ponctuelle |
| Fréquence | Irrégulière, mais toute l'année | Continue si la masse critique est atteinte | 4 à 6 fois par an (calendrier du Club) |
| Adéquation au brief supposé (« prolonger la communauté ») | Forte : agit entre les événements | Très forte : rend la communauté visible | Forte : prolonge les événements existants |
| Différence avec l'existant | Nette (ni annuaire, ni app d'événement) | Nette (ressemble à BNI, mais outillé) | Faible : Brella et Swapcard le font déjà |
| Accès aux données | Profils structurés des membres (à obtenir, avec consentement) | Idem, plus des besoins publiés | Listes d'inscrits aux événements |
| Faisabilité en 24 h | **Déjà fonctionnel** | Réutilise A ; + publication et modération | Réutilise A ; + QR codes et agenda |
| Force de démonstration | Forte : transformation visible en 60 s | Forte en visuel (mur), plus faible en preuve | Moyenne : difficile à montrer sans événement réel |
| Valeur après l'événement | Directe | Dépend de l'animation par le Club | Saisonnière |

### Choix provisoire
**A comme noyau démontrable, B comme horizon du pitch.** A se prouve en 60 secondes et réutilise
exactement ce qui fonctionne. B (le même moteur en sens inverse : « 3 besoins du Club auxquels vous pouvez répondre »)
est l'extension la plus différenciante. Elle rend la réciprocité visible, déjà amorcée dans A par le badge « Réciprocité ».
C devient une fonctionnalité de A (une liste de rencontres par événement) plutôt qu'un produit.

**Compromis** : A sans B peut être perçu comme un « annuaire intelligent ». Réponse : l'abstention, le consentement
et le suivi du résultat ne relèvent pas d'un annuaire. Montrer B, même en maquette fonctionnelle, renforce ce point.

**Pivot si la recherche terrain contredit l'hypothèse** : si les membres disent « je sais déjà qui appeler, mais je n'ai pas
le temps d'entretenir mes relations », pivoter vers C avec suivi relationnel (rappels, historique des échanges) en gardant
le moteur de pertinence pour prioriser.

### Visualisation en réseau : écartée pour l'instant
Avec 1 à 3 suggestions, un graphe n'aide pas à comprendre *pourquoi* une personne correspond. Les cartes avec
citations le font. Un graphe pourra servir une vue « animateur du Club » (qui est isolé, quels secteurs se parlent). À tester seulement avec de vraies données.

## 2. Moteur : « le LLM pour la nuance, le code pour les règles »

**Problème.** Un membre écrit comme il parle. La décision de proposer quelqu'un doit rester sûre et vérifiable.
**Choix.** Pipeline en 4 étapes :
1. **Analyse du besoin** → critères typés (compétence, zone, langue, obligatoire ou souhaité, extrait source). Par Claude en
   direct si configuré, sinon par règles (taxonomie + désambiguïsation par indices).
2. **Filtres durs, écrits dans le code** : consentement, appartenance à la communauté, disponibilité, zone, langue, concurrence.
   Une donnée inconnue ne satisfait jamais un critère obligatoire.
3. **Classement** : couverture déclarée (offre) > déduite (présentation, phrases négatives ignorées) ; bonus sur les critères souhaités,
   la réciprocité et la similarité TF-IDF.
4. **Explications** : chaque raison est un extrait du profil **vérifié mot pour mot** avant affichage.

**Pourquoi.** Un LLM peut se tromper de sens. Il ne doit jamais pouvoir rendre éligible un profil exclu. Le modèle ne voit
d'ailleurs **pas** les profils : il ne fait que traduire la phrase en critères d'un vocabulaire fermé, que le code valide
(concept inconnu ignoré, extrait inventé retiré, panne → repli visible).
**Compromis.** La taxonomie est un vocabulaire fermé à entretenir. Un besoin hors taxonomie aboutit à une abstention
(voulue) plutôt qu'à une approximation.
**Pour le défendre.** « L'IA comprend la phrase, le code décide qui est proposé. Chaque raison affichée est une citation du profil. »

## 3. Stack

| Brique | Problème résolu | Pourquoi ce choix | Compromis | À savoir pour le jury |
|---|---|---|---|---|
| **FastAPI + Pydantic** | Un seul schéma de données pour l'API, la validation de la sortie du LLM et l'évaluation | Les schémas Pydantic servent à la fois de contrat d'API, de format de sortie structurée pour Claude (`messages.parse`) et de validation. L'écosystème Python sert aussi l'évaluation | Deux langages (Python + JS) | « Le même schéma contraint l'IA, l'API et les tests » |
| **JS natif + CSS, sans build** | Démo sur projecteur, sans réseau, modifiable par une équipe formée sur place | Zéro dépendance ni étape de build : `uvicorn` suffit. View Transitions API pour des transitions natives | Pas de composants réutilisables ; à migrer vers Svelte/React au-delà d'une dizaine d'écrans | « Nous avons optimisé pour la robustesse de la démo, pas pour la mode » |
| **SQLite** | Persister les introductions et leur historique | Fichier local, aucun service à lancer | Une seule instance ; PostgreSQL en production | Machine à états contrôlée côté serveur |
| **Claude (`claude-opus-5`, sortie structurée)** | Comprendre des formulations variées, en FR ou en DE | Sortie validée par schéma, puis revalidée par le code. Modèle configurable (`HACKVS_CLAUDE_MODEL`) | Coût et latence par requête (non mesurés : pas de clé dans l'environnement) ; dépendance réseau | Repli automatique et **affiché** sur les règles |
| **Web Speech API** (dictée) | Interaction mémorable, dire son besoin au lieu de l'écrire | Natif dans Chrome, aucune dépendance | Chrome envoie l'audio aux serveurs de Google (à signaler) ; absent de Firefox. Amélioration progressive | Si c'est indisponible, le bouton n'apparaît pas |
| **Playwright** | Vérifier le parcours réel avant chaque présentation | Rejoue la démo et produit les captures | Nécessite Chromium | `scripts/parcours_demo.py` = test de fumée |

**Écartés à ce stade (réversible)** :
- **Embeddings / recherche vectorielle.** Sur 33 profils fictifs, ils masqueraient le problème des faux amis au lieu de le résoudre,
  et aucun modèle n'était téléchargeable ici. À ajouter comme 3e signal de rappel avec des données réelles, **évalué contre l'actuel**.
- **LangGraph / multi-agents.** Le flux est linéaire (analyse → filtre → classement), sans boucle ni outil à choisir : pas de bénéfice observable.
- **Brouillon de message rédigé par un LLM.** Pour l'instant, gabarit déterministe construit à partir des preuves validées : aucune
  invention possible. Un LLM pourrait adapter le ton, à condition de revérifier chaque affirmation.

## 4. Choix produit notables

1. **Abstention assumée** : « Je préfère ne rien vous proposer plutôt qu'un mauvais contact. » Les pistes plus larges sont
   montrées séparément, étiquetées « non vérifiées », et limitées à la catégorie parente directe.
2. **Raisons d'exclusion sans nom** : on affiche « 1 profil ne souhaite pas recevoir d'introductions », jamais qui.
3. **Double consentement** : les coordonnées ne sont partagées qu'après acceptation. En démo, la réponse est simulée par un bouton
   au contour pointillé rouge, étiqueté « Simuler ». En mode réel, l'API refuse toute simulation (403).
4. **Extension à forte valeur : un serveur MCP « Club ».** Exposer `chercher_membres`, `demander_introduction` et `mes_introductions`
   comme outils MCP. Un membre pourrait alors solliciter le Club depuis Claude ou ChatGPT, avec les mêmes garde-fous (le code
   décide). Démonstration possible : « même depuis votre assistant IA, le consentement tient ». Non construit ; candidat au cycle 3.

# Décisions : problème, proposition de valeur, choix et compromis

Format de chaque décision : **problème → choix → pourquoi → compromis → pour la défendre devant le jury.**
Mise à jour : lot 2 (28.09.2026). Les décisions du cycle 1 encore valables sont conservées ; les révisions sont signalées.

## 1. Le problème, l'existant, notre proposition

**Problème visé (hypothèse, non confirmée par des membres).** Le Club des Affaires réunit plus de 100 dirigeants lors de rendez-vous
physiques (pré-ouverture, Rendez-vous économique, Soirée Wow, soirée de printemps : faits publics). **Entre deux rendez-vous**, quand un
membre a un besoin précis (un transporteur, un juriste, un distributeur), rien de visible ne lui permet de savoir qui, dans le Club,
peut l'aider. Et un membre qui pourrait aider n'apprend jamais que ce besoin existe.

**Ce qui existe** (RESEARCH.md §C, sources officielles) :
- plateformes événementielles (Brella, Swapcard, Grip) : matching par intention, rendez-vous à double consentement, recommandations expliquées, **le temps d'un événement** ;
- plateforme de communauté (Hivebrite) : annuaire, mentorat, **permanente** ;
- réseaux locaux (CCI Valais, FER Valais, Valais Network) et BNI.

**Notre proposition de valeur, spécifique.**
> *Un membre dit ce dont il a besoin ; le Club le fait parvenir aux seuls membres capables d'y répondre, avec la preuve de pourquoi eux ;
> ceux-ci proposent leur aide ; la mise en relation se fait avec consentement, et le Club voit ce qu'elle a produit.*

Les trois différences défendables :
1. **Déclenché par un besoin et dirigé vers les bons membres (sens inverse)**, entre les événements. C'est la Bourse.
2. **Preuves exactes et abstention** : pas de suggestion sans citation vérifiable du profil ; « je préfère ne rien proposer » plutôt qu'un mauvais contact.
3. **Outil d'une communauté**, pas une plateforme événementielle.

**Correction du lot 2.** Le double consentement et les « recommandations expliquées » ne sont **plus** présentés comme distinctifs :
Brella et Swapcard les proposent déjà.

**Hypothèses encore non confirmées** : voir ASSUMPTIONS.md (H1 à H8). Les plus structurantes : H1 (des besoins surviennent entre les
événements), H3 (les membres rempliront 3 lignes de profil), H4 (le Club animerait une Bourse).

**Ce qui justifierait un changement de direction** (à surveiller dès le brief) :

| Signal | Pivot proposé |
|---|---|
| Le brief porte sur les **exposants** ou les **visiteurs**, pas sur les membres | Réutiliser le moteur pour « 3 exposants à voir selon votre besoin », avec la même abstention |
| Les membres disent « je sais qui appeler, je n'ai pas le temps d'entretenir mes relations » | Compagnon relationnel : rappels et suivi après les rencontres (concept C du cycle 1), le moteur servant à prioriser |
| Le Club ne veut pas de publication de besoins (confidentialité) | Garder le mode privé seul (solliciter soi-même), sans Bourse |
| Des données réelles sont fournies, mais sans champ « offre » structuré | Priorité au hors catalogue et à l'extraction par LLM depuis les descriptions, avec validation humaine |
| Le jury attend surtout de l'IA générative visible | Brancher Claude en direct (flux déjà prêt) sans changer les garde-fous |

## 2. Concept retenu : la Bourse des besoins (A + B du cycle 1)

**Problème.** Au cycle 1, le parcours « je cherche → je sollicite » (A) ressemblait à un annuaire intelligent.
**Choix.** Le même moteur, dans les deux sens :
- **auteur** : besoin → critères → aperçu → publication (ou mode privé) → sollicitation ou offres reçues → suivi → clôture ;
- **membre qui peut aider** : sa **Bourse** ne montre que les besoins qui correspondent à *son* profil, avec la raison → il propose son aide.
**Pourquoi.** C'est ce qui transforme un annuaire en communauté : l'aide devient visible et réciproque. Le concept C (compagnon de
soirée) reste une extension future du même moteur.
**Compromis.** Il faut une masse critique de membres et de profils renseignés. Sans animation par le Club, la Bourse peut rester vide.
**Pour la défendre.** « Le même moteur, les mêmes règles, dans les deux sens : si Julien voit le besoin de Sophie, c'est exactement parce
que Sophie aurait vu Julien. » (propriété testée : `test_bourse_et_correspondances_sont_symetriques`)

## 3. Moteur : « le LLM pour la nuance, le code pour les règles » (conservé, renforcé)

Pipeline : analyse du besoin → **filtres durs dans le code** → classement → **preuves vérifiées** → abstention si rien de fiable.

Corrections du lot 2, une par fragilité signalée par l'audit :

| Fragilité | Correction | Vérifiée par |
|---|---|---|
| Préférences transformées en obligations | Portée des marqueurs limitée à la clause (`,` `;` `:` `mais`) ; les compétences secondaires sont souhaitées par défaut ; des marqueurs forts existent (« impérativement »…) | cas `pref_*`, 18/18 critères conformes |
| Négations mal interprétées | Une compétence niée devient une **exclusion** appliquée aux offres ET aux présentations ; dans un profil, l'expression la plus longue l'emporte (« sécurité informatique » ≠ « informatique ») | `neg_*`, `test_preference_negation_implantation` |
| Spécialités mal interprétées | Le plus précis l'emporte (« avocat » + « droit du travail » → droit du travail) | `spec_*` |
| Citations exactes qui ne prouvent pas la compétence | Une phrase de présentation ne prouve une compétence que si elle **affirme une offre** (« nous assurons… ») et ne décrit ni un besoin (« nous cherchons… ») ni une clientèle (« nos clients : … ») ; ce type de preuve donne au mieux une correspondance « partielle » | `citation_*` + profils pièges p33 et p34 |
| Confusion implantation / zone d'intervention | Deux critères distincts : **zone d'intervention** (où il travaille : `zones_service`) et **implantation** (où il est installé : commune) ; « nous sommes basés à Sion » = contexte, pas critère ; affichage « Implanté·e à X · intervient : Y » | `implantation_*` |
| Résultats obsolètes après modification | Besoins **versionnés** ; tout critère modifié **grise** les résultats et bloque les actions jusqu'à actualisation ; une mise en relation garde la version d'origine et affiche « besoin modifié depuis » | `test_modification_versionnee…`, capture 24 |
| Limites du vocabulaire fermé | Critère **hors catalogue** (recherche par mots dans les offres déclarées, seuil strict), clarification en cas d'ambiguïté, abstention sinon | jeu adversarial ; EVALUATION.md |

**Compromis assumé.** Le jeu réservé montre un moteur **précis mais peu couvrant** sur des formulations nouvelles (3 fausses abstentions sur 14, 0 violation).
Nous avons préféré un système qui se tait à un système qui se trompe. Le LLM est la voie prévue pour améliorer la couverture, sans toucher aux garde-fous.

## 4. Claude : sortie structurée en flux, validée par le code

**Problème.** Les règles ne comprennent pas les paraphrases ; une IA générative peut halluciner.
**Choix.** `client.messages.stream(..., output_config={"format": {"type": "json_schema", …}})`. Pendant la génération, les critères
complets sont affichés comme **provisoires** (pointillés, recherche désactivée). À la fin, le code valide : vocabulaire fermé, extraits présents
dans le texte, compétence principale obligatoire. En cas de panne, de refus ou de JSON invalide, l'analyse **bascule sur les règles et le signale**.
Le modèle ne voit **jamais** les profils.
**Pourquoi.** Afficher les critères au fur et à mesure rend la transformation visible et réduit l'attente perçue, sans jamais agir sur
une donnée non validée.
**Compromis.** Non exécuté contre l'API réelle (pas de clé). Latence et coût inconnus. Modèle par défaut `claude-opus-5` (configurable).
Le paramètre de repli côté serveur d'Anthropic n'est pas activé : c'est notre repli local qui s'applique.
**Pour la défendre.** « L'IA propose, le code dispose. Un critère provisoire ne décide jamais rien. »

## 5. Stack (réexaminée sans considération de familiarité)

| Brique | Problème résolu | Pourquoi | Compromis | À savoir pour le jury |
|---|---|---|---|---|
| **FastAPI + Pydantic** | Un même schéma pour l'API, la sortie du LLM, l'évaluation | Les schémas servent de contrat partout | Deux langages (Python + JS) | « Le même schéma contraint l'IA, l'API et les tests » |
| **SQLite + magasin unique** (`store.py`) | Des états cohérents entre toutes les vues | Toutes les règles métier au même endroit, transactions sous verrou | Une seule instance ; PostgreSQL en production | Une action faite par API directe ne contourne aucune règle |
| **Server-Sent Events** (`/api/flux`, `/api/analyser/flux`) | Mise à jour en direct entre deux membres ; critères en flux | Natif dans le navigateur, unidirectionnel (suffisant), sans dépendance | Pas de canal retour (inutile ici) ; reconnexion gérée | La scène à deux écrans montre une vraie base partagée, pas une animation |
| **JS natif en modules ES, sans build** | Démonstration hors ligne, modifiable par l'équipe | Zéro étape de build ; un module par vue | Pas de framework de composants ; à migrer au-delà d'une dizaine d'écrans | Choix de robustesse pour le jour J |
| **View Transitions API, animations CSS** | Montrer ce qui change, sans décor | Natif, désactivé si l'utilisateur préfère réduire les animations | Rendu variable selon le navigateur | Chaque animation porte une information (arrivée d'un besoin, fil tracé) |
| **Playwright** | Tester le parcours réel, produire captures et vidéo | Le même script sert de test de fumée et de générateur de support | Nécessite Chromium | `scripts/parcours_demo.py --video` |

**Écartés à ce stade (réversibles)** : embeddings (voir EVALUATION.md) ; LangGraph et multi-agents (flux linéaire, sans boucle ni choix d'outil : aucun bénéfice observable) ;
brouillon de message par LLM (le gabarit déterministe n'invente rien) ; serveur MCP « Club » (intéressant pour l'après-hackathon : exposer
`chercher_membres`, `publier_besoin` et `proposer_aide` aux assistants IA des membres avec les mêmes garde-fous ; non construit).

## 6. Choix produit notables

1. **Humains simulés = identités incarnées, pas des boutons.** En démo, on incarne tour à tour Sophie et Julien (sélecteur « Vous incarnez (démo) »
   ou vue `/scene`). Chaque action est réellement faite par le rôle autorisé. En mode réel, l'API refuse toute identité simulée (501).
2. **Publier = consentir aux offres pour ce besoin.** Un auteur peut recevoir des propositions d'aide même s'il a désactivé les introductions entrantes en général.
3. **Anonymat facultatif** : nom masqué dans la Bourse (« Un membre du Club · secteur boissons »), révélé seulement à la personne dont on accepte l'aide.
4. **Retrait du consentement** : le membre disparaît des recherches et de la Bourse ; ses demandes **en attente** sont annulées avec un motif visible ; les relations **déjà acceptées** restent (le consentement avait été donné) et peuvent être annulées.
5. **Clôture d'un besoin** : « Résolu grâce à X » (seulement avec une relation acceptée) ou « Clos sans suite » ; les demandes en attente sont annulées.
6. **Exclusions anonymes** : « 1 membre ne souhaite pas recevoir d'introductions », jamais qui.
7. **Visualisation en réseau** : toujours écartée. Le « pont » besoin ↔ preuves explique mieux une correspondance qu'un graphe.

## 7. Historique (cycle 1, résumé)
Trois concepts comparés (A : du besoin à l'introduction ; B : Bourse des besoins ; C : compagnon de soirée). A était démontrable et B portait l'horizon.
Au lot 2, B a été construit sur le moteur de A ; C reste une extension.

## 8. Lot 3 : ce qui a été ajouté pour gagner, et pourquoi

| Ajout | Problème résolu | Pourquoi ce choix | Compromis | À dire au jury |
|---|---|---|---|---|
| **Vue du Club** (`/club`) : compétences à recruter, offres à faire connaître, activité | Le sponsor (le Club) doit voir ce qu'il y gagne ; une abstention était une impasse | Un besoin sans réponse devient une **entreprise à inviter** : c'est l'argument d'affaires du Club, qui vend des adhésions | Historique fictif nécessaire pour la démo (étiqueté) ; agrégats seulement, sans nom | « Un membre aide un membre ; quand personne ne peut aider, le Club sait qui inviter. » |
| **Profil en 30 secondes** | Risque n°1 : les membres ne rempliront pas de profil structuré | Description libre → offres, recherches, zones, langues **proposées** ; le membre valide ; la phrase devient la preuve | Extraction par règles (même limites de vocabulaire) ; Claude pourrait la reprendre | « Trente secondes, et c'est vous qui validez. » |
| **Acte 2 « le Club se répare »** (scène Club + membre) | Montrer la boucle membre → communauté → organisation | Deux états réels comparés : « Comblé » n'est affiché que si la compétence a vraiment disparu de la liste | Nécessite l'historique chargé avant la démo | Le jury voit le changement en direct |
| **Couverture** : pluriels générés, allemand, paraphrases | 3 fausses abstentions sur 14 au lot 2 ; Valais bilingue | Variantes générées au chargement (taxonomie lisible), sans collision | Mesure du gain circulaire (réservé n°2 écrit en connaissant les ajouts) | Chiffre de référence inchangé : première exécution du réservé n°1 |
| **Présentation intégrée** (`/presentation`) | Pitcher sans improvisation, hors ligne | Le support est servi par l'application et utilise ses vraies captures | Pas d'export .pptx (au besoin : impression PDF depuis le navigateur) | Notes d'orateur avec P1/P2 |
| **QR et `/rejoindre`** | Faire essayer le jury | QR généré localement (paquet `qrcode`), aucun service externe | Nécessite une URL joignable (Wi-Fi partagé ou déploiement) | « Scannez, vous incarnez un membre fictif. » |
| **Dockerfile vérifié + guide Cloud Run** | Une URL publique le jour J | Image construite et testée ici (249 Mo, non root) | Une seule instance (SQLite et SSE locaux) ; publier est une décision de Hiba | — |

Écartés à nouveau : graphe de réseau (pas plus explicatif que le pont besoin ↔ preuves), multi-agents (aucune boucle à orchestrer), tableau de bord décoratif (chaque chiffre porte son dénominateur et sa définition).

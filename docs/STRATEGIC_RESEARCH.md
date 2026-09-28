# Recherche stratégique : dépasser le matchmaking

Date : 28.09.2026. Méthode : quatre chercheurs indépendants (open source, commercial, académique, expériences
internationales), puis boucle **hypothèse → prototype → mesure → garder / tuer**. Limite de méthode : les pages web
n'ont pas pu être lues en entier (accès bloqué) ; les faits viennent d'extraits de recherche recoupés, de dépôts clonés
et lus, et sont marqués « non vérifié » quand ils ne sont pas recoupés. Aucune donnée réelle de membre n'a été utilisée.

**Conclusion en une phrase.** Tout ce qu'un jury attend (matching IA, explication, double opt-in, agents qui se parlent,
MCP, planification) existe déjà dans le commerce ; ce qui n'existe pas, c'est un Club capable de rapprocher les
intentions **que personne n'écrit jamais**, sans que la plateforme elle-même puisse les lire. C'est le concept retenu :
**les intentions scellées**.

---

## 1. Solutions existantes (ce qui est banal en 2026)

Source : chercheur B (extraits de recherche, sites des éditeurs, G2, presse ; détails et URL dans l'annexe).

| Déjà banal | Qui le fait |
|---|---|
| Matching IA sur profils et objectifs, y compris offre ↔ besoin | b2match, Brella, Grip, Swapcard, 2Connect (« complementarity, not similarity ») |
| Explication du match, message d'intro rédigé par l'IA | Highbar, 2Connect (avec « points de friction »), The Swarm |
| Double opt-in avant l'intro | Boardy, Brella, Lunchclub |
| Planification optimisée des rendez-vous, notation après coup | Grip MustMeet, b2match, Swapcard |
| Agent IA personnel qui parle aux autres agents | **Bebb** (usebebb.com), Boardy (vocal) |
| Serveur MCP | The Swarm, Connect The Dots, Eventtia |
| Suivi « affaire conclue » d'une recommandation | BNI Connect (manuel) |
| Communauté à l'année + pages de networking après événement | Hivebrite, Swapcard, **CCI Valais** (Odoo, présenté le 02.06.2026 : concurrent local que le jury connaîtra) |

**Conséquence** : une grande partie de notre prototype actuel (matching expliqué, Bourse, soirée optimisée, MCP) est
**attendue**. C'est une base solide, pas un argument de différenciation.

## 2. Paysage open source

Source : chercheur A (dépôts clonés, code lu ; commit et licence relevés).

| Projet | Ce qui est réellement dans le code | Leçon pour nous |
|---|---|---|
| chrisroge/agent-rendezvous (`f158ccc`, AGPL-3.0, protocole CC BY) | Agents personnels, éligibilité mutuelle « muette » (`mutuallyEligible`, ne dit jamais quel critère a échoué), recommandation scellée YES/YES, révélation après double consentement, étiquettes EXPLICIT/OBSERVED/INFERRED | Le plus proche. Mais le **serveur lit les intentions** (Postgres) et c'est pour la rencontre amoureuse |
| tacitprotocol/tacit (`e03773e`, MIT) | Intents signés, relais de matching ; la spec exige le chiffrement de bout en bout, **absent du code** (grep) ; score pondéré qui ne vaut que 0 ou 100 | Ce qu'il ne faut pas faire : promettre la confidentialité sans l'implémenter |
| a2aproject/A2A (`72b3761`, Apache-2.0) | Cartes d'agent signées, carte étendue après authentification, état « input required » | Le protocole prévoit la révélation progressive, pas le secret vis-à-vis de l'intermédiaire |
| OpenMined/PSI (`d1edfcf`, Apache-2.0) | PSI ECDH, option « taille de l'intersection seulement » | La primitive existe et est mûre |
| sd-jwt-python, swiyu (e-ID suisse) | Divulgation sélective champ par champ | Piste pour prouver « membre du Club » sans tout dévoiler |
| A2CN (`55391cb`) | Record de transaction signé par les deux parties | Piste pour tracer un accord sans tiers de confiance |

## 3. Recherche académique

Source : chercheur C (références vérifiées par DOI ou arXiv).

- **Frictions d'appariement réelles** : des rencontres structurées augmentent de 75 % la co-soumission de projets
  (Boudreau et al., *REStat* 2017) ; des interactions imposées multiplient par plus de 8 les chances de collaborer
  (Zajdela et al., *Phys. Rev. Research* 2022). Cela justifie notre plan de soirée, sans le rendre original.
- **Liens modérément faibles** les plus utiles (Rajkumar et al., *Science* 2022, 20 M de personnes) ; chevauchement
  **partiel** d'intérêts plus productif (Lane et al., *SMJ* 2021) : la similarité maximale n'est pas le bon objectif.
- **Recommandation réciproque et équité** (Tomita et Yokoyama, RecSys 2024) : sans régulation, les « stars » sont submergées.
- **Cycles d'échange** (Roth, Sönmez, Ünver, *QJE* 2004) : non transposés aux services entre PME, à la connaissance du chercheur.
- **Agents LLM** : mieux vaut les brancher sur un **mécanisme** que les laisser négocier librement (Hoshino et al.,
  arXiv 2606.03030, 2026 ; biais de première proposition 10 à 30× dans Magentic Marketplace, arXiv 2510.25779).
- **Découverte privée de contacts** par PSI (De Cristofaro et al., IACR ePrint 2011/026).

## 4. Expériences internationales

Source : chercheur D (18 expériences, extraits datés).

- **Un algorithme ne crée pas l'intention** : chez Web Summit, 3 rendez-vous sur ~40 viennent de l'algorithme ;
  Start-Up Nation Finder compte 1 million d'utilisateurs pour 2 400 connexions ; Shapr et Bumble Bizz ont disparu.
  Ce qui marche part d'un **besoin explicite** (EEN, Slush, Venture Kick).
- **L'échec, c'est l'absence de réponse** : 60 % des demandes Brella non acceptées ; 65-75 % sans réponse sur les
  salons sans IA (Grip, chiffre fournisseur).
- **La confiance se perd en un envoi** (campagne d'e-mails de Boardy, janvier 2025) ; les dispositifs crédibles
  filtrent (J-GoodTech, S-GE, Bookface).
- **Atout d'un petit club** : « les membres savent qui cherche un successeur » : une connaissance tacite qui circule
  aujourd'hui par la rumeur.

## 5. Contexte suisse

- ≈ 101 427 entreprises cherchaient un successeur en 2024, soit plus d'une PME sur six (Dun & Bradstreet, cité par le
  SECO : [kmu.admin.ch](https://www.kmu.admin.ch/kmu/fr/home/actuel/interviews/2025/prendre-soin-successions-renforce-economie.html)).
- Une cession se prépare dans la confidentialité : une rumeur peut faire partir employés et clients
  ([Acquira](https://acquira.com/confidentiality-business-selling/), [Midstreet](https://www.midstreet.com/blog/confidentiality-selling-business)).

## 6. Ce que les autres équipes construiront (chercheur F, notre analyse)

Même brief, 24 h : (1) un **chatbot** RAG sur l'annuaire ; (2) un **matching par embeddings** « qui devrais-je
rencontrer » avec un score ; (3) une **appli de la Foire** (agenda, QR de contact) ; (4) un **tableau de bord** pour le
Club ; (5) un **multi-agent** avec orchestrateur ; (6) un **MCP** posé sur l'annuaire. Toutes supposent que les membres
**déclarent** leurs besoins à une plateforme qui les lit. Aucune ne peut servir un besoin qu'un dirigeant ne déclarera
jamais à personne.

**Question décisive** : « Quelle fonctionnalité rendrait notre solution impossible à confondre avec les trois autres ? »
Réponse : **un besoin qui ne peut exister que si la plateforme est aveugle.**

## 7. Espace d'opportunités : matrice de différenciation

Notes de 1 à 5. **Score = valeur + nouveauté + effet démo + faisabilité + preuve − probabilité que d'autres le fassent
− dépendance aux données** (pondération simple et explicite, pour comparer, pas pour décider seul).

| # | Idée | Valeur | Nouveauté | Démo | Faisab. | Données | Risque | Preuve | Réutil. | Autres équipes | **Score** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Intentions scellées** (PSI entre agents, Club aveugle, jetons k-anonymes, révélation équitable) | 5 | 5 | 4 | 4 | 2 | 3 | 5 | 3 | 1 | **20** |
| 2 | Circuits d'entraide (cycles à la Roth) | 3 | 5 | 5 | 4 | 4 | 3 | 4 | 5 | 1 | **16** |
| 3 | Le Club garant (intro parrainée par un membre commun, clôture triadique +35 %) | 4 | 3 | 3 | 4 | 3 | 2 | 3 | 4 | 2 | **12** |
| 4 | Registre des résultats signé par les deux parties (réputation par les issues) | 4 | 3 | 2 | 3 | 4 | 2 | 2 | 3 | 1 | **9** |
| 5 | Pont dosé (liens modérément faibles, trous structuraux) | 3 | 4 | 3 | 3 | 5 | 3 | 3 | 3 | 1 | **10** |
| 6 | Agents mandataires qui font la due-diligence (à la RAP) | 4 | 2 | 4 | 3 | 3 | 4 | 2 | 3 | 3 | **9** |
| 7 | Mécanisme d'acceptation différée pour les créneaux de soirée (0 paire bloquante) | 3 | 3 | 2 | 5 | 2 | 1 | 5 | 4 | 1 | **15** |
| 8 | Recommandation équitable anti-congestion (« stars » protégées) | 3 | 3 | 2 | 4 | 3 | 2 | 4 | 4 | 1 | **12** |
| 9 | Contacts / fournisseurs en commun sans les révéler (PSI-cardinalité) | 3 | 4 | 3 | 4 | 4 | 3 | 3 | 2 | 1 | **12** |
| 10 | Badge membre vérifiable dans le wallet swiyu | 2 | 4 | 3 | 1 | 2 | 4 | 2 | 1 | 1 | **9** |
| 11 | Détection de besoins jamais exprimés (inférence sur profils) | 4 | 3 | 4 | 2 | 5 | 5 | 1 | 3 | 3 | **6** |
| 12 | Symbioses de ressources (capacités vides, saisonnalité) | 4 | 3 | 3 | 2 | 5 | 3 | 2 | 2 | 1 | **8** |
| 13 | Jumeau IA de chaque dirigeant (entretien → agent) | 3 | 3 | 4 | 2 | 4 | 5 | 1 | 2 | 3 | **6** |
| 14 | « Je connais quelqu'un qui connaît » (recherche indirecte dans le graphe) | 3 | 2 | 3 | 3 | 5 | 3 | 2 | 2 | 2 | **6** |
| 15 | Stratégie de networking personnelle générée | 2 | 2 | 3 | 4 | 3 | 2 | 1 | 3 | 4 | **5** |
| 16 | Chatbot du Club / RAG sur l'annuaire | 2 | 1 | 2 | 5 | 2 | 2 | 1 | 4 | 5 | **4** |
| 17 | Matching à trois pour projets communs (équipes) | 3 | 3 | 3 | 3 | 4 | 3 | 2 | 4 | 2 | **8** |

## 8. Trois concepts

### Concept A : **Intentions scellées** (retenu)
1. **Phrase de 10 s** : « Dites à votre agent ce que vous ne direz à personne ; le Club vous présente seulement si l'autre veut exactement l'inverse, et même le Club ne l'aura jamais su. »
2. **Problème** : les besoins les plus précieux d'un club d'affaires (céder, reprendre, lever des fonds, trouver un successeur) ne sont jamais publiés ; dans un petit club, même une annonce « anonyme » désigne son auteur (mesuré : 26 membres sur 34 sont seuls de leur secteur).
3. **Expérience** : le dirigeant confie une intention à son agent (sur son poste) ; il ne se passe rien, pour personne, jusqu'à ce qu'une intention inverse apparaisse ; les deux agents le signalent à leurs humains ; chacun décide de dévoiler le secteur précis, puis son identité, **seulement si l'autre le fait aussi**.
4. **Architecture** : agent personnel (intentions en clair chez le membre) → jetons **k-anonymes** calculés sur l'annuaire public → **PSI Diffie-Hellman sur ristretto255** entre agents, via le **serveur du Club en simple relais** (points aléatoires, pseudonymes) → notification locale → révélation progressive (secteur, puis identité par **engagement puis ouverture simultanée**) → introduction dans le parcours existant (consentement, suivi, rendez-vous).
5. **Agents** : un agent personnel par membre ; aucun agent central ; aucun LLM nécessaire au mécanisme (un LLM peut aider à **formuler** l'intention, localement).
6. **Données** : l'annuaire public du Club (secteurs), les intentions saisies par chaque membre (qui ne quittent pas son agent).
7. **Technologies** : libsodium (ristretto255, via ctypes), repli RFC 3526 ; notre API, MCP, parcours d'introduction existants.
8. **Existe déjà** : double opt-in (banal) ; agents qui se parlent (Bebb) ; éligibilité muette (agent-rendezvous) ; PSI (bibliothèques, messageries) ; plateformes de cession (courtiers, bourses d'entreprises).
9. **Réellement nouveau** : la combinaison **intention sensible B2B + plateforme structurellement aveugle + anonymat adapté aux petits groupes (k-anonymat des jetons) + révélation équitable**, dans un club local de confiance. Non observé dans le commerce ni dans les dépôts lus (formulation prudente : « non observé »).
10. **Démo 60 s** : voir §12.
11. **Démo 3 min** : les 60 s + « ce que voit le Club » (flux de points aléatoires, attaque par dictionnaire en direct : 0) + la bascule vers l'introduction et la soirée.
12. **Risques** : adoption (les dirigeants oseront-ils ?) ; sondage par un faux acheteur (atténué, voir §10) ; modèle semi-honnête ; volume faible par définition.
13. **Preuve** : exactitude contre le calcul en clair, attaques, coût (§10).
14. **Pourquoi on s'en souviendrait** : c'est le seul projet où l'on peut dire « notre base de données ne contient pas ce que nos membres cherchent, et c'est pour cela que ça marche ».

### Concept B : **Circuits d'entraide** (don croisé de reins appliqué aux PME)
- **Phrase** : « Personne ne vous doit rien, mais trois membres peuvent s'aider en boucle. »
- **Nouveau** : cycles A→B→C→A (Roth, Sönmez, Ünver 2004) pour des services B2B ; programme en nombres entiers déjà maîtrisé.
- **Mesure (H1)** : sur les 37 profils écrits à la main, les membres « donnant-donnant » passent de 4 (échanges directs) à 7 (cycles ≤ 3) ; sur les 150 synthétiques : **0 dans les deux cas** (le générateur ne donne des besoins qu'à un tiers des membres).
- **Verdict** : **mis en réserve**. Très dépendant de données qui n'existent pas encore ; brillant sur un graphe dense, vide sur un graphe clairsemé. À rejouer avec de vrais besoins.

### Concept C : **Le Club garant** (introductions parrainées et registre des résultats)
- **Phrase** : « Une introduction vaut ce que vaut celui qui la recommande. »
- **Appui** : clôture triadique +35 % (Mosleh et al., *PNAS* 2025) ; BNI suit les affaires à la main ; records signés par les deux parties (A2CN).
- **Verdict** : **rejeté comme concept principal** (valeur réelle mais peu surprenante ; demande un historique de relations que le Club n'a pas encore). Gardé comme couche de confiance future.

## 9. Concept retenu

**Intentions scellées**, parce qu'il est le seul à cumuler valeur élevée (succession : 1 PME sur 6), nouveauté
défendable, démonstration visuelle (« ce que voit le Club »), preuves mesurables et faible probabilité qu'une autre
équipe le fasse. Il **réutilise** l'existant au lieu de le remplacer : une compatibilité débouche sur le parcours
d'introduction, de rendez-vous et de soirée déjà construit.

Rôle de chaque brique, sans décor :
- **Agent personnel** : garde l'intention, fait les calculs, demande l'accord de son humain à chaque étape.
- **Protocole agent ↔ agent** (ce qu'A2A appelle une tâche entre agents) : la PSI ; le serveur du Club n'est qu'un relais.
- **MCP** : l'assistant IA du membre peut **l'aider à formuler** son intention et lire les compatibilités, jamais les révéler.
- **Code déterministe** : k-anonymat, taille fixe des ensembles, plafond anti-sondage, révélation équitable.

## 10. Preuves (prototype isolé, `prototype/experiences/`)

`python -m experiences.mesure_intentions --k 3` — **Club SYNTHÉTIQUE** (150 membres générés), intentions générées
(16 % de cédants, hypothèse calée sur Dun & Bradstreet ; le reste est une hypothèse de génération).

| Mesure | Résultat |
|---|---|
| Intentions scellées | 74, portées par 64 membres (30 cessions, 10 reprises, 11 levées de fonds, 4 investisseurs, 10 recherches de dirigeant, 9 candidats) |
| Paires compatibles trouvées / attendues (calcul en clair de référence) | **19 / 19** : précision 1,0, rappel 1,0 |
| Ce que le Club peut lire | **0** intention ; 72 576 points aléatoires relayés |
| Attaque du Club par dictionnaire complet (222 jetons possibles) | **0** réussite |
| Traçage d'un point d'une session à l'autre | **0** point répété |
| Secteurs généralisés par le k-anonymat (k = 3) | 14 sur 92 |
| Coût | 4 032 sessions PSI, 2,3 Mo relayés, **8,3 s** pour toutes les paires (64 participants, CPU) ; ristretto255 : 0,063 ms par opération |
| **Référence : notre Bourse actuelle** | 74 / 74 intentions **lisibles par le serveur** ; dans le Club de démonstration, **26 membres sur 34** seraient ré-identifiés par leur seul secteur dans une annonce « anonyme » (sur le Club synthétique, plus peuplé : 0 sur 30) |

**H2 — deviner l'auteur d'une intention de cession** (`python -m experiences.mesure_reidentification`, l'annuaire
public étant supposé connu de tous) :

| Club | Bourse « anonyme » actuelle (lue par TOUS) | Intentions scellées (contrepartie seulement ; autres : 0) |
|---|---|---|
| Démo, 34 membres | 82 % en moyenne ; 26 auteurs désignés à coup sûr | 5 % en moyenne ; 17 % au pire |
| Synthétique, 150 | 19 % en moyenne ; 2 désignés à coup sûr | 14 % en moyenne ; ≤ 33 % (k = 3), ≤ 20 % (k = 5) |

**H3 — y a-t-il assez de volume ?** (`python -m experiences.sensibilite_volume`, Monte-Carlo SYNTHÉTIQUE, 16 % de
cédants, secteurs en loi de Zipf ; compatibilité au seul niveau du secteur, donc **bornes hautes**) :

| Périmètre | Repreneurs 1 % | 2 % | 4 % |
|---|---|---|---|
| 1 club de 100 (≈ 16 cédants) | 2,4 cédants avec un repreneur compatible | 4,4 | 7,0 |
| 3 clubs fédérés | 17,4 | 25,1 | 32,8 |
| 10 clubs / CCI | 104 | 125 | 143 |

Verdict : l'idée n'est pas tuée, mais **un seul club ne suffit pas** ; la valeur apparaît en **fédération**, et la PSI
est précisément ce qui permet à plusieurs clubs (dont la CCI Valais, concurrent local) de confronter leurs intentions
**sans échanger leurs listes de membres**. Le concurrent devient un partenaire possible.

**Limites honnêtes** : sécurité semi-honnête (un agent qui ment sur son intention n'est pas empêché) ; un faux acheteur
peut **sonder** l'existence d'un cédant dans une catégorie, mais sans identité (pseudonymes par session, catégories
k-anonymes), au plus 6 jetons par sens et par tour ; la personne sondée voit la compatibilité et peut ne jamais
révéler. La volonté réelle des dirigeants de confier une intention à un agent n'est **pas mesurée** : c'est le premier
test à faire avec de vrais membres.

## 11. Idées rejetées ou différées (et pourquoi)

- **Chatbot / RAG sur l'annuaire, matching par embeddings, tableau de bord, MCP seul** : banals (§1, §6).
- **Agents qui négocient librement** : biais documentés (§3) ; nous branchons les agents sur un mécanisme (PSI + règles).
- **Circuits d'entraide** : en réserve (données).
- **Jumeaux IA, stratégie de networking générée** : peu vérifiables, risque de confiance (Boardy).
- **Détection de besoins jamais exprimés par inférence** : c'est exactement ce qu'un membre ne veut pas qu'on devine ; les intentions scellées font l'inverse : **il** le dit, **à son agent**.
- **Badge swiyu** : fort ancrage suisse, accès aux environnements non vérifié.

## 12. Démonstration de 60 secondes et pitch d'une minute

**Démo (60 s)** : trois colonnes. À gauche, **Benoît**, 63 ans, seule menuiserie du Club, confie à son agent :
« céder mon atelier d'ici deux ans ». À droite, **une repreneuse** confie : « reprendre une entreprise du bois ou de la
construction en Valais ». Au centre, **« Ce que voit le Club »** : un défilement de points aléatoires, et un compteur
« intentions lisibles : 0 ». Le tour de rapprochement tourne : les deux agents s'allument « un membre compatible
existe ». Benoît accepte de dévoiler son secteur **si** l'autre le fait ; elle aussi ; puis les identités, en même
temps. (Prototype `/scelle` : 15 agents, 3 780 points relayés en ≈ 0,45 s ; parcours complet rejoué automatiquement en
3,6 s, bureau et mobile. Le passage au parcours d'introduction existant, puis aux disponibilités communes, est la
prochaine étape : il n'est pas encore branché.)

**Pitch (1 min)** : « Une PME suisse sur six cherche un successeur. Aucune ne l'écrira sur une plateforme : une rumeur
fait partir les employés. Et dans un club de cent dirigeants, une annonce anonyme ne l'est pas : chez nous, 26 membres
sur 34 sont seuls dans leur secteur. Nous avons donc construit l'inverse d'un réseau social : chaque membre confie
l'indicible à son agent ; les agents se comparent par cryptographie ; le Club relaie des nombres aléatoires et ne sait
rien. Quand deux intentions s'emboîtent, chacun décide de se dévoiler, en même temps que l'autre. Tout le reste,
le matching expliqué, la soirée optimisée, l'assistant IA, nous l'avons aussi ; mais ça, personne ne l'a. »

## Annexe : sources principales
- Commercial : b2match (innoloft.com/en-us/blog/b2b-matchmaking-software), Brella (brella.io/event-matchmaking),
  Grip (grip.events/products/pre-scheduled-meetings), Highbar (highbar.ai/products/networking-agent), Bebb (usebebb.com),
  2Connect (2connect.ai), Boardy (boardy.ai ; betakit.com, forbes.com 2025-01-20), Lunchclub (cnbc.com 2020-09-01 ;
  fortune.com 2025-11-11), The Swarm MCP (docs.theswarm.com/docs/integrations/mcp), CCI Valais (kodoa.ch/realisations/cci-valais ;
  alpict.ch, événement du 02.06.2026), BNI Connect (bniblog.co.nz).
- Open source : github.com/chrisroge/agent-rendezvous, github.com/tacitprotocol/tacit, github.com/a2aproject/A2A,
  github.com/OpenMined/PSI, github.com/openwallet-foundation-labs/sd-jwt-python, github.com/swiyu-admin-ch/swiyu-issuer,
  github.com/A2CN-protocol/A2CN, github.com/agntcy/dir, github.com/projnanda/nanda-town-2.
- Académique : doi 10.1126/science.abl4476 ; 10.1002/smj.3256 ; arXiv 2112.08468 ; doi 10.1073/pnas.2404590122 ;
  arXiv 2409.00720 ; QJE 119(2):457 (Kidney Exchange) ; arXiv 2606.03030 ; arXiv 2510.25779 ; IACR ePrint 2011/026.
- International : websummit.com/blog/startups-investors ; een.ec.europa.eu (rapport d'impact 2022-2025) ;
  jgoodtech.smrj.go.jp ; startupnationcentral.org ; ycombinator.com/blog/what-do-people-want-in-a-co-founder ;
  crossiety.ch ; foireduvalais.ch/fr/le-club-foire-du-valais-1604.

## 13. Prochaines étapes (dans l'ordre)
0. **Fédération** : démontrer deux clubs (deux relais, aucune donnée partagée) qui trouvent une compatibilité commune.
1. **Tester l'hypothèse de valeur avec 5 vrais dirigeants** : « Confieriez-vous cette intention à un agent qui ne la
   montre à personne ? » Si la réponse est non, le concept meurt, quelle que soit sa qualité technique.
2. Brancher la compatibilité révélée sur le parcours existant (mise en relation, disponibilités communes, suivi).
3. Faire tourner chaque agent **chez le membre** (navigateur : OpenMined/PSI existe en WASM) ; le serveur ne garde que le relais.
4. Transport agent ↔ agent en tâches A2A (extension déclarée par URI), cartes d'agent signées par le Club.
5. Outil MCP côté membre : l'assistant IA aide à **formuler** l'intention, localement, sans la transmettre.
6. Évaluer le sondage par faux acheteur sur un Club simulé (plafond de jetons, fréquence de changement d'intentions).

# Démonstration et pitch (répétition générale, lot 4)

Règle d'or : **on ne montre que ce qui fonctionne, et on dit ce qui est simulé.** Personnes et entreprises fictives ; le bandeau et les badges le disent en permanence.

## Préparation (3 minutes avant de monter)
1. `cd prototype && uvicorn app.main:app` (aucun réseau nécessaire). Ou l'image Docker (DEPLOIEMENT.md).
2. `python scripts/parcours_demo.py` : test de fumée complet (≈ 1 min). Il doit afficher « Scène OK », « Cas limites OK » ×2 et « Club, profil et présentation OK ».
3. Ouvrir **http://localhost:8000/club** et cliquer sur « Charger l'historique fictif » : 14 besoins fictifs de 6 semaines. **Ne plus réinitialiser ensuite** (le bouton Réinitialiser de la scène effacerait l'historique).
4. Onglet 1 : `/presentation` (← → pour avancer, N pour les notes, F pour le plein écran). Onglet 2 : `/scene`. Onglet 3 : `/scene?gauche=club&droite=p10&vue_d=profil`.
5. Garder les vidéos réelles `docs/captures/demo_scene.webm` (50 s) et `demo_club_repare.webm` (20 s) en secours.

## Le moment waouh, en deux actes (90 secondes au total)

### Acte 1 : un besoin devient une occasion d'aider (60 s, onglet `/scene`)
À gauche, **Sophie** (jus d'abricot, Saxon) ; à droite, **Julien** (transport frigorifique, Martigny). Une seule base de données.

| t | Écran | Phrase (P1 récit / P2 clavier) | Ce que le public voit |
|---|---|---|---|
| 0–10 s | Gauche : exemple « Transport frigorifique vers Zurich » | P1 : « Sophie lance ses jus en Suisse alémanique. Elle écrit son besoin comme elle le dirait. » | Une phrase naturelle |
| 10–20 s | « Analyser mon besoin » | P1 : « La phrase devient des critères. Les mots soulignés disent d'où vient chaque critère. » | Transport frigorifique (obligatoire), Suisse alémanique, allemand **souhaité** |
| 20–28 s | Défilement : « Qui peut vous aider » | P1 : « Deux membres, pas vingt. Chaque raison est une citation exacte. Six autres sont écartés, sans être nommés. » | Julien (forte), Élodie (partielle) |
| 28–35 s | « Publier dans la Bourse » | P1 : « Sophie publie. Regardez à droite. » | Point rouge sur le fil ; badge Bourse = 1 chez Julien |
| 35–50 s | Droite : la carte | P1 : « Pour Julien, le besoin de Sophie devient une occasion d'aider, et il voit pourquoi lui. » | « Sophie Moret cherche : transport frigorifique » ; pont besoin ↔ preuves |
| 50–60 s | Droite : « Proposer mon aide » ; gauche : « Accepter » | P1 : « Julien propose, Sophie choisit ; les coordonnées ne passent qu'après son accord. » | « Acceptée » des deux côtés |

### Acte 2 : quand personne ne peut aider, le Club se répare (30 s, onglet 3)
À gauche, la **vue du Club** ; à droite, **Yann** (Cyberalp), sur son profil.

| t | Écran | Phrase | Ce que le public voit |
|---|---|---|---|
| 0–8 s | Gauche | P1 : « Parfois, personne ne peut aider. Le produit le dit, et le Club le voit : trois membres ont cherché un accompagnement ISO 27001, aucun ne le propose. » | « Compétences à recruter : 3 · ISO 27001 » |
| 8–22 s | Droite : taper « Nous accompagnons les PME valaisannes vers la certification ISO 27001. » → « Proposer mon profil » → « Valider » | P1 : « Yann complète son profil en trente secondes, et c'est lui qui valide. » | Proposition d'offre avec la phrase en preuve |
| 22–30 s | Les deux panneaux | P1 : « Le manque est comblé, et la demande qui attendait trouve Yann. » | À gauche : **« Comblé : ISO 27001 »** ; à droite : notification « Alain a besoin de ce que vous faites » |

### Acte 3 : la prochaine soirée du Club (30 s, onglet `/soiree`)
| t | Écran | Phrase | Ce que le public voit |
|---|---|---|---|
| 0–10 s | « Club synthétique (150 membres) » → « Calculer le plan » | P1 : « Avant chaque soirée, qui doit rencontrer qui ? 150 membres, 3 tours. » | Tableau : optimisé **92** participants avec une rencontre utile, glouton 74, hasard 79 |
| 10–20 s | Tours et cartes | P1 : « Chaque rencontre cite l'aide prouvée ; jamais deux personnes sans langue commune. Optimum prouvé en quelques dizaines de millisecondes. » | Cartes « Anna peut aider David : « … » », langue FR/DE |
| 20–30 s | « Mon programme » → un membre → « Ajouter à mon agenda » | P1 : « Et chacun repart avec son programme dans son agenda. » | Fichier .ics téléchargé |

### Acte 4 : le même Club, piloté par un assistant IA (30 s)
Deux options, selon ce qui est disponible le jour J :
- **En direct** (si un membre de l'équipe a Claude Desktop ou Claude Code avec une clé) : brancher le serveur MCP
  (`claude mcp add fil-du-club -e HACKVS_API_URL=http://localhost:8000 -e HACKVS_MCP_MEMBRE=p00 -- python <chemin>/prototype/scripts/mcp_club.py`, voir HANDOFF.md) et demander : « Trouve-moi un
  transporteur frigorifique pour Zurich dans le Club et explique-moi pourquoi. » Montrer la **fenêtre de confirmation**
  avant toute publication.
- **Rejouée** (hors ligne, sans clé) : `docs/captures/agent_mcp.md`, transcription d'un agent **scripté** sur le vrai
  serveur MCP : abstention pour « comptabilité carbone », explication critère par critère, raison opaque pour Stefan,
  refus 403/409 du serveur, confirmation humaine à chaque action. Le dire : « agent scripté, serveur réel ».

Phrase : « Un assistant IA peut tout faire à la place du membre, sauf décider à sa place. »

**Phrase de conclusion** : « Un membre aide un membre ; et quand personne ne peut aider, le Club sait qui inviter. »

### Moments de preuve (15 s chacun, pour les questions)
- **Il sait dire non** : exemple « Aucune bonne réponse » (ISO 27001, sans historique). « Je préfère ne rien vous proposer plutôt qu'un mauvais contact. »
- **Il comprend la négation** : exemple « Négation ». Le frigoriste est écarté et barré.
- **Il ne triche pas** : retirer un critère grise les résultats (« Actualiser »).
- **Face à une recherche par mots-clés** : « Comparer avec une simple recherche par mots-clés ».
- **Il parle allemand** : « Wir brauchen einen Treuhänder für unsere Buchhaltung. » (règles locales).
- **Pourquoi cette personne ?** : déplier « Pourquoi cette personne ? Critère par critère » sur une carte (✓ vérifié, ? à vérifier, ✗ non satisfait).
- **Pourquoi pas lui ?** : « Pourquoi pas quelqu'un d'autre ? » → Stefan : « le détail n'est pas communiqué » (son choix est protégé).
- **L'IA locale propose, le membre confirme** : « Je voudrais rencontrer quelqu'un qui travaille dans les renouvelables » ou
  « Nos bouteilles ont besoin d'un nouvel habillage » → 1 à 3 compétences proposées, bouton « Aucune ».
- **Il ne se laisse pas piéger** : « Je cherche quelqu'un pour la comptabilité carbone » → personne (pas un fiduciaire).
- **Essayez vous-mêmes** : `/rejoindre` ou la dernière diapositive (QR ; nécessite une URL joignable, voir DEPLOIEMENT.md).

## Pitchs

Répartition : **P1 = récit**, **P2 = démo**. Chaque bloc tient seul si l'un des deux est absent (P1 peut cliquer, les étapes sont guidées).

### 1 minute
1. (P1, 15 s) « Le Club des Affaires réunit plus de 100 dirigeants, surtout lors de soirées. Entre deux soirées, un besoin ne rencontre pas celui qui pourrait y répondre. C'est notre hypothèse, et nous la testons ici. »
2. (P2, 35 s) Scène : phrase → critères → publication → le besoin apparaît chez Julien avec la raison → il propose son aide.
3. (P1, 10 s) « L'IA comprend la phrase, le code décide qui la voit, et chacun garde le dernier mot. »

### 3 minutes
- 0:00 (P1, 30 s) **Utilisateur et problème** : Sophie, fondatrice de PME, membre du Club. Constat public : le Club vit surtout lors d'événements. Hypothèse : les besoins entre deux événements ne trouvent pas leur réponse dans le Club. *(Citer uniquement les réponses réellement recueillies sur place : « X membres sur Y nous ont dit… »)*
- 0:30 (P2, 75 s) **Démo** : le scénario ci-dessus jusqu'à l'acceptation.
- 1:45 (P1, 30 s) **Pourquoi lui faire confiance** : citations exactes, abstention, exclusions anonymes, consentement, résultats rendus obsolètes quand le besoin change.
- 2:15 (P2, 30 s) **Preuve, avec ses limites** : « Sur des jeux écrits avant le code et testés une seule fois, le moteur propose très rarement un mauvais contact (0 à 2 par jeu de 14 à 20 cas), bien moins qu'une recherche par mots-clés ; mais seul, il se tait trop sur des formulations libres. Quand l'IA locale propose une compétence et que le membre confirme, il trouve 14 à 15 besoins sur 15, sans aucun mauvais contact de plus. Données fictives : ça prouve le mécanisme, pas encore l'utilité. »
- 2:15 (P2, 25 s) **Acte 2** : le Club se répare (voir plus haut). *(Si on manque de temps, remplacer la « Preuve » par l'acte 2.)*
- 2:45 (P1, 15 s) **Suite** : pilote de 30 jours avec 20 membres volontaires ; trois mesures (besoins publiés, part avec une proposition d'aide, rencontres jugées utiles).

### 5 minutes
Version 3 minutes, plus :
- (40 s) **Différence avec l'existant** : Brella et Swapcard font déjà du matching avec double consentement, **pendant un événement**. Hivebrite est un annuaire permanent. Nous faisons parvenir **un besoin** aux membres qui peuvent y répondre, entre les événements, et nous refusons de proposer sans preuve.
- (40 s) **Architecture** : analyse du besoin (règles ou Claude, en flux) → filtres durs dans le code → classement → preuves vérifiées → abstention. Même moteur dans les deux sens : c'est pour ça que les deux écrans sont cohérents.
- (40 s) **Soirée optimisée** (acte 3) et **assistant IA via MCP** (acte 4) : mêmes garde-fous, mêmes preuves.
- (20 s) **Ingénierie visible** : 51 tests, intégration continue, jeux réservés écrits avant le code, reconnaissance de 20 projets open source (ce qu'on a repris, ce qu'on a mesuré et rejeté).

## Support de présentation
`/presentation` : 11 diapositives, hors ligne, captures réelles, notes d'orateur (N) avec la répartition P1/P2, espaces « à compléter » en ambre
(noms de l'équipe, chiffres terrain). Captures des diapositives : `docs/captures/40_pitch_*.png`.

## Storyboard (captures réelles, `docs/captures/`)
10 départ · 11 critères · 12 aperçu · **13 Bourse de Julien (image clé)** · 14 proposition · 15 offre reçue · 16 résolu.
Cas limites : 21 abstention · 22 ambiguïté · 23 négation · 24 résultats obsolètes · 25 hors catalogue · 26 profil et consentement (versions `_mobile` incluses).
Acte 2 et Club : 30 vue du Club · 31 profil en 30 s · 32 manque comblé · 33 Bourse de Yann · 34 et 35 scène Club + Yann.
Vidéos : `demo_scene.webm` (50 s) et `demo_club_repare.webm` (20 s), parcours réels enregistrés par Playwright, rythme ralenti.

## Objections du jury

| Objection | Réponse (vérifiable) |
|---|---|
| « Vos données sont fausses. » | « Oui, et c'est affiché partout : nous n'avons aspiré aucun profil réel. Le mode réel existe et refuse de démarrer sans source autorisée (503), et n'accepte aucune identité simulée (501). » |
| « Brella fait déjà ça. » | « Brella fait du matching avec double consentement pendant un événement. Nous faisons parvenir un besoin aux bons membres entre les événements, avec preuve et abstention. Le double consentement n'est pas notre argument. » |
| « Où est l'IA ? » | Trois places, chacune bornée : (1) **IA locale** (modèle multilingue e5, sur la machine, sans réseau) qui propose des compétences quand les règles ne comprennent pas — badge « règles + IA locale » ; (2) **LLM** (Claude ou Apertus, l'IA suisse) pour analyser des phrases riches, **seulement si une clé est configurée** — badge « Analyse : Claude / Apertus » ; (3) **optimisation** du plan de soirée. **Ne jamais dire qu'un LLM tourne si le badge dit « règles ».** |
| « Pourquoi pas un agent LLM qui fait tout ? » | « Parce qu'on a mesuré que la similarité sémantique ne sait pas dire "je ne sais pas". L'IA suggère, le code vérifie consentement, zone, langue, preuves ; le membre décide. Un agent externe peut tout piloter via MCP, sauf décider à sa place. » |
| « Ça passe à l'échelle ? » | Plan de soirée : 150 membres, optimum prouvé en < 0,1 s (calcul des aides ≈ 1,2 s). Recherche : parcours exact en ≈ 10 ms pour 37 profils ; au-delà de quelques milliers, un index s'imposerait (voir OPEN_SOURCE_RECON.md). |
| « Et si un membre écrit des consignes pour manipuler l'IA dans son profil ? » | « Le LLM ne voit jamais les profils ; un profil qui contient des consignes est signalé, ne change pas le classement, et rien ne part sans le membre. C'est testé. » |
| « Et si l'IA se trompe ? » | Vocabulaire fermé, extraits vérifiés, critères provisoires sans effet, repli affiché. Elle ne voit pas les profils et ne décide pas qui est proposé. |
| « Pourquoi pas un annuaire avec filtres ? » | Montrer la comparaison ; chiffres des jeux réservés (EVALUATION.md §2). |
| « Votre moteur rate des choses. » | « Oui : seul, il se tait trop sur des formulations libres (3/15 sur notre jeu le plus dur). C'est pourquoi l'IA locale propose des compétences à confirmer : 15/15 dans ce cas, si le membre reconnaît la bonne. Et il reste des faux amis qu'on connaît et qu'on liste. » |
| « Les membres rempliront-ils leur profil ? » | « C'est notre premier risque. D'où le profil en 30 secondes : on décrit son entreprise, on valide. Et la Bourse motive : on voit qui on peut aider. » (Montrer l'acte 2.) |
| « Qu'est-ce que le Club y gagne ? » | « Une information qu'il n'a pas aujourd'hui : les compétences que ses membres cherchent sans les trouver, donc les entreprises à inviter. Et des chiffres sur ce que produit la communauté. » |
| « Vos chiffres du Club sont inventés. » | « L'historique est fictif et étiqueté comme tel ; les indicateurs, eux, sont calculés en direct par le code, comme vous venez de le voir changer. » |
| « Confidentialité, LPD ? » | Consentement révocable (cascade testée), anonymat facultatif, coordonnées partagées après acceptation, exclusions anonymes, aucune donnée réelle. (Pas d'avis juridique.) |
| « Qu'avez-vous préparé avant ? » | Répondre selon le règlement (HANDOFF.md, Règles). Ne jamais présenter la préparation comme faite pendant les 24 h. |
| « Combien ça coûte ? » | Règles : zéro. Claude : ≈ 0,56 USD estimés pour 40 analyses avec `claude-opus-5` (estimation, non mesurée). |

## Plan de secours sans réseau
1. Tout fonctionne en local en mode règles : le badge affiche « Analyse : règles locales ». La dictée vocale, elle, dépend du réseau : ne pas l'utiliser en secours.
2. Si le navigateur ou la machine tombe : lire `demo_scene.webm`, puis dérouler les captures 10 à 16 (« enregistrements du vrai produit »).
3. Si Claude est lent ou coupé : le repli sur les règles est automatique et affiché. Le dire.
4. Si la scène est trop petite pour le projecteur : ouvrir deux onglets, `/?membre=p00` et `/?membre=p01`, et alterner.

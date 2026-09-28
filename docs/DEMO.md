# Démonstration et pitch (répétition générale, lot 2)

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

**Phrase de conclusion** : « Un membre aide un membre ; et quand personne ne peut aider, le Club sait qui inviter. »

### Moments de preuve (15 s chacun, pour les questions)
- **Il sait dire non** : exemple « Aucune bonne réponse » (ISO 27001, sans historique). « Je préfère ne rien vous proposer plutôt qu'un mauvais contact. »
- **Il comprend la négation** : exemple « Négation ». Le frigoriste est écarté et barré.
- **Il ne triche pas** : retirer un critère grise les résultats (« Actualiser »).
- **Face à une recherche par mots-clés** : « Comparer avec une simple recherche par mots-clés ».
- **Il parle allemand** : « Wir brauchen einen Treuhänder für unsere Buchhaltung. » (règles locales).
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
- 2:15 (P2, 30 s) **Preuve, avec ses limites** : « Sur 14 cas écrits après nos corrections et testés une seule fois, le moteur n'a jamais proposé un mauvais contact, contre 4 fois pour une recherche par mots-clés avec les mêmes filtres. En revanche, il s'est abstenu à tort 3 fois : c'est là que l'IA générative doit aider. Données fictives : ça prouve le mécanisme, pas encore l'utilité. »
- 2:15 (P2, 25 s) **Acte 2** : le Club se répare (voir plus haut). *(Si on manque de temps, remplacer la « Preuve » par l'acte 2.)*
- 2:45 (P1, 15 s) **Suite** : pilote de 30 jours avec 20 membres volontaires ; trois mesures (besoins publiés, part avec une proposition d'aide, rencontres jugées utiles).

### 5 minutes
Version 3 minutes, plus :
- (40 s) **Différence avec l'existant** : Brella et Swapcard font déjà du matching avec double consentement, **pendant un événement**. Hivebrite est un annuaire permanent. Nous faisons parvenir **un besoin** aux membres qui peuvent y répondre, entre les événements, et nous refusons de proposer sans preuve.
- (40 s) **Architecture** : analyse du besoin (règles ou Claude, en flux) → filtres durs dans le code → classement → preuves vérifiées → abstention. Même moteur dans les deux sens : c'est pour ça que les deux écrans sont cohérents.
- (40 s) **Vision** : compagnon de soirée (3 personnes à rencontrer), accès depuis l'assistant IA de chaque membre (serveur MCP), mêmes garde-fous.

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
| « Où est l'IA ? » | Selon le badge : « Analyse : Claude », qui transforme la phrase en critères, validés par le code ; ou « Analyse : règles locales » : « Ici, hors ligne, ce sont des règles. L'intégration Claude est prête et testée avec un client simulé, pas encore contre l'API réelle. » **Ne jamais dire que Claude tourne si le badge dit « règles ».** |
| « Et si l'IA se trompe ? » | Vocabulaire fermé, extraits vérifiés, critères provisoires sans effet, repli affiché. Elle ne voit pas les profils et ne décide pas qui est proposé. |
| « Pourquoi pas un annuaire avec filtres ? » | Montrer la comparaison ; chiffres du jeu réservé (0 violation sur 14 contre 4 sur 14). |
| « Votre moteur rate des choses. » | « Oui : 3 fausses abstentions sur 14 cas nouveaux. Nous préférons qu'il se taise plutôt qu'il se trompe. La couverture est le chantier du LLM. » |
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

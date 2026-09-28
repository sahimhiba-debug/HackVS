# Démonstration et pitch (répétition générale, lot 2)

Règle d'or : **on ne montre que ce qui fonctionne, et on dit ce qui est simulé.** Personnes et entreprises fictives ; le bandeau et les badges le disent en permanence.

## Préparation (2 minutes avant de monter)
1. `cd prototype && uvicorn app.main:app` (aucun réseau nécessaire).
2. `python scripts/parcours_demo.py` : test de fumée complet (≈ 40 s). Il doit afficher « Scène OK » puis « Cas limites OK ».
3. Ouvrir **http://localhost:8000/scene** en plein écran, zoom du navigateur à 100 % sur un écran de 1600 px (110 % à 1920 px).
4. Cliquer sur « Réinitialiser » dans la barre de la scène.
5. Garder sous la main `docs/captures/demo_scene.webm` (vidéo réelle de 50 s) et les captures.

## Le moment waouh : scénario de 60 à 90 secondes (vue scène)

À gauche, **Sophie** (jus d'abricot, Saxon) ; à droite, **Julien** (transport frigorifique, Martigny). Une seule base de données.

| t | Écran | Phrase (P1 récit / P2 clavier) | Ce que le public voit |
|---|---|---|---|
| 0–10 s | Gauche : clic sur « Transport frigorifique vers Zurich » | P1 : « Sophie lance ses jus en Suisse alémanique. Elle écrit son besoin comme elle le dirait. » | Une phrase naturelle, en grand |
| 10–20 s | « Analyser mon besoin » | P1 : « La phrase devient des critères. Chaque mot souligné dit d'où vient le critère. » | Soulignements ; Transport frigorifique (obligatoire) ; Suisse alémanique ; allemand **souhaité** (« idéalement ») ; « deux fois par semaine : noté, non vérifiable » |
| 20–30 s | Défilement vers « Qui peut vous aider » | P1 : « Deux membres, pas vingt. Chaque raison est une citation exacte de leur profil. Six autres sont écartés (concurrent, refus des introductions, profil incomplet…), sans être nommés. » | Julien (forte), Élodie (partielle, « à vérifier ») |
| 30–40 s | « Publier dans la Bourse » | P1 : « Sophie publie. Regardez à droite. » | Point rouge qui traverse le fil ; **à droite**, badge Bourse = 1 ; notification |
| 40–55 s | Droite : la carte Bourse | P1 : « Pour Julien, le besoin de Sophie devient une occasion d'aider, et il voit pourquoi lui : son offre déclarée répond au besoin. » | « Sophie Moret cherche : transport frigorifique » ; pont **Son besoin ↔ Pourquoi vous**, fil tracé |
| 55–65 s | Droite : « Proposer mon aide » → envoyer | P1 : « Julien propose. Sophie choisit. » | Message pré-rédigé à partir des preuves |
| 65–75 s | Gauche : « Accepter et partager nos coordonnées » | P1 : « Les coordonnées ne sont partagées qu'après son accord. » | À droite : « acceptée » ; fil : Acceptée |
| 75–90 s | (optionnel) Droite : Suivi → planifier ; gauche : « Résolu grâce à Julien » | P1 : « Et le Club sait ce que la mise en relation a produit. » | Frise ; besoin « Résolu » |

**Si le temps manque**, s'arrêter à 55 s (carte Bourse) : c'est le cœur de la démonstration.

### Moments de preuve (15 s chacun, pour les questions)
- **Il sait dire non** : exemple « Aucune bonne réponse » (ISO 27001). Réponse : « Je préfère ne rien vous proposer plutôt qu'un mauvais contact. » La piste plus large est étiquetée « non vérifiée ».
- **Il comprend la négation** : exemple « Négation ». Le frigoriste est écarté, et barré dans le texte.
- **Il ne triche pas après modification** : retirer un critère grise les résultats (« Critères modifiés… Actualiser »).
- **Face à une recherche par mots-clés** : déplier « Comparer avec une simple recherche par mots-clés ».

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
- 2:45 (P1, 15 s) **Suite** : pilote avec 20 membres volontaires, profils de 3 lignes, mesure du taux de mises en relation utiles.

### 5 minutes
Version 3 minutes, plus :
- (40 s) **Différence avec l'existant** : Brella et Swapcard font déjà du matching avec double consentement, **pendant un événement**. Hivebrite est un annuaire permanent. Nous faisons parvenir **un besoin** aux membres qui peuvent y répondre, entre les événements, et nous refusons de proposer sans preuve.
- (40 s) **Architecture** : analyse du besoin (règles ou Claude, en flux) → filtres durs dans le code → classement → preuves vérifiées → abstention. Même moteur dans les deux sens : c'est pour ça que les deux écrans sont cohérents.
- (40 s) **Vision** : compagnon de soirée (3 personnes à rencontrer), accès depuis l'assistant IA de chaque membre (serveur MCP), mêmes garde-fous.

## Storyboard (captures réelles, `docs/captures/`)
10 départ · 11 critères · 12 aperçu · **13 Bourse de Julien (image clé)** · 14 proposition · 15 offre reçue · 16 résolu.
Cas limites : 21 abstention · 22 ambiguïté · 23 négation · 24 résultats obsolètes · 25 hors catalogue · 26 profil et consentement (versions `_mobile` incluses).
Vidéo : `demo_scene.webm` (50 s, parcours réel enregistré par Playwright, rythme ralenti pour la lecture).

## Objections du jury

| Objection | Réponse (vérifiable) |
|---|---|
| « Vos données sont fausses. » | « Oui, et c'est affiché partout : nous n'avons aspiré aucun profil réel. Le mode réel existe et refuse de démarrer sans source autorisée (503), et n'accepte aucune identité simulée (501). » |
| « Brella fait déjà ça. » | « Brella fait du matching avec double consentement pendant un événement. Nous faisons parvenir un besoin aux bons membres entre les événements, avec preuve et abstention. Le double consentement n'est pas notre argument. » |
| « Où est l'IA ? » | Selon le badge : « Analyse : Claude », qui transforme la phrase en critères, validés par le code ; ou « Analyse : règles locales » : « Ici, hors ligne, ce sont des règles. L'intégration Claude est prête et testée avec un client simulé, pas encore contre l'API réelle. » **Ne jamais dire que Claude tourne si le badge dit « règles ».** |
| « Et si l'IA se trompe ? » | Vocabulaire fermé, extraits vérifiés, critères provisoires sans effet, repli affiché. Elle ne voit pas les profils et ne décide pas qui est proposé. |
| « Pourquoi pas un annuaire avec filtres ? » | Montrer la comparaison ; chiffres du jeu réservé (0 violation sur 14 contre 4 sur 14). |
| « Votre moteur rate des choses. » | « Oui : 3 fausses abstentions sur 14 cas nouveaux. Nous préférons qu'il se taise plutôt qu'il se trompe. La couverture est le chantier du LLM. » |
| « Les membres rempliront-ils leur profil ? » | « Inconnu : c'est notre premier risque. Pilote : 3 lignes, et la Bourse comme motivation (on voit ceux qu'on peut aider). » |
| « Confidentialité, LPD ? » | Consentement révocable (cascade testée), anonymat facultatif, coordonnées partagées après acceptation, exclusions anonymes, aucune donnée réelle. (Pas d'avis juridique.) |
| « Qu'avez-vous préparé avant ? » | Répondre selon le règlement (HANDOFF.md, Règles). Ne jamais présenter la préparation comme faite pendant les 24 h. |
| « Combien ça coûte ? » | Règles : zéro. Claude : ≈ 0,56 USD estimés pour 40 analyses avec `claude-opus-5` (estimation, non mesurée). |

## Plan de secours sans réseau
1. Tout fonctionne en local en mode règles : le badge affiche « Analyse : règles locales ». La dictée vocale, elle, dépend du réseau : ne pas l'utiliser en secours.
2. Si le navigateur ou la machine tombe : lire `demo_scene.webm`, puis dérouler les captures 10 à 16 (« enregistrements du vrai produit »).
3. Si Claude est lent ou coupé : le repli sur les règles est automatique et affiché. Le dire.
4. Si la scène est trop petite pour le projecteur : ouvrir deux onglets, `/?membre=p00` et `/?membre=p01`, et alterner.

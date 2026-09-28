# Démonstration et pitch

Règle d'or : **on ne montre que ce qui fonctionne.** Les données sont fictives : on le dit dans la première phrase,
et l'interface l'affiche en permanence.

## Le moment waouh : scénario de 60 secondes

Personnage **fictif** : Sophie Moret, fondatrice des Vergers du Rhône (jus d'abricot, Saxon).
Préparation : page ouverte, démo réinitialisée (lien en bas de page), zoom navigateur à 110 % sur projecteur.

| t | Action à l'écran | Phrase (courte) | Ce que le public voit |
|---|---|---|---|
| 0–8 s | Clic sur l'exemple « Transport frigorifique vers Zurich » (ou dictée au micro) | « Sophie lance ses jus en Suisse alémanique. Elle a besoin d'un transporteur. Elle l'écrit comme elle le dirait. » | Une phrase naturelle, en grand |
| 8–18 s | « Analyser mon besoin » | « Le produit transforme la phrase en critères, et souligne les mots d'où ils viennent. » | Mots soulignés en rouge ; 3 cartes : **Transport frigorifique** (obligatoire), **Suisse alémanique**, **allemand (souhaité)** ; « deux fois par semaine : noté, mais non vérifiable » |
| 18–22 s | Clic sur « Souhaité » ou « Obligatoire » (facultatif) | « Tout est modifiable. » | Le critère change d'état |
| 22–35 s | « Trouver des contacts » | « Deux membres, pas vingt. Chaque raison est une citation du profil. » | Julien Morand (forte) : « Transport frigorifique 2–8 °C, tournées Valais–Zurich… » ; Élodie Rithner (partielle, déduite de la présentation, à vérifier) |
| 35–42 s | Déplier « 6 profils écartés » | « Six autres étaient pertinents mais écartés : un concurrent, une personne qui ne veut pas être sollicitée, un profil incomplet… sans les nommer. » | Les raisons, sans noms |
| 42–52 s | « Demander une introduction » → « Envoyer (simulation) » | « Julien reçoit une demande. C'est lui qui choisit. Ses coordonnées ne sont partagées qu'après son accord. » | Message pré-rédigé à partir des preuves ; bloc consentement |
| 52–60 s | « Simuler : Julien accepte » → date → « Planifier » | « Et le Club voit si la mise en relation a servi. » | Frise : Demandée → Acceptée → Rencontre planifiée |

### Cas « pas de bonne réponse » (15 s, à enchaîner si le temps le permet)
Exemple « Certification ISO 27001 » → « Je préfère ne rien vous proposer plutôt qu'un mauvais contact. »
Montrer ensuite la piste plus large, étiquetée « non vérifiée ». **Phrase : « Un système qui sait dire non, on peut lui faire confiance quand il dit oui. »**

### Preuve comparative (15 s, pour une question du jury)
Déplier « Comparer avec une simple recherche par mots-clés » : la recherche par mots-clés classe **Froidtech**
(un frigoriste dont le profil dit « nous ne livrons pas ») et un agent commercial parmi les 3 premiers.

## Pitch modulable

Répartition possible entre deux personnes : **P1 = récit / P2 = démo**. Chaque bloc est jouable seul si l'un des deux est absent.

### 1 minute
1. (P1) « Le Club des Affaires réunit plus de 100 dirigeants, surtout lors d'événements. Entre deux soirées, quand un membre a un besoin précis, le réseau reste silencieux. C'est notre hypothèse, et nous la vérifions sur place. »
2. (P2) Démo en accéléré : phrase → critères → 2 contacts justifiés → introduction.
3. (P1) « L'IA comprend la phrase, le code décide qui est proposé, et la personne sollicitée garde le dernier mot. »

### 3 minutes
- 0:00 Problème (P1, 30 s) : le Club est fort en présentiel et discret entre les rencontres (constat public). Le besoin de solliciter le réseau entre deux événements est une hypothèse, testée auprès de N personnes sur place (**ne citer que des chiffres réellement recueillis**).
- 0:30 Démo 60 s (P2).
- 1:30 Pourquoi on peut lui faire confiance (P1, 45 s) : raisons citées, abstention, consentement, exclusions sans nom.
- 2:15 Preuve (P2, 25 s) : évaluation exploratoire sur 20 cas fictifs. Aucune violation de contrainte dans le top 3, contre 9 cas sur 20 pour une recherche par mots-clés avec les mêmes filtres. « Sur des données fictives, écrites par nous : ça montre que le mécanisme fonctionne, pas encore qu'il est utile. »
- 2:40 Suite (P1, 20 s) : pilote avec 20 membres volontaires, puis la Bourse des besoins.

### 5 minutes
Version 3 minutes, plus :
- **Différence avec l'existant** (40 s) : Brella et Swapcard vivent le temps d'un événement ; Hivebrite est un annuaire qu'il faut interroger soi-même ; BNI impose une réunion hebdomadaire. Nous : déclenché par un besoin, entre les événements, avec consentement et suivi.
- **Vision** (40 s) : la Bourse des besoins (le même moteur en sens inverse), le compagnon de soirée (3 personnes à rencontrer), et le Club accessible depuis l'assistant IA de chaque membre (MCP), avec les mêmes garde-fous.
- **Architecture** (40 s) : schéma en 4 étapes (analyse, filtres, classement, preuves vérifiées).

## Storyboard (6 images, à partir des vraies captures)
`docs/captures/` : 01 accueil · 02 critères · 03 contacts · 04 comparaison · 05 introduction · 06 suivi · 07 abstention · 08 ambiguïté.
Captures réelles du prototype (Playwright), versions bureau et mobile.

## Questions difficiles du jury

| Question | Réponse courte (honnête) |
|---|---|
| « Vos données sont fausses. » | « Oui, et c'est affiché partout. Nous n'avons pas voulu aspirer de profils réels sans consentement. Le mode réel existe et refuse de fonctionner sans source autorisée. » |
| « Qu'apporte l'IA, concrètement ? » | « Elle transforme une phrase libre en critères. Elle ne choisit pas qui est proposé : c'est le code, avec des règles visibles. » (Si Claude n'est pas branché : « En démo hors ligne, ce sont des règles locales. Le badge l'indique. ») |
| « Et si l'IA se trompe ? » | « Tout ce qu'elle produit est validé : vocabulaire fermé, extraits vérifiés, panne → repli affiché. L'utilisateur voit et corrige les critères. » |
| « Pourquoi pas un simple annuaire avec filtres ? » | Montrer la comparaison : mêmes filtres, les mots-clés remontent un frigoriste qui ne livre pas. |
| « Les membres vont-ils remplir leur profil ? » | « Inconnu. C'est notre premier risque. Pilote : 3 lignes par membre, et la réciprocité comme motivation. » |
| « RGPD / LPD ? » | Consentement explicite pour être proposé, coordonnées partagées après acceptation, exclusions anonymes, aucune donnée réelle dans la démo. (Pas d'avis juridique formel.) |
| « Qu'avez-vous fait avant l'événement ? » | Répondre selon le règlement (docs/HANDOFF.md, section Règles). Ne jamais présenter la préparation comme faite pendant les 24 h. |
| « Combien ça coûte ? » | Analyse par règles : coût nul. Avec Claude : un appel par besoin, coût et latence **non encore mesurés** (mesure prévue avec `eval --claude`). |

## Plan de secours sans réseau
1. Tout tourne en local : `uvicorn` + navigateur. Aucune dépendance réseau en mode règles (badge « Analyse : règles locales »).
2. Si l'ordinateur tombe : dérouler les captures `docs/captures/` dans l'ordre (le dire : « captures du vrai produit »).
3. Si Claude est lent ou indisponible : le repli sur les règles est automatique et affiché. Le dire, ne pas le cacher.
4. Avant de monter sur scène : `python scripts/parcours_demo.py` (test de fumée, 20 s), puis « Réinitialiser la démo ».

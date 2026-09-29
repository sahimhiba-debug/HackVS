# Club Pulse — thèse produit

> **Le Club ne se contente plus de connaître ses membres. Il apprend ce que son réseau peut accomplir.**

Données : toutes FICTIVES (monde de démonstration de 150 membres, graine fixe). Aucun membre réel, aucun résultat réel
mesuré. Ce document décrit une thèse et ce que le prototype en démontre ; il n'affirme aucun impact.

## Le problème
Une rencontre professionnelle dure quelques minutes ; sa valeur potentielle peut durer des mois. Aujourd'hui :

    RENCONTRE → carte / contact → oubli

La Foire du Valais crée des milliers de moments ; ce qui se passe *après* le moment n'appartient à personne. Le Club des
Affaires possède déjà la communauté, les adhésions et les événements : ce qui lui manque est une couche qui fait vivre
ce réseau **entre** les événements.

## L'intuition
La valeur d'un réseau n'est pas dans le nombre de contacts, mais dans les collaborations qu'il sait déclencher au bon
moment. Cette capacité existe déjà dans le Club — dispersée dans des profils, des besoins non dits, des rencontres
oubliées. Elle est invisible pour chaque membre.

## La catégorie
Club Pulse n'est ni un réseau social, ni un annuaire, ni un moteur de recommandation, ni un CRM. C'est **la couche
numérique d'intelligence et d'activation d'une communauté professionnelle existante** :

    RENCONTRE → CONTEXTE → MÉMOIRE → OPPORTUNITÉ → ACTIVATION → COLLABORATION → RÉSULTAT → MÉMOIRE DU RÉSEAU → opportunité suivante

Le matching, le graphe, l'analyse du langage et la mémoire sont des composants internes. Le produit visible est
l'**activation** : ce que le réseau peut faire maintenant, pourquoi, avec qui, sous quel consentement — et ce qui s'est
réellement passé ensuite.

## L'unité de valeur : la demande débloquée
Une demande est **débloquée** quand une contribution a été reçue **et** que la personne aidée confirme qu'elle a permis
la prochaine étape qu'elle visait. Ni un clic, ni un « match », ni une introduction envoyée : un effet déclaré par le
bénéficiaire, que le système ne peut pas fabriquer (sans confirmation au bout de 21 jours : « résultat inconnu »).

Mesures associées (cadre, pas résultats) : demandes débloquées · activations vérifiées (activation → contribution →
effet confirmé) · réutilisation de la mémoire · taux de refus et de replanification · charge par membre (sollicitations
ouvertes, plafonnées à 2).

## Ce qui rend l'activation possible sans trahir les membres
- **Identité ≠ capacité** : le moteur raisonne sur « MEMBRE-042 · traduction français–allemand », jamais sur un nom.
- **Consentement d'abord** : le bénéficiaire accepte avant que quiconque soit sollicité ; chaque sollicité ne voit que
  sa part, sans savoir qui demande ; son nom n'est révélé qu'après son accord ; un refus n'est attribué à personne —
  pas même au Club.
- **Trois mémoires séparées** : notes privées (propriétaire seul) · contexte partagé (ce que le membre a choisi de
  publier) · mémoire vérifiée (résultats confirmés, anonymisés).
- **L'IA propose, le code décide** : Apertus (quand il est configuré) comprend et rédige ; les permissions, la
  visibilité, les états et les preuves restent déterministes.

## Pourquoi un animateur compétent ne suffit pas (et quand il suffit)
Un bon animateur connaît quelques dizaines de membres, expose la demande à chaque personne qu'il appelle, sollicite
toujours les mêmes, ne sait pas si l'aide a servi, et sa mémoire part avec lui. Club Pulse ne remplace pas l'animatrice :
il lui montre ce qu'il faut activer maintenant (tour de contrôle), fait le travail de coordination sous consentement, et
garde la trace de ce qui a vraiment aidé. Dans un club minuscule aux demandes rares, un formulaire et un animateur
suffisent — nous le disons.

## Ce que le prototype démontre (et ne démontre pas)
Démontré dans le code, sur données fictives : détection d'opportunités non demandées avec preuves ; plan d'activation ;
refus → replanification réelle ; consentement et révélation minimale ; résultat confirmé ; motif vérifié réutilisé ;
confidentialité testée. Non démontré : valeur pour de vrais membres, adoption, qualité d'Apertus sur ces tâches (aucune
clé disponible dans l'environnement de développement — voir `APERTUS.md`). Voir `CLAIMS_LEDGER.md`.

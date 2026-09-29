# Valeur métier — réponses concrètes (sans retour utilisateur inventé)

Statut : **aucun membre ni organisateur du Club n'a été interrogé.** Tout ce qui suit est une hypothèse de produit
(INFERRED) ou un fait du prototype (REAL, sur données fictives). Le brief exact du challenge n'est pas encore connu
(docs/ASSUMPTIONS.md, I1) : ces réponses seront confrontées à lui le 3 octobre.

## 1. Pourquoi le Club l'utiliserait-il entre deux événements ?
Parce que c'est entre deux événements que les rencontres meurent. Le prototype transforme ce temps mort en trois
moments précis, et seulement s'ils sont fondés :
- **un membre publie un besoin** → il reçoit des personnes du Club dont le profil prouve qu'elles peuvent aider, ou
  une abstention franche (scène A) ;
- **une raison nouvelle apparaît** (un besoin publié auquel un contact rencontré peut répondre) → une relance, avec la
  preuve ; sinon, rien (scène C : 1 relance, 17 silences) ;
- **chaque mois, l'organisatrice** voit ce qui se défait et choisit une ou deux introductions (scène B).
Hypothèse non vérifiée : que ces moments soient assez fréquents pour justifier une visite mensuelle. À mesurer (§ 6).

## 2. Quelle action NOUVELLE l'organisatrice peut-elle accomplir ?
Aujourd'hui (hypothèse sur la pratique) : elle sait qui est venu à quel événement, et présente des gens de mémoire.
Avec le prototype, elle peut :
1. voir que deux parties du Club ne tiennent qu'à une relation (« pont fragile ») et **qui** serait coupé si elle
   s'éteignait (scène B, contrefactuel) ;
2. choisir, pour un budget d'une introduction, entre « réunir les îlots » et « consolider », **en connaissant le prix
   de chacun** (8 → 15 membres reliés, mais seulement 4 qui résistent à une perte ; ou 4 → 8 qui résistent, sans rien
   réunir) — chiffres de la scène fictive ;
3. apprendre, après coup, ce que ses décisions ont réellement produit (boucle prévu / réalisé ; aucune décision réelle
   à ce jour).
Rien de cela n'existe dans un annuaire ; nous n'avons pas trouvé ces trois gestes dans la documentation publique des
plateformes comparées (AUDIT_CHAMPIONNAT § 7, avec ses limites).

## 3. Quel travail humain évite-t-elle ?
| Travail | Aujourd'hui (hypothèse) | Avec le prototype | Mesuré ? |
|---|---|---|---|
| Trouver « qui peut aider X » | mémoire de l'organisatrice, carnet d'adresses | recherche avec preuves citées, en millisecondes | vitesse : oui (fictif) ; qualité réelle : non |
| Demander l'accord des deux avant de présenter | courriels ou appels | workflow en double accord, coordonnées partagées après | non (aucun envoi réel) |
| Décider qui relancer | rien, ou relance générale « restez en contact » | seulement les paires avec raison nouvelle | non |
| Repérer ce qui se défait dans le réseau | impossible à l'œil au-delà de quelques dizaines de membres | diagnostic : 0,67 s à 150 membres générés, mais 5,8 s à 500 et 25 s à 1000 (limite connue) | vitesse : oui (synthétique) |
Nous ne chiffrons PAS d'heures économisées : aucune mesure de la pratique actuelle n'existe.

## 4. Pourquoi un annuaire, un CRM ou une plateforme de mise en relation ne suffit pas ?
- **Annuaire** : il dit qui existe, pas qui peut aider qui, ni quand. Et selon le brief connu, l'annuaire du Club ne
  publie pas les contacts : il faut un tiers de confiance pour présenter.
- **CRM** : il suit les relations d'UNE organisation avec ses clients, pas les relations des membres ENTRE EUX, et ne
  gère pas le consentement de deux tiers à être présentés.
- **Plateforme de mise en relation (Swapcard, Grip, Brella)** : excellente pendant l'événement. Notre différence
  défendable n'est pas la recommandation, mais ce qui suit : preuve, abstention, silence, consentement, et les plans de
  l'organisatrice avec leur prix. Si le Club utilise déjà l'une d'elles, notre moteur peut s'y ajouter comme couche de
  suivi (frontière MCP) — **hypothèse d'intégration non testée**.
- Honnêtement : pour un Club de 30 membres qui se connaissent tous, un bon organisateur suffit. La valeur supposée
  croît avec la taille et le renouvellement du Club : à vérifier sur le nombre réel de membres.

## 5. Comment obtenir des données pertinentes sans surcharger les membres ?
Principe : **aucune saisie longue, aucun formulaire de 20 champs.**
| Donnée | Source | Effort du membre | Dans le prototype ? |
|---|---|---|---|
| Profil (offre, recherche) | description libre d'une phrase → proposition, le membre valide | ~1 minute | Oui (`extraire_profil`, validé par le membre) |
| Présence aux événements | liste d'inscription du Club | aucun | Oui (import de faits `RENCONTRE`, fictifs) |
| Besoin du moment | une phrase libre | ~30 s | Oui ; phrase complexe : exige l'IA (scène A) |
| Suite d'une introduction | un clic (« rencontré », « sans suite ») | ~5 s | Oui |
| Consentement | un interrupteur, invisible par défaut | ~5 s | Oui |
Ce que nous ne ferons pas : lire les courriels, scraper LinkedIn, deviner des relations. Risque connu : si les membres
ne publient pas de besoins, le système se tait presque toujours (c'est honnête, mais sans valeur). Le pilote doit
mesurer ce taux de publication en premier.

## 6. Comment mesurer la valeur réelle après un pilote ?
Protocole proposé (à pré-enregistrer avant le pilote, sur le modèle de GENAI_RESEARCH.md) :
- **Durée** : 3 mois entre deux événements du Club ; organisatrice et membres volontaires.
- **Référence** : les 3 mois précédents (relations déclarées a posteriori), et les membres non volontaires.
- **Échelle d'impact** (déjà codée, `adaptateurs/club/impact.py`) : contact → relation → activation → persistance →
  effet de réseau. Chaque niveau compté sur des FAITS enregistrés, jamais sur des simulations.
- **Indicateurs principaux** : part des membres avec au moins une relation actuelle ; introductions acceptées / demandées ;
  rencontres confirmées ; relances acceptées / ignorées (une relance ignorée est un échec du système) ; plans de
  l'organisatrice réalisés / décidés (boucle prévu / réalisé).
- **Indicateurs de coût** : minutes de l'organisatrice par mois ; sollicitations par membre (budget d'attention).
- **Garde-fous** : aucun taux sous 10 observations ; aucune comparaison de politiques sans groupe témoin ; les
  plaintes et désinscriptions comptent comme des résultats.
- **Critère d'échec fixé d'avance** : si moins d'un membre volontaire sur cinq publie un besoin en 3 mois, la mécanique
  « besoin → proposition » ne tient pas dans ce Club et le produit doit être repensé.
Aucun résultat de pilote n'existe à ce jour.

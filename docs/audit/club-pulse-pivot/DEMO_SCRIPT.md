# Démonstration — banc d'essai partagé (2 minutes)

> Scénario **illustratif** : aucune demande réelle d'exposant n'existe dans nos documents. Personnes, entreprises et
> offres sont **fictives**. Les actions sont faites **en direct** depuis deux téléphones.

## Préparation (5 minutes avant)
1. `make setup` puis lancer le serveur **sur la machine de démonstration** :
   `cd prototype && HACKVS_SECRET=<32 caractères ou plus> HACKVS_CONSOLE_JETON=<jeton> HACKVS_ESSAIS_DB=var/essais.db python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
   (sans `HACKVS_CONSOLE_JETON`, la console ne répond qu'à la machine locale).
2. Écran commun : `http://<machine>:8000/console` → « Nouvelle démonstration ». Les codes des deux téléphones s'affichent.
3. Téléphone 1 (Sophie, porteuse) et téléphone 2 (Markus, contributeur) : ouvrir l'adresse affichée sous chaque code
   (`/app?code=…`) → « Continuer ». Deux sessions distinctes, deux appareils.
4. Vérifier sur l'écran commun : « Apertus non configuré · formulaire et règles » (ou « Apertus configuré · <modèle> »).

## Comptes et rôles
| Qui | Appareil | Rôle | Données préparées |
|---|---|---|---|
| Sophie Carron (fictive) | téléphone 1 | porteuse : pose la question, choisit, lance, observe | aucune (elle formule en direct) |
| Markus Heinzmann (fictif) | téléphone 2 | contributeur | offre publiée : « Regard neuf de distributeur sur un emballage ou une étiquette », 15 min au plus, 2 fois |
| Pauline Darbellay (fictive) | écran commun | contributrice absente de la scène : **geste JOUÉ** par l'animation, marqué | offre : « Un présentoir éclairé sur mon stand », 20 min, 1 fois |
| Léa Imhof (fictive) | — | alternative possible | offre : « Quelques minutes de regard neuf sur un support imprimé », 15 min |
| Inès (fictive) | — | offre **expirée** (visible en console) | « Photographier un produit sur fond neutre » |

## Déroulé (≈ 2 minutes)
| t | Qui | Geste | Ce que le public voit |
|---|---|---|---|
| 0:00 | Sophie | « Proposer un essai » → tape : *Notre nouvelle étiquette de tisane est-elle comprise en 10 secondes à 1 mètre par quelqu'un qui ne connaît pas la marque ?* → « Préparer » | un brouillon pré-rempli ; mention « Formulaire : aucun modèle utilisé » (ou « Préparé par Apertus — à vérifier ») |
| 0:20 | Sophie | écrit le **critère** (« Sur 3 personnes, combien nomment le produit après 10 s à 1 m ? »), ajoute « + temps » et « + lieu », enregistre | le brouillon, avec pour chaque geste les **offres admissibles** (anonymes) |
| 0:35 | Sophie | choisit l'offre « Regard neuf de distributeur… » → « Publier la proposition » | « proposé : en attente de choix » ; personne n'est nommé |
| 0:45 | animation | console : « Pauline accepte » (JOUÉ) | l'écran commun marque le geste comme joué |
| 0:50 | Markus | « Mes actions » → la proposition → lit SA part (10 min, pour Sophie, avant le …, ce qui sera partagé) → « Accepter ma part » | Sophie voit « autorisé » et, seulement maintenant, le nom de Markus |
| 1:05 | **jury** | demande à Markus de réduire sa disponibilité : « Mes conditions ont changé » → **5** minutes → « Mettre à jour » | Sophie : « Une condition a changé » — *demande 10 min, l'offre en accepte 5* ; « Reste valable : Pauline » ; le bouton « Lancer » a disparu |
| 1:20 | Sophie | choisit : **raccourcir le geste à 5 min** (ou : demander à une autre personne) | nouvelle version ; Markus doit redonner SON accord (sa part a changé) ; Pauline, non |
| 1:30 | Markus | « Accepter ma part » (5 min) | Sophie : « autorisé » → « Lancer l'essai » |
| 1:35 | Sophie + Markus | Sophie lance ; **Markus regarde réellement l'étiquette** (objet physique) ; Sophie touche « Contribution reçue » pour chaque geste | « contributions reçues — aucun résultat n'en découle » |
| 1:45 | Sophie | déclare ce qu'elle a VRAIMENT observé (qualification + portée) | « déclaration humaine du porteur — non vérifiée par le système » |
| 1:55 | Markus / Sophie | Markus confirme ou conteste ; chacun choisit la réutilisation | « visible par : participants » tant que chacun n'a pas dit « club » |

## Perturbation du jury
Perturbation **principale** (gérée et testée) : **moins de temps** (Markus : 15 → 5 minutes). Le jury peut aussi demander :
Markus **décline** (→ alternative Léa ou arrêt), Markus **retire son offre**, Sophie **change le critère** (→ les accords
concernés sont redemandés, pas les autres). Ne pas improviser une perturbation non listée ici.

## Résultat positif possible
Markus nomme le produit : Sophie déclare « positif », portée « 1 personne, 1 m, lumière de la salle ». C'est UNE
observation, pas une preuve de lisibilité en général : l'écran le dit.

## Résultat négatif possible
Markus ne comprend pas le produit : Sophie déclare « négatif ». **On le garde tel quel** : un essai qui échoue est une
information. Si Markus conteste la portée (« j'étais à 2 m »), la contestation reste affichée.

## Secours
| Problème | Secours |
|---|---|
| Apertus absent ou en panne | formulaire (mode affiché) ; rien d'autre ne change |
| Markus décline pour de vrai | l'écran montre l'alternative (Léa) ou « impossible en l'état » : on le montre, on ne force rien |
| personne n'accepte | arrêt honnête : « expiré sans lancement » (avancer l'horloge SIMULÉE de 15 jours, annoncé comme tel) |
| réseau de la salle | téléphones sur le même point d'accès que la machine ; sinon, un seul ordinateur avec deux fenêtres privées (deux sessions) |
| tout tombe | rejouer le test de bout en bout (`make e2e`) à l'écran : **annoncer « REPLAY automatisé »** |

## Mentions de transparence (à dire et affichées)
- Données **préparées** : membres, entreprises et offres fictifs. Actions **en direct** : Sophie et Markus, sur leurs
  téléphones. Gestes **joués** : Pauline (et Léa si utilisée), marqués dans la console.
- Mode IA : affiché sur chaque brouillon ; « Apertus » n'apparaît que si un appel a réellement réussi.
- Horloge : **simulée** quand on l'avance. Aucun résultat terrain, aucune adoption, aucun effet économique n'est montré.

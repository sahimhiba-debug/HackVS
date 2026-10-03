# Feuille de route — 30 jours pour lancer, 45 pour prouver, la Foire 2027 pour grandir

Révisée le 03.10.2026 (vague 3, liste du Club reçue). La vitesse de la nuit du 3 octobre change le plan : **le code
n'est plus le goulot, la validation l'est**. Il faut des membres réels, un juriste, des partenaires.

- Les trois jalons sont comptés **à partir du feu vert du Club** (J0).
- Le prototype tourne sur un **monde de démonstration** (150 profils fictifs).
- Le Club réel compte **145 entreprises et 173 représentants** (liste fournie par le Club ; métiers proposés par
  l'équipe, à confirmer).
- **La demande au Club** : « Un pilote de 45 jours avec 50 membres volontaires parmi vos 173 représentants. »
- Rien ci-dessous n'est fait sauf mention contraire. L'état daté de chaque chantier est dans [etat.yaml](etat.yaml),
  repris par [README.md](README.md).

## Jalon 1 — « Lancer » (J0 → J+30)

Durcir ce qui existe pour la production, faire valider ce qui touche aux personnes, puis lancer devant les membres.

| Chantier | Qui | Sortie |
|---|---|---|
| Durcissement : sécurité, sauvegardes chiffrées du journal, supervision, vrais e-mails (fournisseur suisse) ; hébergement en Suisse (la démo de la Foire tourne sur le Mac du pitch, derrière un tunnel : [DEMO_TUNNEL.md](../DEMO_TUNNEL.md)) | 2 ingénieurs | service en production, restauration testée |
| **Conditions d'utilisation du service d'IA** : Apertus 1.5 est servi par le CSCS (Lugano) ; vérifier que ses conditions permettent un pilote, sinon relais par Public AI ou un hébergeur suisse | ingénieur + secrétariat | réponse écrite du CSCS ou solution de relais choisie |
| **Audit de sécurité externe** | prestataire | rapport, corrections faites avant le lancement |
| **Analyse d'impact nLPD / RGPD avec un juriste** (registre des traitements : modèle prêt dans `docs/conformite/`) | juriste + secrétariat | analyse signée, information FR / DE validée |
| Relecture des traductions allemandes par des germanophones | 2 membres du Haut-Valais | écrans DE validés |
| **Recrutement de 50 volontaires parmi les 173 représentants**, lancement lors d'un événement du Club (le mode salle sert ce soir-là) | communauté + secrétariat | 50 volontaires inscrits, capacités déclarées |

## Jalon 2 — « Prouver » : pilote de 45 jours (début janvier → mi-février 2027)

Le pilote évite les fêtes et **culmine pendant les Championnats du monde de ski alpin de Crans-Montana (1er – 14 février
2027)**. Pendant cette période, hôtels, transport, traiteurs et bras manquent partout en Valais : c'est le test le plus dur.

**Risque nommé : « quand tout le monde manque de tout, l'entraide tient-elle ? »** Si oui, la preuve vaut beaucoup.
Sinon, on le saura avant d'investir. Le bilan le dira dans les deux cas.

Les **critères de réussite sont fixés d'avance**, sur les **50 volontaires**, et marqués **« à valider avec le Club »** :

| Critère (à valider avec le Club) | Seuil |
|---|---|
| Demandes adressées | **≥ 25** |
| Part de « oui » | **≥ 30 %** |
| Premier oui, médiane | **< 72 h** |
| Membres actifs | **≥ 15 sur les 50 volontaires** |
| Incidents de confidentialité | **0** |

**Avec ce volume, le taux de réponse est un signal, pas une mesure fine** : 25 demandes, c'est un ordre de grandeur,
pas une statistique. Le bilan le dira tel quel.

Pendant et à la fin du pilote : bilan au comité (`make bilan`, mêmes chiffres que Suivi) ; **premier partenaire
français** approché ; **dépôt Interreg France-Suisse avant le 12 mars 2027**, avec les résultats du pilote ; **chèque
d'innovation Innosuisse** avec la HES-SO Valais-Wallis (voir [FINANCEMENT_JURIDIQUE.md](FINANCEMENT_JURIDIQUE.md)).

## Jalon 3 — « Grandir » (jusqu'à la Foire 2027)

- **Membres à distance** et **adhésion croisée** avec une chambre partenaire (exemple fictif dans le prototype, aucun
  partenaire acquis) ;
- parcours **« Allumage Foire »** avec les exposants : QR sur les stands, passe découverte, page « prévu ensuite » ;
- **mesure des adhésions venues du passe découverte** (intentions → adhésions réelles, comptées par le secrétariat).

## Pistes de partenaires — toutes « à contacter », aucune acquise

| Piste | Pourquoi | Statut |
|---|---|---|
| **Le stand de la Haute-Savoie** (région d'honneur de la Foire 2026) | premier partenaire français naturel ; chef de file possible pour Interreg | à contacter pendant la Foire |
| **La Vallée d'Aoste** | voisine, francophone, même logique transfrontalière | à contacter |
| **Crans-Montana 2027** (comité d'organisation des Mondiaux) | un appel à projets pour les associations existerait : **à vérifier** | à contacter, existence de l'appel à vérifier |

## Équipe (resserrée)

| Rôle | Charge |
|---|---|
| 2 ingénieurs : production, sécurité, support | plein temps pendant « Lancer », mi-temps ensuite |
| 1 personne communauté et partenariats | mi-temps |
| Le secrétariat du Club | temps partiel (clôture des reçus, relais des annonces, bilan) |

## Budget — hypothèses (à chiffrer, rien n'est engagé)

| Poste | Hypothèse |
|---|---|
| Hébergement en Suisse (VPS, sauvegardes, e-mails) — pour le pilote ; la démo de la Foire ne coûte rien (Mac + tunnel) | quelques dizaines de CHF par mois |
| Audit de sécurité externe | forfait à demander à deux prestataires |
| Juriste (analyse d'impact) | forfait à demander |
| Ingénierie | 2 personnes sur 30 jours, puis mi-temps — à couvrir par fonds propres, chèque Innosuisse, puis Interreg |
| Modèle de langage (Apertus) | à l'appel ; la démonstration et le pilote tournent aussi sans modèle |

## Métriques

Celles de l'écran Suivi ([SUIVI_METRIQUES.md](SUIVI_METRIQUES.md)) : demandes, oui / non / pas cette fois, délai du
premier oui, partenariats par étape, membres actifs, hors Valais, invités — agrégats, seuil « < 3 ».

## Dépendances

Feu vert du comité ; 50 volontaires ; juriste disponible avant le lancement ; hébergement en Suisse ; un chef de file
français pour Interreg ; conditions d'utilisation du CSCS pour Apertus (facultatif : le produit tient sans modèle).

## Risques et parades

| Risque | Parade |
|---|---|
| Peu de réponses pendant le pilote | une demande à la fois, plafond hebdomadaire, réponse depuis l'e-mail, escalade vers des piliers volontaires |
| **Membres débordés pendant les Mondiaux** | c'est le risque nommé ; plafond hebdomadaire ; « Pas cette fois » ne coûte rien ; la mesure dira si l'entraide tient sous tension |
| Conditions du CSCS incompatibles avec un pilote | relais par Public AI ou un hébergeur suisse ; le produit tient sans modèle (parité testée) |
| Un petit club permet de deviner | seuil « < 3 » partout, compté en **entreprises distinctes** (deux représentants d'une même entreprise comptent une fois) ; message honnête ; rien de nominatif sans double accord |
| Données de membres résidant en France | analyse d'impact avec un juriste avant le lancement ; consentement prouvé par le reçu ; purge réelle |
| L'IA se trompe sur des demandes vagues | l'IA propose, le membre décide ; parité IA allumée / éteinte ; abstention permise |
| Volume trop faible pour conclure | dit d'avance : le taux est un signal ; décision du comité sur des critères fixés avant |
| Le secrétariat porte trop | tableau de bord, bilan généré, relais minimal |

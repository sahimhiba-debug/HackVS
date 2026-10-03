# Feuille de route — 30 jours pour lancer, 45 pour prouver, la Foire 2027 pour grandir

Révisée le 03.10.2026 (vague 2) : la vitesse de la nuit du 3 octobre change le plan. **Le code n'est plus le goulot ;
la validation l'est** — avec des membres réels, un juriste, des partenaires. Les trois jalons sont comptés **à partir
du feu vert du Club** (J0). Le prototype tourne sur un **monde de démonstration** (150 profils fictifs) ; le Club réel
compte **une cinquantaine de membres**. Rien ci-dessous n'est fait sauf mention contraire : l'état daté de chaque
chantier est dans [etat.yaml](etat.yaml), repris par [README.md](README.md).

## Jalon 1 — « Lancer » (J0 → J+30)

Durcir ce qui existe pour la production, faire valider ce qui touche aux personnes, puis lancer devant les membres.

| Chantier | Qui | Sortie |
|---|---|---|
| Durcissement : sécurité, sauvegardes chiffrées du journal, supervision, vrais e-mails (fournisseur suisse) | 2 ingénieurs | service en production, restauration testée |
| **Audit de sécurité externe** | prestataire | rapport, corrections faites avant le lancement |
| **Analyse d'impact nLPD / RGPD avec un juriste** (registre des traitements : modèle prêt dans `docs/conformite/`) | juriste + secrétariat | analyse signée, information FR / DE validée |
| Relecture des traductions allemandes par des germanophones | 2 membres du Haut-Valais | écrans DE validés |
| **Lancement auprès des 50 membres lors d'un événement du Club** (le mode salle sert ce soir-là) | communauté + secrétariat | membres inscrits, capacités déclarées |

## Jalon 2 — « Prouver » : pilote de 45 jours (début janvier → mi-février 2027)

Le pilote évite les fêtes. Les **critères de réussite sont fixés d'avance** et marqués **« à valider avec le Club »** :

| Critère (à valider avec le Club) | Seuil |
|---|---|
| Demandes adressées | **≥ 25** |
| Part de « oui » | **≥ 30 %** |
| Premier oui, médiane | **< 72 h** |
| Membres actifs | **≥ 15 sur 50** |
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

## Équipe (resserrée)

| Rôle | Charge |
|---|---|
| 2 ingénieurs : production, sécurité, support | plein temps pendant « Lancer », mi-temps ensuite |
| 1 personne communauté et partenariats | mi-temps |
| Le secrétariat du Club | temps partiel (clôture des reçus, relais des annonces, bilan) |

## Budget — hypothèses (à chiffrer, rien n'est engagé)

| Poste | Hypothèse |
|---|---|
| Hébergement en Suisse (VPS, sauvegardes, e-mails) | quelques dizaines de CHF par mois |
| Audit de sécurité externe | forfait à demander à deux prestataires |
| Juriste (analyse d'impact) | forfait à demander |
| Ingénierie | 2 personnes sur 30 jours, puis mi-temps — à couvrir par fonds propres, chèque Innosuisse, puis Interreg |
| Modèle de langage (Apertus) | à l'appel ; la démonstration et le pilote tournent aussi sans modèle |

## Métriques

Celles de l'écran Suivi ([SUIVI_METRIQUES.md](SUIVI_METRIQUES.md)) : demandes, oui / non / pas cette fois, délai du
premier oui, partenariats par étape, membres actifs, hors Valais, invités — agrégats, seuil « < 3 ».

## Dépendances

Feu vert du comité ; juriste disponible avant le lancement ; hébergement en Suisse ; un chef de file français pour
Interreg ; disponibilité d'Apertus (facultatif : le produit tient sans modèle).

## Risques et parades

| Risque | Parade |
|---|---|
| Peu de réponses pendant le pilote | une demande à la fois, plafond hebdomadaire, réponse depuis l'e-mail, escalade vers des piliers volontaires |
| Un petit club permet de deviner | seuil « < 3 » partout ; message honnête ; rien de nominatif sans double accord |
| Données de membres résidant en France | analyse d'impact avec un juriste avant le lancement ; consentement prouvé par le reçu ; purge réelle |
| L'IA se trompe sur des demandes vagues | l'IA propose, le membre décide ; parité IA allumée / éteinte ; abstention permise |
| Volume trop faible pour conclure | dit d'avance : le taux est un signal ; décision du comité sur des critères fixés avant |
| Le secrétariat porte trop | tableau de bord, bilan généré, relais minimal |

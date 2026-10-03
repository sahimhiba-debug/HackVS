# Feuille de route — six mois après la Foire (octobre 2026 → avril 2027)

Le prototype tourne sur un **monde de démonstration** (150 profils fictifs). Le Club réel compte **une cinquantaine de
membres**. Rien ci-dessous n'est fait sauf mention contraire (voir [README.md](README.md) pour l'état daté). Chaque
jalon chiffré est un **objectif**, mesuré par l'écran Suivi ([SUIVI_METRIQUES.md](SUIVI_METRIQUES.md)) — jamais
affiché comme atteint avant d'être mesuré.

## Phase 0 — cadrage (semaines 1 à 3)

- **Métriques signées par le Club** : les définitions de [SUIVI_METRIQUES.md](SUIVI_METRIQUES.md), relues et signées
  par le comité ; le seuil k = 3 confirmé.
- **Analyse d'impact nLPD / RGPD** (voir [FINANCEMENT_JURIDIQUE.md](FINANCEMENT_JURIDIQUE.md)) avant toute donnée réelle.
- **Rendez-vous** : CimArk / Innosuisse (chèque d'innovation), Secrétariat conjoint Interreg France-Suisse (chef de
  file français), contact **HES-SO Valais-Wallis** (partenaire de recherche).
- Sortie : un pilote autorisé, des métriques signées, un calendrier de financement.

## Phase 1 — mois 1 à 3 · 5 ingénieurs · pilote mesuré avec les 50 membres

| Chantier | État au gel | Remarque |
|---|---|---|
| Pilote mesuré avec les membres réels | ⬜ | données d'identité séparées du journal dès le jour 1 |
| Réponse depuis l'e-mail (Oui / Non / Pas cette fois, liens signés à usage unique) | ⬜ / 🟡 selon F | prototype : boîte de sortie locale « simulé en démonstration » si F livré |
| Escalade vers des membres « piliers » quand une demande reste sans réponse | ⬜ | décidée par une personne, jamais par l'IA |
| Clôture de reçu (signé / test sans suite / contact établi / abandonné) | ✅ prototype | B, testé |
| Tableau de bord du secrétariat (Suivi) | ✅ prototype | A, agrégats, k = 3 |
| Bilan trimestriel | ⬜ / 🟡 selon G | `make bilan` |
| Passe découverte | ✅ prototype | D, 90 jours, 3 demandes |

**Jalon de fin de phase 1 (objectifs, à mesurer)** : ≥ 30 membres avec une capacité déclarée ; ≥ 40 demandes
adressées ; ≥ 30 % de oui ; premier oui en moins de 72 h en médiane.

## Phase 2 — mois 4 et 5 · 8 ingénieurs · au-delà du Valais romand

- Interface et demandes **en allemand** (Haut-Valais, acheteurs alémaniques) ; les écrans d'invité sont déjà FR / DE.
- Statut **membre à distance** (zone, langue, réponse depuis l'e-mail).
- **Adhésion croisée** avec un partenaire français (CCI France Suisse / CCSF — voir [BENCHMARK.md](BENCHMARK.md)).
- **Annonces sous chiffre intermédiées** (le Club relaie, l'entreprise reste anonyme jusqu'à son accord).
- Dossiers de **financement** déposés (Interreg avant le 12 mars 2027, Innosuisse).

**Jalon (objectifs)** : ≥ 10 membres actifs hors Valais romand ; un partenaire français signé.

## Phase 3 — mois 6 · « Allumage Foire »

- QR sur les stands de la Foire, passe découverte, page « prévu ensuite » ;
- pont avec le concours de pitch **The Ark** ;
- **simulation à 50 utilisateurs** (charge, concurrence, mode salle) avant l'édition suivante.

## Équipe

| Rôle | Phase 1 | Phase 2 |
|---|---|---|
| Produit / animation du Club | 1 | 1 |
| Back-end (journal, registre, sécurité) | 2 | 3 |
| Front-end (téléphone, console, accessibilité) | 1 | 2 |
| IA (Apertus, évaluation, voir [APERTUS_PLAN.md](APERTUS_PLAN.md)) | 1 | 1 |
| Données / juridique (nLPD, RGPD, DPIA) | — (prestataire) | 1 |
| **Total ingénieurs** | **5** | **8** |

## Dépendances

Accord du comité sur les métriques ; analyse d'impact avant données réelles ; hébergement en Suisse ; un chef de file
français pour Interreg ; disponibilité d'un modèle Apertus servi en Suisse.

## Risques et parades

| Risque | Parade |
|---|---|
| Les membres ne répondent pas (taux de oui faible) | une demande à la fois, plafond hebdomadaire, réponse depuis l'e-mail ; on mesure avant d'élargir |
| Un petit club permet de deviner qui s'est retiré | k = 3 sur tout décompte ; message honnête (« dans un petit club on peut parfois deviner ») |
| Données de membres résidant en France | RGPD + nLPD dès la phase 0 ; consentement prouvé par le reçu ; purge réelle des identités |
| L'IA se trompe sur des demandes vagues | l'IA propose, le membre décide ; parité IA allumée / éteinte ; repli déterministe |
| Financement en retard | pilote phase 1 dimensionné sur fonds propres + chèque d'innovation |
| Dépendance à une seule personne du secrétariat | console documentée, bilan généré, runbook |

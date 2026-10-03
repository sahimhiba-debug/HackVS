# Financement et cadre juridique

> **Analyse générale, pas un avis juridique.** Les montants, dates et conditions ci-dessous proviennent du cadrage de
> l'équipe (octobre 2026) ; ils n'ont pas été revérifiés auprès des organismes cités pendant la nuit du 3 au 4.10 et
> **doivent l'être avant tout dépôt** (jalon « Lancer » de la [ROADMAP.md](ROADMAP.md), avant le dépôt Interreg du jalon « Prouver »).

## Financement

| Source | Ce que c'est | Conditions retenues | Usage pour Club Pulse |
|---|---|---|---|
| **Interreg France-Suisse 2021-2027** | programme européen de coopération transfrontalière | fenêtre de dépôt **du 12 septembre 2026 au 12 mars 2027** ; priorité 2 « Recherche, innovation, usages numériques » (**17,2 M€ FEDER + 12,7 MCHF**) ; **chef de file français obligatoire, en Haute-Savoie ou dans l'Ain** | jalon « Prouver » : dépôt avant le 12.03.2027 avec les résultats du pilote de 45 jours ; « Grandir » : membres à distance, adhésion croisée ; exemples proches cités : **ArcINNOLAB**, **UX ARC NEXUS** |
| **Innosuisse** | agence suisse pour l'innovation | **chèque d'innovation** puis **projet d'innovation** avec une haute école (HES-SO Valais-Wallis) ; **40 à 60 % de contribution propre** | jalon « Prouver » (chèque d'innovation) : évaluation d'Apertus sur les demandes du Club ([APERTUS_PLAN.md](APERTUS_PLAN.md)) |
| **Fondation The Ark** | promotion de l'innovation en Valais | à préciser au rendez-vous CimArk | pont avec le concours de pitch (jalon « Grandir ») |
| **NPR** (Nouvelle politique régionale) | soutien régional | à préciser avec le canton | ancrage valaisan, Haut-Valais |
| **Crans-Montana 2027** (Mondiaux, 1er – 14.02.2027) | un appel à projets pour les associations existerait | **existence et conditions à vérifier** — piste « à contacter » | le pilote culmine pendant les Mondiaux |

## Cadre juridique

- **nLPD** (Suisse) : applicable au Club et à l'hébergeur ; registre des traitements, information, sécurité.
- **RGPD** : applicable aux membres et invités **résidant en France** (offre de services ciblant des personnes dans
  l'UE) ; la désignation d'un **représentant dans l'UE** est **à vérifier**.
- **Décision d'adéquation** : la Commission européenne a confirmé le **15 janvier 2024** l'adéquation de la Suisse —
  un hébergement en Suisse de données de résidents français est licite sans garanties supplémentaires (à confirmer
  dans l'analyse d'impact).
- **Consentement granulaire, prouvé** : un consentement par finalité ; le **reçu** (référence, finalité, date,
  révocable) en est la preuve, côté membre comme côté Club — déjà dans le prototype (registre des capacités, passe
  découverte).
- **Retrait = purge réelle** : le journal des événements est **séparé des identités** (coffre) ; « tout effacer » retire
  l'identité du coffre, ce qui reste du journal ne désigne plus personne — déjà dans le prototype (`/moi/effacer`).
- **Information FR / DE** : écrans, reçus et politique de confidentialité dans les deux langues (écrans d'invité déjà
  FR / DE ; relecture par des germanophones au jalon « Lancer »).
- **Pas de décision automatisée** au sens de l'art. 21 nLPD / art. 22 RGPD : **l'IA propose, le membre décide** ;
  aucune capacité, aucun consentement, aucun destinataire n'est choisi par un modèle (testé : `test_frontiere_ia.py`).
- **Liste d'entreprises** (`docs/data/entreprises.csv`, reçue du Club le 3 octobre : 145 lignes, **colonne métier
  seule**, aucun nom dans le dépôt) : sert uniquement à compter des métiers ; aucune offre attribuée à une vraie
  entreprise ; classification proposée par l'équipe, à confirmer avec le Club.
- **Seuil « < 3 » en entreprises distinctes** : deux représentants d'une même entreprise ne comptent qu'une fois.
- **Service d'IA** : Apertus 1.5 est servi par le **CSCS (Lugano)**. Ses conditions d'utilisation doivent être vérifiées
  pour un pilote (jalon « Lancer ») ; à défaut, relais par Public AI ou un hébergeur suisse.

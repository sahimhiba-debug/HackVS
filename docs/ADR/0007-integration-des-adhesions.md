# ADR 0007 — Intégration des adhésions par adaptateur

Statut : **accepté** (prototype). Date : 2026-09-29.

## Contexte
Les membres existent déjà dans le système du Club (Organisation → Adhésion → Personne, cartes entreprise). Nous
n'avons pas accès à ce système.

## Décision
Interface `FournisseurAdhesions.importer() -> Import` (`intelligence/identite.py`) avec trois implémentations :
`AdhesionsSynthetiques` (démonstration), `AdhesionsCSV` (export du Club, colonnes documentées), `AdhesionsAPIClub`
(lève `NonConnecte` : aucune API n'est prétendue). L'activation d'un compte se fait par code d'invitation (QR), pas
par inscription.

## Conséquences
+ Brancher le vrai système = écrire un adaptateur ; le moteur ne change pas.
− Pas de synchronisation (départs, changements d'organisation) : à concevoir avec le Club (fréquence, source d'autorité).

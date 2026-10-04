# Analyse d'impact relative à la protection des données (AIPD) — modèle pré-rempli

> **À VALIDER PAR UN JURISTE.** Base : nLPD art. 22 (et RGPD art. 35 si le RGPD s'applique, art. 3 al. 2 — à évaluer). Modèle de
> l'équipe : il dit ce que l'on sait aujourd'hui, et ce qui reste à décider. **Construit — branche `annee-1`.**

## 1. Description
Club Pulse fait circuler les demandes d'entraide entre membres d'un club d'entrepreneurs (« Oui / Non / Pas cette
fois »), avec consentement d'abord, et des bilans AGRÉGÉS pour le secrétariat. IA facultative (Apertus 1.5, servi par
le CSCS), jamais nécessaire au fonctionnement.

## 2. Nécessité et proportionnalité
- Données minimales : compétences déclarées, disponibilité, région, langue ; aucun profilage commercial.
- Pas de classement des membres ; solde « reçus / donnés » visible du membre seul.
- Seuil « < 3 » compté par entreprise sur tout décompte.

## 3. Risques identifiés (à coter par le responsable)
| Risque | Gravité (à coter) | Vraisemblance (à coter) | Mesures en place | Reste à faire |
|---|---|---|---|---|
| Ré-identification par recoupement des décomptes | | | seuil « < 3 » par entreprise | revue des bilans par le comité |
| Accès non autorisé à la console | | | compte nominatif, TOTP, élévation, journal des accès | revue trimestrielle du journal des accès |
| Fuite d'un texte vers l'IA | | | noms filtrés avant l'appel ; interrupteur ; prestataire suisse | contrat avec le CSCS |
| Suppression incomplète | | | purge réelle, copies comprises (lot 3) ; `secure_delete` | durée des sauvegardes et du WAL |
| Sollicitation non voulue | | | consentement d'abord, pause, désinscription | — |
| Notification au mauvais destinataire | | | adresses du coffre seulement, suivi sans contenu | vérification des adresses à l'import |

## 4. Avis
*[Conseiller à la protection des données / juriste : à compléter. Consultation du PFPDT si le risque reste élevé
(nLPD art. 23).]*

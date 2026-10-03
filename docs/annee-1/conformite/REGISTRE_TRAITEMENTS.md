# Registre des activités de traitement — Club Pulse

> **À VALIDER PAR UN JURISTE.** Modèle rédigé par l'équipe, pas un avis juridique. Base : loi fédérale sur la
> protection des données (nLPD, RS 235.1), art. 12 ; pour les membres frontaliers, RGPD art. 30. **Construit —
> branche `annee-1`, pas dans la démo** : aucun membre réel n'a encore été traité.

Responsable du traitement : *[le Club — raison sociale, adresse, contact protection des données : à compléter]*.

| # | Traitement | Finalité | Personnes | Données | Base | Destinataires | Durée de conservation (PROPOSÉE) | Mesures |
|---|---|---|---|---|---|---|---|---|
| 1 | Comptes et accès | ouvrir et sécuriser l'accès des membres et du secrétariat | membres, invités, secrétariat | étiquette du compte, rôle, appareils, sessions, second facteur (jamais en clair) | contrat d'adhésion | hébergeur | durée de l'adhésion + 3 mois | invitation à usage unique, TOTP pour la console, sessions signées |
| 2 | Profil de membre | proposer des mises en relation à la demande du membre | membres | compétences déclarées, disponibilité, région, langue | consentement (révocable) | aucun (pseudonymes dans le moteur) | jusqu'à la suppression du compte | pseudonymisation, coffre d'identités séparé |
| 3 | Demandes et réponses « Oui / Non / Pas cette fois » | faire circuler une demande vers qui peut aider | membres | texte de la demande, réponses | consentement | les membres concernés (accord mutuel) | 24 mois après la clôture | jamais de nom avant l'accord des deux, seuil « < 3 » par entreprise |
| 4 | Reçus de consentement | prouver chaque accord et chaque retrait | membres | finalité, date, statut | obligation de preuve | le membre lui-même | durée de l'accord + 3 ans | export JSON-LD aligné ISO/IEC TS 27560 (aligné, pas certifié) |
| 5 | Notifications | prévenir un membre d'une demande qui l'attend | membres | adresse e-mail, téléphone (canaux choisis) | consentement (désinscription en un clic) | fournisseur SMTP / SMS *[à désigner]* | suivi sans adresse ni contenu : 12 mois | lien de désinscription signé, rien pendant la pause |
| 6 | Passe découverte (invités) | laisser un non-membre aider pendant 90 jours | invités | entreprise, métier, région déclarés | consentement | le Club | 90 jours + 3 mois | usage unique, révocable |
| 7 | Console du secrétariat | animer le Club (bilans agrégés, campagnes) | secrétariat, membres (agrégés) | décomptes seulement ; journal des accès | intérêt légitime du Club | comité (bilan) | journal des accès : 12 mois | compte nominatif + TOTP, « < 3 » par entreprise |
| 8 | IA (Apertus 1.5, servi par le CSCS) | reformuler, extraire, classer — facultatif | membres | textes de demande (jamais les noms : filtrés avant l'appel) | consentement | CSCS (Suisse) | aucune conservation côté Club au-delà du journal des appels | interrupteur, repli déterministe, parité testée |
| 9 | Sauvegardes | reprendre après une panne | toutes | journal complet | intérêt légitime | hébergeur | *[à fixer : 30 jours proposés]* | format vérifié par empreinte, restauration tout ou rien |

Transferts à l'étranger : aucun prévu (hébergement et CSCS en Suisse) — *à confirmer selon l'hébergeur retenu*.
Suppression : réelle, y compris des copies dans le journal (lot 3) ; les sauvegardes suivent leur durée (ligne 9).

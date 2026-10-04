# Guide du pilote pour le secrétariat

> **Modèle, à relire avec le secrétariat du Club.** Le pilote n'a pas commencé. La console du secrétariat est
> **construite sur la branche annee-1, pas dans la démo** (interrupteurs `HACKVS_COMPTES=1`, `HACKVS_SECRETARIAT=1` :
> [CONFIGURATION.md](../CONFIGURATION.md)).

## Avant le pilote (une fois)

1. **Votre compte.** L'administration vous envoie une invitation (`/compte#invitation=…`). Acceptez-la, puis activez
   la **double authentification** (application d'authentification sur votre téléphone). Pour toute action
   d'administration, vous « élevez » votre session avec un code : elle reste élevée 12 heures.
2. **Les critères du pilote.** Console → « Pilote » : relisez les critères avec le comité, puis cliquez **« Geler les
   critères »**. C'est irréversible : une fois gelés, ils ne peuvent plus être ajustés aux résultats. C'est voulu.
3. **Les métiers.** Console → « Métiers à confirmer » : rattachez chaque libellé de la liste d'entreprises à un métier.
   Seule la colonne « métier » est lue, jamais un nom d'entreprise.
4. **Les volontaires.** Envoyez à chaque volontaire le lien et le code d'invitation, avec le
   [kit d'accueil](KIT_ACCUEIL_FR.md) (FR) ou le [Begrüssungskit](KIT_ACCUEIL_DE.md) (DE).

## Chaque semaine (environ 30 minutes — à mesurer)

| Quoi | Où dans la console | Pourquoi |
|---|---|---|
| Regarder le tableau du pilote | « Pilote » | suivre les critères, sans les changer |
| Relancer les membres qui ont des demandes en attente | « Notifications » | une relance, pas un harcèlement : chaque membre reçoit au plus un e-mail de ce type par jour, jamais pendant sa pause ni après s'être désinscrit |
| Inviter des entreprises d'un métier qui manque (passes découverte) | « Le Club cherche → campagne d'invitation » | au plus 20 invitations par campagne et 100 par jour |
| Confirmer les adhésions venues d'un passe découverte | « Foire » → saisir la **référence** que l'invité montre (`P-XXXXXXXX`) | une intention n'est jamais une adhésion : seule une adhésion confirmée compte |
| Regarder le suivi de l'IA | « Ce que le Club comprend des demandes » | taux d'acceptation des propositions ; rien en dessous de 3 entreprises |
| **Noter votre temps passé** | sur papier ou tableur | c'est la mesure qui décidera si le Club peut porter le service après le pilote |

## Ce que vous ne verrez jamais (et c'est voulu)

- qui a dit **Non** ou **Pas cette fois** ;
- un chiffre portant sur **moins de 3 entreprises** (affiché « < 3 ») ;
- les notes privées des membres ;
- une liste des invités qui veulent adhérer (vous recevez leur référence quand ils la montrent).

## Si un membre demande…

| Demande | Réponse |
|---|---|
| « Que sait le Club de moi ? » | « Mes données », sur son téléphone ; il peut aussi « Télécharger mes données (JSON) » depuis « Mon espace » |
| « Je veux tout effacer » | « Mes données » → Tout effacer ; c'est définitif, il n'y a rien à faire de votre côté |
| « Je ne veux plus d'e-mails » | le lien « Ne plus recevoir ces e-mails » en bas de chaque e-mail |
| « Je suis débordé » (Mondiaux…) | « Mon espace » → « Mode pause » → « Me mettre en pause » : il ne sera plus sollicité jusqu'à la date choisie |

## À la fin du pilote

1. Console → « Bilan » : exportez le bilan trimestriel (Markdown, CSV ou PDF).
2. Présentez-le au comité **contre les critères gelés**, y compris s'ils ne sont pas atteints.
3. Joignez votre temps passé par semaine.

## En cas de problème

- Le service ne répond plus : prévenir l'équipe technique (contact à définir avant le pilote).
- Une donnée semble visible par la mauvaise personne : **arrêter et prévenir immédiatement** l'équipe ; c'est un
  incident de confidentialité (critère du pilote : **zéro**).

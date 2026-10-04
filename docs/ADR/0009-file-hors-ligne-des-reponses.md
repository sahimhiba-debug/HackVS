# ADR 0009 — File d'attente hors ligne des réponses (exception à « les données jamais en cache »)

Statut : **accepté pour la branche annee-1** (construit, pas dans la démo). Date : 2026-10-04.

## Contexte
L'ADR 0008 interdit de garder des données sur le téléphone : le service worker ne met en cache que l'enveloppe. Au
stand d'une foire ou dans un hall d'hôtel, le réseau tombe au moment où le membre répond à une demande. Le lot 11
demande une « file d'attente hors ligne pour les réponses ».

## Décision
- Interrupteur `HACKVS_HORS_LIGNE=1`, dit au téléphone par `/api/pulse/moi/date` (aucun appel supplémentaire : éteint,
  la démo ne fait aucune requête de plus et ne laisse aucune erreur dans la console).
- Seules les **réponses aux demandes** (Oui / Non / Pas cette fois) entrent dans la file : jamais une lecture, jamais
  un écran, jamais une autre écriture.
- La file est dans `localStorage` (elle survit à la fermeture de l'application installée), **une entrée par demande**
  (la dernière réponse gagne), **liée au membre** qui l'a donnée (son identifiant, jamais le jeton de session : jamais envoyée sous un autre compte ;
  celle d'un autre membre trouvée sur l'appareil est effacée, et c'est dit) ; vidée par « Se déconnecter » et « Tout
  effacer » (audit des lots 11-12, I1 et I2).
- Au retour du réseau (`online`, ou au prochain écran), chaque réponse est envoyée ; **le serveur reste seul juge** :
  une demande qui n'est plus d'actualité est refusée, retirée de la file, et le membre le lit. Une réponse refusée
  n'est jamais renvoyée.
- Interrupteur éteint (ou éteint ensuite) : la file est vidée sans rien envoyer.

## Conséquences
+ Une réponse donnée sans réseau n'est pas perdue ; le membre voit « en attente du réseau » sur la demande.
− **Exception assumée à l'ADR 0008** : jusqu'à l'envoi, la réponse (Oui/Non, nombres, texte facultatif) est sur le
  téléphone, lisible par qui a le téléphone déverrouillé. Dit dans la politique de confidentialité FR / DE et les kits d'accueil.
− Les demandes ne sont pas mises en cache : on ne peut répondre hors ligne qu'à une demande DÉJÀ affichée.
− Pas de synchronisation en arrière-plan (Background Sync) : l'envoi attend que l'application soit ouverte.

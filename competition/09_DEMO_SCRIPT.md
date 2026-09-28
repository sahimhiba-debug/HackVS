# 09 — Script de démonstration (scène `/demo/stage`)

Données : réseau de scène FICTIF (16 membres inventés, `prototype/data/stage_reseau.json`). Horloge simulée et fixe.
Chaque chiffre affiché est calculé par le moteur réel ; la même scène est rejouée à l'identique (testé 3 fois).
Commandes : **→ / espace** suivant · **←** précédent · **R** réinitialiser · bouton « Rejouer tout ».

| Étape | Clic | Ce que l'écran montre (calculé) | Ce que l'on dit | Pourquoi ce clic |
|---|---|---|---|---|
| 0 | (ouverture) | « La Foire crée les rencontres. Qu'en reste-t-il un mois plus tard ? » | Ouverture | Poser la question |
| 1 | → | 16 membres, 2 groupes séparés, rencontres sans suite depuis plus de 90 jours | « Des rencontres ont eu lieu ; le réseau reste fait d'îlots. » | Le problème, visible |
| 2 | → | Proposition de profil → validation par Sophie ; invisible par défaut | « Le système propose, elle corrige. C'est elle qui choisit d'être recommandée. » | Humain aux commandes, confidentialité par défaut |
| 3 | → | Besoin compris : « Développement commercial en Allemagne (obligatoire) » | « Compris localement, sans modèle externe. » | Pas de dépendance cachée |
| 4 | → | 2 candidats : Markus (fort, réciprocité PROUVÉE), Claudia (partielle, preuve déduite, profil ancien) ; qui refuse d'être sollicité n'est ni nommé, ni proposé, ni compté (moins de 3) | « Pas une liste : des preuves. Et ce qui reste inconnu. » | Pourquoi / pourquoi maintenant / comment nous savons / inconnu |
| 5 | → | Aucune coordonnée ; « distributeur au Japon » → abstention | « Nous avons préféré une abstention à une hallucination. » | **Moment intelligent n° 1** |
| 6 | → | Demande d'introduction ; boîte de Markus : 1 introduction à répondre ; coordonnées non partagées | « Il peut refuser. » | Consentement |
| 7 | → | Markus accepte : coordonnées partagées ; un trait plein apparaît dans le graphe | « Maintenant seulement. » | La relation naît |
| 8 | → | Ligne de temps : introduction demandée → acceptée → rencontre | « La relation garde son contexte. » | Mémoire relationnelle |
| 9 | → | +10 jours : 1 relance (Markus cherche ce que Sophie produit, preuves citées) ; 17 silences | Réplique d'humour | **Moment intelligent n° 2** |
| 10 | → | Suivi accepté ; « affaire en cours » = opportunité, pas résultat | « Relation ≠ opportunité ≠ résultat. » | Rigueur du modèle |
| 11 | → | Présentation Sophie ↔ Anna, proposée d'abord à Markus ; micro-cercle de 5 avec ses inconnues | « Le réseau voit ce qu'aucun membre ne voit seul. » | Valeur collective |
| 12 | → | Simulation : 2 groupes → 1 ; « proposé à la décision humaine » | « Avant d'agir, on simule. L'humain décide. » | Avant / après |

Autres écrans disponibles pour les questions : `/decision` (moteur de décision, certificat, rejeu), `/cycle`
(cycle des soirées), `/` (espace membre : boîte réseau dans « Suivi »).

**Plan B.** Si le réseau de la salle tombe : tout tourne en local (`uvicorn app.main:app`), aucune dépendance externe.
Si le navigateur plante : la vidéo `competition/video/demo.webm` (144 s) montre exactement la même scène.

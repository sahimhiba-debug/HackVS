# Banc des tâches de langage — Apertus contre repli déterministe

Apertus : **NON EXÉCUTÉ — aucun identifiant Apertus dans l'environnement**. Entrées FICTIVES. Toute sortie passe la validation du produit ; une sortie refusée n'est jamais comptée comme réussie.

| Tâche | Cas | Déterministe : justes | Apertus : acceptées | Apertus : rejetées | Apertus : indisponibles | Apertus : justes | Apertus : latence médiane |
|---|---|---|---|---|---|---|---|
| comprendre_demande | 8 | 7/8 | NON EXÉCUTÉ | — | — | — | — |
| capturer_rencontre | 3 | — | NON EXÉCUTÉ | — | — | — | — |
| expliquer | 5 | — | NON EXÉCUTÉ | — | — | — | — |
| rediger_sollicitation | 3 | — | NON EXÉCUTÉ | — | — | — | — |
| structurer_essai | 5 | 5/5 | NON EXÉCUTÉ | — | — | — | — |
| comprendre_action | 6 | 4/6 | NON EXÉCUTÉ | — | — | — | — |

Le repli déterministe EST le produit sans clé : il est mesuré ici comme référence, pas comme « IA ».
« structurer_essai » en secours = FORMULAIRE : texte recopié, objet reconnu dans une courte liste, AUCUN geste proposé — le membre complète. Temps et corrections humaines : non mesurés (aucun utilisateur).
« comprendre_action » en secours = RÈGLES : mots-clés de langue, lieu, public, jour, moment (français surtout). Notation EXACTE : une exigence non demandée est une erreur. Échecs du repli : « Besoin de quelqu'un qui parle allemand pour tenir notre stand vendredi entre 15h et 17h, des acheteurs de Zurich passent. »; « Ich möchte unseren Käse am Donnerstag deutschen Einkäufern vorstellen. ». C'est là qu'un modèle (Apertus) pourrait être utile — à vérifier par un appel réel, NON EXÉCUTÉ ici.

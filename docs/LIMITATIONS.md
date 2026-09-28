# Limites connues (à dire avant qu'on nous les demande)

## Données et preuve d'utilité
- **Aucun membre réel** n'a utilisé le produit : l'utilité est une hypothèse. Profils, historique et soirée synthétique sont fictifs.
- Les jeux d'évaluation sont écrits par l'équipe de développement : même les jeux réservés ne sont pas une évaluation indépendante.
- Le Club synthétique (150) est régulier ; de vrais profils seront plus hétérogènes et moins bien remplis.

## Compréhension du besoin
- Seules, les **règles se taisent trop** sur des formulations libres (réservé 4 : 3/15). La boucle « IA propose, membre
  confirme » le compense (15/15), mais ce chiffre suppose un membre qui reconnaît toujours la bonne compétence.
- L'IA locale **ne sait pas reconnaître un besoin hors catalogue** : elle propose toujours quelque chose (6/6 négatifs
  reçoivent des options). Le bouton « Aucune » et l'abstention du moteur protègent, pas le modèle.
- **Faux amis** : une liste éditable en corrige certains (« comptabilité carbone ») ; les cas hors liste passent (0/4
  mesurés : « formation de yoga », « loueur de voitures »…). Trois faux amis de règles restent sur les réservés.
- Italien : non couvert par les règles (le modèle e5 est multilingue, mais rien n'est mesuré en italien).

## IA générative
- **Claude et Apertus n'ont jamais été appelés réellement** : pas de clé ni d'accès réseau autorisé dans cet
  environnement. Adaptateurs testés contre des serveurs simulés (flux, sortie contrainte, refus, JSON invalide, réessai, panne).
- Aucun reranker neuronal : les poids (BGE, Jina) sont sur Hugging Face, bloqué ici.

## Produit et sécurité
- **Pas d'authentification des membres** côté API : en démo, l'identité est un en-tête ; le mode réel refuse (501).
  Le serveur MCP HTTP authentifie par jeton, mais l'API derrière lui ne sait pas encore authentifier.
- Détection des consignes dans les profils : heuristique (0 faux positif sur nos 187 profils, précision réelle inconnue).
  La protection principale est structurelle (le LLM ne voit pas les profils ; rien sans confirmation humaine).
- Disponibilité : un simple booléen ; pas d'agenda, pas de créneaux (« disponible la semaine prochaine » n'est pas compris).
- Plan de soirée : suppose que tous les membres éligibles sont présents (pas de liste d'inscrits) ; rencontres en tête-à-tête seulement.
- Échelle : recherche exhaustive (≈ 10 ms pour 37 profils) ; au-delà de quelques milliers de profils, un index serait nécessaire.
- Aucun déploiement public ; aucun avis juridique (LPD).

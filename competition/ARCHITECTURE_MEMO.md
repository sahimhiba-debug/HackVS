# Mémo architecture (travail) — décisions prises pendant les cycles techniques

1. **Une règle, un endroit.** L'état d'une relation est calculé par une seule fonction (`reseau._etat`) ; le graphe
   actuel, les paires déclinées et la carte candidat l'utilisent. Un test de propriété compare les deux chemins de
   calcul (une passe globale / une paire) sur 100 historiques générés.
2. **Historique ≠ actuel.** Le graphe des rencontres est la MÉMOIRE ; le graphe actuel (≤ 90 jours, ni décliné ni sans
   suite) sert à AGIR. Toute fonction qui s'appuie sur un lien pour proposer une action lit le graphe actuel.
3. **Consentement et refus non levables.** Ils sont exclus du problème, revérifiés par un validateur indépendant qui
   relit l'instantané brut, et bloqués par une règle du gardien. Une spécification ne peut pas les lever.
4. **Journal append-only + cache incrémental.** Lire la mémoire ne désérialise que les faits nouveaux ; resynchronisation
   par (max seq, nombre) pour rester exact si un autre objet écrit ou vide le fichier. Événements figés.
5. **Bornes à la frontière.** Toute entrée de l'API est bornée de façon déclarative ; un test d'introspection échoue si
   un nouveau champ ne l'est pas (on teste la classe, pas le cas).
6. **Pas de score composite.** L'activation du réseau se lit en indicateurs factuels (membres avec une relation
   actuelle, groupes, plus grand groupe) ; les objectifs en conflit (inclusion / cohésion) sont présentés côte à côte.
7. **Toujours la même forme de sortie pour une action d'organisation** : nature SIMULATION, hypothèses écrites,
   décision PROPOSER_A_L_HUMAIN ou NE_RIEN_FAIRE, rien n'est écrit ni envoyé.
8. **Pas d'agent, pas de microservice.** Aucun problème rencontré n'aurait été mieux résolu par un agent LLM ; tout
   tient dans un processus FastAPI + SQLite, mesuré jusqu'à 5000 membres générés.

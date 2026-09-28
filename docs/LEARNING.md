# Ce qu'il faut comprendre pour défendre le projet

Notes courtes, dans l'ordre où le jury risque de creuser.

1. **Sortie structurée d'un LLM** (`client.messages.parse(..., output_format=SortieLLM)`).
   Le modèle doit répondre dans un schéma Pydantic. Ce schéma garantit la *forme*, pas la *vérité* : d'où la seconde
   validation dans `parser_llm._valider` (vocabulaire fermé, extraits présents dans le texte saisi).
2. **Garde-fou déterministe au-dessus du LLM.** Même principe que dans Persei (un spectre hors domaine force « non certifiable ») :
   ici, un profil sans consentement ne peut pas être proposé, quoi que produise le modèle. Invariant testé.
3. **Abstention.** Équivalent produit de la détection hors domaine : sans couverture de la compétence principale,
   on ne propose rien. Les « pistes plus larges » sont séparées et étiquetées.
4. **Déclaré ou déduit.** Une offre structurée est plus fiable qu'une phrase de présentation. Les phrases négatives
   (« nous ne livrons pas ») sont ignorées. C'est une heuristique simple : elle échouera sur des négations complexes.
5. **TF-IDF.** Pondère les mots rares. Il sert ici seulement à départager, avec un faible poids (0,2).
6. **Évaluation honnête.** Référence simple avec les *mêmes filtres*, pour isoler l'apport du classement.
   Circularité : les cas sont écrits par l'auteur de la taxonomie. Remède : cas écrits à l'aveugle par l'équipe ou par des membres.
7. **Machine à états.** Les transitions autorisées sont listées dans `intros.TRANSITIONS`, avec l'acteur autorisé.
   L'API refuse (409) toute transition impossible, même appelée directement.
8. **View Transitions API et Web Speech API.** APIs natives du navigateur : aucune dépendance, amélioration progressive.
   La dictée de Chrome passe par des serveurs Google, à mentionner si on la montre.
9. **MCP (piste).** Exposer les fonctions du Club comme outils utilisables depuis Claude ou ChatGPT. Les garde-fous restent
   côté serveur, donc ils tiennent quel que soit le client.

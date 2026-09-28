# Ce qu'il faut comprendre pour défendre le projet

Notes courtes, dans l'ordre où le jury risque de creuser. Chaque point renvoie au code.

1. **Filtres durs avant pertinence** (`matching.filtres_durs`). Le consentement, la zone, la langue et la concurrence sont des règles de code,
   appliquées avant tout classement. Une donnée inconnue ne satisfait jamais une obligation. Même principe que dans Persei : un spectre hors domaine
   force « non certifiable », quoi que dise le modèle.
2. **Sortie structurée en flux** (`parser_llm.analyser_flux`). Le schéma JSON garantit la *forme*, pas la *vérité*. D'où la seconde validation
   (`valider`) : vocabulaire fermé, extraits présents dans le texte. Les objets complets sont extraits du JSON en cours d'écriture (`_objets_complets`),
   affichés comme provisoires, puis remplacés par la version validée.
3. **Abstention** : l'équivalent produit d'une détection hors domaine. Sans preuve pour la compétence principale, on ne propose rien.
4. **Trois niveaux de preuve** : déclarée (offre) > mentionnée (présentation qui *affirme* une offre, sans négation, besoin ni clientèle) > textuelle (hors catalogue).
   Seule une preuve déclarée peut donner « forte ».
5. **L'expression la plus longue l'emporte** (`taxonomy.concepts_dans`). « Sécurité informatique » compte comme cybersécurité, pas comme informatique générale. C'est ce qui rend les exclusions fiables.
6. **Symétrie Bourse ⇔ recherche**. La Bourse d'un membre relance la recherche de chaque besoin publié, restreinte à ce membre. Mêmes
   règles, donc les deux vues ne peuvent pas se contredire (propriété testée sur tous les membres).
7. **Machine à états avec rôles** (`store.TRANSITIONS`). Chaque transition précise *qui* peut la déclencher : destinataire, initiateur ou participant.
   Toute violation renvoie 403 ou 409, même par appel direct à l'API.
8. **Versions et obsolescence**. Un besoin modifié incrémente sa version. Les résultats affichés portent une empreinte de critères : si elle diffère,
   l'interface grise les résultats et bloque les actions.
9. **Server-Sent Events**. Un flux HTTP unidirectionnel (`text/event-stream`) : le serveur pousse les événements du journal, et le navigateur
   se reconnecte seul. C'est ce qui rend la scène à deux membres « vraie ».
10. **Évaluation honnête**. Référence avec les *mêmes filtres* ; jeux séparés (régression, développement, réservé exécuté une fois) ; dénominateurs explicites.
    La circularité (même auteur pour les cas et le moteur) reste la limite principale.
11. **MCP (piste)**. Exposer les fonctions du Club comme outils utilisables depuis Claude ou ChatGPT. Les garde-fous restent côté serveur, donc ils tiennent quel que soit le client.

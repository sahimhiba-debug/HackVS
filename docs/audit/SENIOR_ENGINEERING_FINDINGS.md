# Findings — audit d'ingénierie senior

> Source : [SENIOR_ENGINEERING_AUDIT.md](SENIOR_ENGINEERING_AUDIT.md) (2026-09-30, commit `43fd20d`). Gravité :
> CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL. Les LOW ne sont pas corrigés automatiquement. État : OUVERT,
> EN COURS, FERMÉ (commit), DÉCISION (en attente d'un choix documenté), ACCEPTÉ (risque connu, borné, expliqué).
> Aucun CRITICAL trouvé.

| ID | Gravité | Domaine | Problème | Risque | Action | État |
|---|---|---|---|---|---|---|
| F01 | HIGH | Frontière IA | `POST /moi/demandes` écrit un `BESOIN` interprété par le modèle sans confirmation du membre, puis lance la détection ; aucun écran ne l'appelle | l'état dépend du modèle sur ce chemin ; la parité ON/OFF ne le couvre pas ; contredit « l'IA propose, le membre confirme » | décider : fermer la route (branche détection retirée du parcours) ou exiger la confirmation ; test rouge d'abord | DÉCISION |
| F02 | HIGH | Documentation | `docs/ARCHITECTURE.md` décrit le produit d'avant le pivot ; ADR 0004 cite `intelligence/activation.py`, supprimé | le jury passe du pitch au code et trouve un autre système | écrire `docs/architecture/ARCHITECTURE.md` du système réel ; marquer l'ancien document et l'ADR 0004 comme historiques | OUVERT |
| F03 | MEDIUM | Tests (infra E2E) | la sonde de disponibilité interroge `/api/stage` (404) : 20 s d'attente aveugle par serveur, jamais de détection d'un serveur qui ne démarre pas | E2E lents ; échecs trompeurs si le serveur tombe au démarrage | sonder une route Club Pulse ; échouer clairement si le serveur n'est jamais prêt ; test rouge d'abord | OUVERT |
| F04 | MEDIUM | Tests | `test_mutation_sans_session_ou_avec_session_falsifiee` forge la signature en remplaçant 2 caractères par `00` : identique à la vraie 1 fois sur 256 | test non déterministe (échec isolé observé) | forger une signature toujours différente | OUVERT |
| F05 | MEDIUM | Domaine / journal | `ACCORD` / `RETRAIT` ont deux sens (essai, finalité) distingués par une clé ; charges `dict[str, Any]` ; 31 types d'événements en chaînes libres, sans catalogue | un lecteur futur sans filtre mélange deux consentements ; schéma implicite | (a) test de séparation des deux sens ; (b) catalogue des événements dans l'architecture ; typage des charges reporté | OUVERT |
| F06 | MEDIUM | Architecture | `Banc` : 1 033 lignes, 80 méthodes, 12 responsabilités | coût de relecture ; risque de régression lors de modifications | ne pas découper avant la démo ; plan de découpage (ADR), à faire derrière les tests existants | ACCEPTÉ (reporté) |
| F07 | MEDIUM | Rejeu | aucun test ne garde le rejeu des types récents (`RECHERCHE_*`, `PASSE_JURE`, `APPEL_IA` avec clé) au redémarrage | régression silencieuse possible | test de redémarrage couvrant ces types (la propriété tient aujourd'hui, vérifiée) | OUVERT |
| F08 | MEDIUM | API / sécurité | 14 routes membre ou console sans écran (branche détection, accueil, profil, reçus) ; 3 sans test HTTP (`capacites/{f}/consentement`, `notes/…/partager`, `profil/proposer`) ; pas de balayage IDOR | surface morte mais ouverte ; contrôle d'accès vérifié au cas par cas seulement | (a) balayage IDOR de toutes les routes membre à identifiant ; (b) classement DELETE / KEEP / DEPRECATE documenté | OUVERT |
| F09 | MEDIUM | Sécurité / démo | `/acces` limité par IP (10/min) | en salle derrière un NAT, 10 activations par minute pour tout le public | décider : clé par code tenté (comme le QR juré) ou plafond relevé ; test d'abord | DÉCISION |
| F10 | MEDIUM | Tests | 3 tests de `test_frontiere_textes.py` ne vérifient que l'absence des noms, pas la présence du texte utile | passeraient si le texte était perdu | ajouter l'assertion « le sens reste » ; contre-épreuve | OUVERT |
| F11 | MEDIUM | Architecture | 39 modules hérités chargés par `app.main` (ancien prototype, plateforme de décision, adaptateur réseau), servis derrière drapeau ; ils portent les benchmarks publiés | un lecteur ne sait pas ce qui est le produit | KEEP (benchmarks), frontière documentée dans l'architecture | OUVERT |
| F12 | LOW | Domaine | partager deux fois la même proposition d'une note ajoute deux fois l'intérêt | doublon dans le profil | non corrigé (LOW) ; noté | ACCEPTÉ |
| F13 | LOW | Performance | `candidats` reconstruit toutes les offres à chaque appel (1 087 appels, 459 ms à froid) | lent à plus grande échelle | mesuré ; pas d'optimisation avant besoin | ACCEPTÉ |
| F14 | LOW | Types | 12 `# type: ignore` (surtout `union-attr` sur `Ask` optionnel) | faible | réduire en passant | ACCEPTÉ |
| F15 | LOW | Architecture | cycle `adaptateurs.club.cycle ↔ reseau` contourné par imports locaux | lisibilité (ancien produit) | noté | ACCEPTÉ |
| F16 | LOW | Documentation | ~20 documents `docs/` de périodes différentes sans statut « historique » | confusion | index avec statut de chaque document | OUVERT |
| F17 | LOW | Rejeu | interrupteur IA, réglages (budgets, plafonds) et fichiers de patrons hors journal | rejeu égal seulement à configuration égale | écrire le contrat (« même version du moteur » inclut la configuration) | OUVERT |
| F18 | LOW | Déterminisme | `plateforme/pipeline.py:107` : repli `date.today()` | ancien produit ; hors Club Pulse | noté | ACCEPTÉ |
| F19 | INFO | Sécurité | console sans jeton = requête locale ; sûr tant que les en-têtes de proxy ne sont crus que de 127.0.0.1 | déploiement derrière un proxy mal configuré | documenter : jeton obligatoire hors machine locale | OUVERT |
| F20 | INFO | Produit | Club Pulse n'est servi qu'en `HACKVS_MODE=demo` | — | le dire dans l'architecture | OUVERT |
| F21 | INFO | Tests | Hypothesis absent ; propriétés couvertes par oracle à graines | — | évaluer l'apport avant tout ajout de dépendance | OUVERT |
| F22 | INFO | Mutation | 102 survivants classés ; campagne GitHub #4 en cours | — | confirmer le run | EN COURS |

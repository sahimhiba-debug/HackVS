> **HISTORIQUE — rédigé avant le registre des capacités (28–30.09.2026).** Conservé pour la traçabilité des décisions ; ne décrit PAS le produit actuel, et ses chiffres, routes et noms de fichiers peuvent être faux aujourd'hui. État actuel : [README](/README.md) · [index de la documentation](/docs/README.md).

# Hypothèses et questions terrain

Statuts : **H** hypothèse · **I** inconnu critique · **C** confirmé (voir RESEARCH.md).

## Inconnues critiques (elles changent la direction)

| # | Inconnue | Impact si différente | Comment la lever |
|---|---|---|---|
| I1 | Brief exact du challenge Club des Affaires | Tout le cadrage | Lire le brief dès sa publication ; le demander à l'accueil le 3.10 |
| I2 | Règles sur le travail préparé avant l'événement | Reconstruire sur place ou réutiliser `prototype/` | Règlement ; question directe aux organisateurs |
| I3 | Données fournies (liste des membres ? profils ? consentement ?) | Mode réel possible ou non | Question au porteur du challenge |
| I4 | Durée du pitch et critères du jury | Choix de la version 1, 3 ou 5 minutes (DEMO.md) | Règlement / briefing d'ouverture |
| I5 | Langue : public bilingue FR/DE ? | Interface et taxonomie à rendre bilingues | Question au porteur |

## Hypothèses produit

| # | Hypothèse | Statut | Test sur place (5 min, sans données personnelles) |
|---|---|---|---|
| H1 | Entre deux événements, un membre a parfois un besoin précis et ne sait pas qui, dans le Club, peut y répondre | H | « La dernière fois que vous avez cherché un fournisseur ou un partenaire, avez-vous pensé au Club ? Qu'avez-vous fait ? » |
| H2 | Les membres préfèrent une introduction consentie à un contact direct | H | « Préférez-vous être contacté directement ou recevoir une demande que vous acceptez ? » |
| H3 | Les membres accepteraient de décrire leur offre en 2 ou 3 lignes | H | « Accepteriez-vous de remplir 3 lignes sur ce que vous proposez et cherchez ? » |
| H4 | Le Club (secrétariat) pourrait animer une bourse des besoins | H | Question au porteur du challenge |
| H5 | Les exposants ne sont pas membres par défaut et ne doivent pas être sollicités sans accord | H | Porteur du challenge |
| H6 | Les outils actuels du Club sont surtout événementiels (invitations, courriels) | I | « Comment le Club communique-t-il avec vous entre deux événements ? » |
| H7 | La réciprocité (« il cherche aussi quelque chose que vous offrez ») augmente l'acceptation | H | Non testable avant usage réel |
| H8 | Un membre préfère parfois publier un besoin sans son nom (anonymat jusqu'à acceptation) | H | « Publieriez-vous un besoin sous votre nom devant les autres membres ? » |
| H9 | Un membre qui voit un besoin qui lui correspond proposera son aide (logique « Givers Gain ») | H | « Si un membre cherchait exactement ce que vous faites, voudriez-vous le savoir ? » |
| H10 | Les membres emploient des formulations variées, parfois en allemand | H (plausible en Valais) | Recueillir 5 besoins réels formulés librement (sans données personnelles) → nouveaux cas d'évaluation |

## Hypothèses techniques

| # | Hypothèse | Risque | Mitigation |
|---|---|---|---|
| T1 | Claude transforme correctement des besoins réels en critères de la taxonomie | Mauvaise compréhension, latence | Validation par le code + repli sur les règles ; `python -m eval.run_eval --claude` dès qu'une clé est disponible |
| T2 | 35 concepts + recherche hors catalogue suffisent pour une démo crédible | Jeu réservé : 3 fausses abstentions sur 14 (paraphrases) | Claude pour les paraphrases (à mesurer) ; ajout de concepts = édition de `taxonomie.json` |
| T4 | Le schéma de sortie structurée est accepté tel quel par l'API Claude | Jamais soumis à l'API réelle | `scripts/verifier_claude.py` dès qu'une clé existe ; repli automatique et affiché |
| T3 | La dictée vocale fonctionne dans la salle | Wi-Fi saturé, micro | Démo principale au clavier ; la dictée est un bonus |

## Questions à poser sur place (liste courte à imprimer)
1. Quel est le brief exact et qui le porte côté Club ?
2. Peut-on utiliser un prototype préparé avant l'événement ? Doit-on le déclarer ?
3. Aurons-nous des données (même anonymisées) ou seulement des données fictives ?
4. Combien de temps de pitch, et quels critères pour le jury ?
5. Comment les membres se contactent-ils aujourd'hui entre deux événements ?
6. Un membre accepterait-il d'être sollicité par un autre membre qu'il ne connaît pas ? Sous quelles conditions ?

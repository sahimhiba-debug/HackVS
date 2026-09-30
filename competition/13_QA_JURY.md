> ⛔ **OBSOLÈTE — produit d'avant le pivot, ne pas présenter.** Ce dossier décrit l'ancien produit (« intelligence relationnelle »), pas le registre des capacités. La réécriture du pitch est en cours (équipe) ; voir `TODO-DEMO.md`.

# 13 — Questions difficiles du jury (45) : RÉPONSE · PREUVE · LIMITE

Règle : répondre en une ou deux phrases, montrer la preuve si on la demande, dire la limite avant qu'on la trouve.
Trois jurés simulés : **B** (business), **T** (technique), **P** (produit).

## Juré business
| # | Question | Réponse | Preuve | Limite |
|---|---|---|---|---|
| B1 | Pourquoi pas LinkedIn ? | LinkedIn est un réseau ouvert ; le Club est un réseau fermé, dont la valeur naît de ses événements et dont les contacts ne sont pas publics. Nous faisons vivre les relations nées au Club, avec l'accord des deux. | 20_COMPETITIVE_ANALYSIS ; scène étape 4 | Nous ne remplaçons pas LinkedIn ; un membre peut y aller en parallèle. |
| B2 | Pourquoi pas Swapcard ? | Swapcard recommande très bien pendant l'événement. Nous n'avons pas trouvé dans ses documents publics de suivi fondé sur une preuve ni de plans chiffrés pour l'organisateur ; nous pourrions nous y ajouter comme couche de suivi. | AUDIT_CHAMPIONNAT § 7 (sources) | Pages éditeur non consultables depuis notre environnement ; absence de preuve ≠ preuve d'absence. |
| B3 | Pourquoi pas Grip ? | Grip apprend de comportements à grande échelle (« 16 stratégies »). Nous ne cherchons pas à mieux prédire un clic : nous exigeons une preuve d'aide et nous savons nous taire. | AUDIT § 7 [G1] | Grip a des données et des clients ; nous n'en avons aucun. |
| B4 | Et Brella, qui a une offre pour les associations ? | C'est le concurrent le plus proche sur « toute l'année ». Notre différence défendable : abstention, silence justifié, consentement relationnel testé, vue réseau pour l'organisatrice. | AUDIT § 7 [B2] | Nous n'avons pas testé Brella. |
| B5 | Pourquoi le Club l'utiliserait-il entre deux événements ? | Pour trois moments précis : un besoin publié reçoit une réponse prouvée ; une raison nouvelle déclenche une relance ; l'organisatrice choisit ses introductions du mois en connaissant leur prix. | VALEUR_METIER § 1 ; scène | Fréquence réelle de ces moments non mesurée. |
| B6 | Quelle action nouvelle pour l'organisatrice ? | Voir ce qui se défait (îlots, ponts fragiles), choisir une introduction en connaissant son effet, et savoir quand ne rien faire. | Tour de contrôle (T) ; scène étapes 8–10 | Aucune organisatrice réelle ne l'a utilisée. |
| B7 | Combien de travail humain évite-t-il ? | Nous ne le chiffrons pas : nous n'avons pas mesuré la pratique actuelle. Le pilote mesure les minutes de l'organisatrice. | VALEUR_METIER § 3, § 6 | Pas de chiffre d'économie. |
| B8 | Combien cela coûte ? | Une machine, aucune clé d'API, aucune licence propriétaire ; l'IA générative est optionnelle. | 16_LIMITATIONS ; C14 | Coût d'hébergement et de maintenance non chiffré. |
| B9 | Comment mesurez-vous votre avantage ? | Par un pilote de trois mois : part des membres avec une relation actuelle, introductions acceptées, relances acceptées ou ignorées, décisions de l'organisatrice réalisées. Critère d'échec fixé d'avance. | VALEUR_METIER § 6 | Aucun résultat de pilote à ce jour. |
| B10 | Et si les membres ne remplissent rien ? | Le système se tait — honnête mais sans valeur. C'est notre premier indicateur : moins d'un volontaire sur cinq qui publie un besoin = échec. | VALEUR_METIER § 5 | Risque principal du produit. |
| B11 | Qui paie ? | Hypothèse : le Club, comme service à ses membres. | — | Non validé avec le Club. |
| B12 | Pourquoi vous croire, sur des données fictives ? | Nous ne demandons pas de croire à une valeur : nous montrons des mécanismes, vérifiables, et un protocole pour mesurer la valeur. | 14_PROOF_LEDGER | La valeur reste à prouver. |
| B13 | Qu'avez-vous fait pendant le hackathon ? | Seulement ce qui a un commit après le début officiel ; le reste est préparé avant, et nous le disons. | CONTRIBUTIONS_HACKATHON | Règlement officiel pas encore reçu. |
| B14 | Le Club a-t-il validé le besoin ? | Non. C'est une hypothèse de produit (INFERRED). | C21 | À confronter au brief exact. |
| B15 | Quelle est la suite ? | Pilote, rôles authentifiés, mesure réelle de l'IA générative, puis intégration à une plateforme d'événement existante. | 17_ROADMAP | Rien de cela n'est commencé. |

## Juré technique
| # | Question | Réponse | Preuve | Limite |
|---|---|---|---|---|
| T1 | Pourquoi pas de simples embeddings ? | La ressemblance n'est pas l'aide : un moteur par ressemblance aurait proposé quelqu'un à Chantal, sans raison. Nous exigeons un extrait qui prouve l'aide. | Scène étape 9 ; SYNTHETIC_BENCHMARK (similarité : 67,7 % de ponts) | Une couche sémantique locale existe en option ; elle ne décide pas seule. |
| T2 | Pourquoi un solveur ? | Parce que les décisions collectives (une soirée, les introductions du mois) ont des contraintes et des objectifs en conflit ; un tri individuel envoie tout le monde vers les mêmes personnes. | AD-05 ; benchmark : 95,7 % de ponts | Front approché ; par introduction, pas d'avantage en membres servis. |
| T3 | Pourquoi un graphe ? | Pour voir ce qu'aucun membre ne voit seul : îlots, ponts fragiles, qui serait coupé si une relation s'éteint. | Scène étape 8 ; contrefactuel ; AD-01 | NetworkX en mémoire : pas au-delà de quelques milliers de membres. |
| T4 | Pourquoi le LLM n'agit-il pas directement ? | Il peut halluciner et être manipulé par injection ; le consentement et les refus sont du code testé. Le LLM peut proposer des critères ; le code les revalide ; il ne décide jamais. | AD-09 ; `parser_llm.valider` | Aucun modèle mesuré à ce jour. |
| T5 | Où est l'IA générative, alors ? | Pas dans la démo. Elle a une place mesurable : comprendre des phrases très libres (22 échecs des règles sur 112 cas) et mettre un diagnostic en mots sous contrôle d'un vérificateur de fidélité. | GENAI_RESEARCH ; banc G1/G2 | NON EXÉCUTÉ faute de modèle accessible. |
| T6 | Que faites-vous quand il n'y a pas assez de preuves ? | Nous nous abstenons, et nous disons pourquoi et ce qui changerait la décision. | C01, C23, C24 | Le système paraît souvent silencieux. |
| T7 | Et si les données sont fausses ? | Chaque proposition cite sa source (déclaré / déduit) et son âge ; un profil ancien est signalé ; une offre déclarée reste une déclaration. | Cartes « Inconnu » ; SYNTHETIC_BENCHMARK (20 % d'offres périmées simulées) | Aucune vérification externe des déclarations. |
| T8 | Et des preuves contradictoires ? | Un refus ancien n'écrase pas une relation devenue vivante ; un terme ambigu avec des indices contradictoires reste une incertitude affichée. | `test_adversarial_reseau.py` ; `test_compilateur_besoin.py` | Contradictions de sens complexes non détectées. |
| T9 | Votre benchmark est-il représentatif ? | Non, et nous le disons : réseaux générés, vérité définie par nous. Il sert à attraper des idées fausses — nous y avons trouvé nos propres biais. | 06_BENCHMARKS ; FAILURES n° 8, 47 | Ne prédit pas la valeur réelle. |
| T10 | Que se passe-t-il à 10 000 membres ? | Recherche : 904 ms à 5000 membres générés. Diagnostic : 24 s à 1000, plus que linéaire : il faudrait le calculer en tâche de fond et passer à une base serveur. | 06_BENCHMARKS § 3 | Jamais mesuré à 10 000. |
| T11 | Comment protégez-vous les membres ? | Invisible par défaut, coordonnées après double accord, refus jamais contourné, qui refuse n'est ni nommé ni compté, entrées bornées. | `test_securite_api.py`, `test_scene.py` ; FAILURES n° 19–22 | Pas d'authentification réelle des membres. |
| T12 | Comment savez-vous que l'explication dit vrai ? | Elle est recalculée indépendamment et comparée à la décision ; une fausse explication injectée est attrapée. | C06 | Couvre les explications affichées, pas tout le texte libre. |
| T13 | La démo est-elle truquée ? | Non : les étapes appellent les mêmes fonctions que l'application, rejouées à l'identique, testées dans un vrai navigateur en CI. | AD-12 ; `test_e2e_scene.py` | Le monde est fictif et l'horloge simulée. |
| T14 | Qu'est-ce qui casse aujourd'hui ? | Paraphrases très libres, diagnostic lent au-delà de 500 membres, aucun envoi réel, pas de rôles authentifiés. | 16_LIMITATIONS | — |
| T15 | Déploiement réel ? | Un conteneur, SQLite, sans dépendance externe ; à passer sur une base serveur et une authentification avant tout pilote. | 04_ARCHITECTURE | Jamais déployé publiquement. |

## Juré produit
| # | Question | Réponse | Preuve | Limite |
|---|---|---|---|---|
| P1 | En une phrase ? | Ce système transforme des rencontres ponctuelles en réseau vivant. | Pitch | — |
| P2 | Qu'est-ce que le jury doit retenir ? | Il propose seulement ce qu'il peut prouver — et il sait s'abstenir. | Scène étape 9 | — |
| P3 | Pourquoi le système se tait-il autant ? | Une relance sans raison fatigue un réseau ; 17 paires n'avaient rien de nouveau à se dire. | C05 | Taux de silence réel inconnu. |
| P4 | N'est-ce pas frustrant pour un membre ? | Il reçoit une abstention claire et ce qui changerait la réponse, plutôt qu'un mauvais contact. | Scène étape 9 | Non testé avec des membres. |
| P5 | Comment un membre remplit-il son profil ? | Une phrase ; le système propose, il valide ; invisible par défaut. | Scène étape 1 | Proposition parfois imparfaite (visible à l'écran). |
| P6 | Et le démarrage à froid ? | Un nouveau membre est trouvable dès son premier besoin ou sa première offre validée ; sa réciprocité est dite prouvée ou non. | C17 ; `test_explications.py` | Sans rien de publié, rien ne se passe. |
| P7 | Pourquoi l'organisatrice ne choisit-elle pas simplement ? | Elle choisit : le système montre l'effet et le prix de chaque plan, et refuse ce qui n'a pas de preuve. | Scène étape 8 ; C09 | — |
| P8 | Les soirées ne suffisent-elles pas ? | Elles créent l'essentiel des rencontres ; nous l'avons mesuré : enchaîner les soirées épuise les rencontres utiles (9 → 1 → 0). Nous aidons entre elles. | C24 ; EXP-N | Simulation fictive. |
| P9 | Que voit un membre, que voit l'organisatrice ? | Un membre voit ses propres relations et propositions ; l'organisatrice voit des chiffres expliqués (tour de contrôle). | Tour de contrôle ; AD-07 | Rôles non authentifiés dans le prototype. |
| P10 | Pourquoi pas une app de rencontres pour dirigeants ? | Nous avons commencé par la mise en relation ; un réseau professionnel qui ressemble à une application de rencontres n'était probablement pas le brief. | 10_PITCH (humour de réserve) | — |
| P11 | Et si Markus refuse ? | La demande est close, rien n'est révélé à Sophie au-delà du refus, et aucune table de soirée ne les réunira. | AD-08 ; FAILURES n° 26 | — |
| P12 | L'IA peut-elle écrire le message d'introduction ? | Possible plus tard (G5), sous contrôle : aucune donnée privée ajoutée ; évaluation humaine nécessaire. | GENAI_RESEARCH G5 | Non construit. |
| P13 | Qu'est-ce qui est fait, simulé, non mesuré ? | Faits enregistrés (fictifs), simulations étiquetées, valeur réelle non mesurée — l'écran final le dit. | Scène étape 11 | — |
| P14 | Accessibilité, mobile ? | La scène fonctionne à 390 px sans défilement horizontal (testé) ; clavier : flèches, R, T, Entrée sur une relation. | `test_e2e_scene.py` | Pas d'audit d'accessibilité complet. |
| P15 | Pourquoi vous, pourquoi maintenant ? | Parce que la Foire crée chaque année les rencontres, et qu'entre deux éditions rien ne les fait vivre ; nous avons un prototype qui le prouve mécanisme par mécanisme. | Démo | Hypothèse de besoin non validée avec le Club. |

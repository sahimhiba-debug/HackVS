# Audit contradictoire — Championship Sprint (29.09.2026)

But : trouver toutes les raisons pour lesquelles un jury d'ingénieurs pourrait trouver la solution ordinaire, fragile,
inutile ou mal démontrée — avant lui. Chaque ligne dit ce qui est prouvé, et par quoi.

## 1. Ce qui est déjà BANAL (ne pas le vendre comme une différence)
| Élément | Pourquoi c'est banal | Conséquence pour le pitch |
|---|---|---|
| Recommander « qui rencontrer » | Swapcard, Grip, Brella le font à grande échelle (§ 7) | Ne jamais ouvrir sur « une IA qui recommande » |
| Communauté toute l'année | Brella (offre associations), Swapcard (engagement toute l'année) | Pas un argument |
| Annuaire, messagerie, prise de rendez-vous | Standard | Pas montré |
| Voir les isolés, les intermédiaires, les ponts | Outils d'analyse de réseaux organisationnels (PARTNER CPRM, Polinode, Gephi) | « Nous voyons le réseau » n'est PAS une différence ; seule l'est la suite : agir avec preuve, consentement, silence et prix de chaque plan |
| Tableaux de bord « connexions / rendez-vous » | Swapcard, Grip (analytique organisateur) | Nos indicateurs ne se vendent pas comme tableau de bord |

## 2. Ce qui est RÉELLEMENT implémenté (code + test exécuté)
Mémoire événementielle datée ; état de chaque relation dérivé de faits ; recherche fondée sur des preuves citées ;
abstention ; double accord avant tout partage de coordonnées ; refus jamais contourné (règle unique + test sur toutes
les paires) ; relances seulement avec raison nouvelle ; budget d'attention ; diagnostic du réseau (8 phénomènes) ;
front de plans (approché) ; contrefactuel « si cette relation disparaît » ; décision humaine enregistrée puis
confrontée aux faits ; vérificateur de fidélité pour tout texte généré. **258 tests** (exécutés, verts),
reproductibilité des benchmarks vérifiée en CI.

## 3. Ce qui est seulement SIMULÉ ou SYNTHÉTIQUE
| Élément | Nature | À dire |
|---|---|---|
| Tous les membres, rencontres, besoins | FICTIFS | Affiché en permanence sur la scène |
| Horloge de la scène | simulée | « Date simulée » dans la barre |
| Effet des plans, disparition d'une relation | SIMULATION (actions supposées acceptées) | Étiquette SIMULATION sur chaque tuile |
| Benchmarks (interventions, Pareto, extinction…) | SYNTHÉTIQUES, vérité définie par nous | Jamais présentés comme une valeur réelle |
| Envoi de messages, authentification | ABSENTS | Dit dans les limites |
| Interprétation par IA | **NON EXÉCUTÉE** (aucun modèle accessible) | Retirée de la démo (règles vérifiables, dit à l'écran) ; aucun chiffre d'IA |
| Utilité pour un vrai Club | **NON MESURÉE** | Protocole de pilote (VALEUR_METIER.md) |

## 4. Ce qui est ORIGINAL mais difficile à comprendre
| Élément | Risque | Décision |
|---|---|---|
| Front de Pareto à 4 axes, « cohésion robuste » (2-arête-connexité) | jargon | Scène B : **deux** plans, deux chiffres (« reliés ensemble » / « résistent à la perte d'une relation ») ; le reste en annexe |
| Silence justifié (17 silences pour 1 relance) | ressemble à « il ne fait rien » | Scène C : montrer le silence **à côté** de la seule relance fondée, avec sa preuve |
| Refus motivé (refus_motives) | invisible si tout va bien | Scène C : trois demandes plausibles refusées, chacune avec sa raison |
| Boucle prévu / réalisé | exige des mois de données réelles | Annexe seulement (aucune décision réelle à confronter) |

## 5. Ce qui IMPRESSIONNE techniquement sans valeur démontrée pour le Club
| Élément | Verdict |
|---|---|
| Serveur MCP (stdio + HTTP), plateforme de décision générique avec certificats et rejeu, expérience « scellée » | Hors démo. Réponse aux questions d'architecture seulement |
| Modèle sémantique local de 2,2 Go | Hors démo (désactivé en CI) |
| Calcul exact par arbre des ponts + LCA | Annexe technique ; dire « exact et rapide », pas comment |
| Invitations par flot de coût minimum | Ne bat une règle simple que pour les petites soirées (7 victoires, 13 égalités sur 20) ; annexe |
| 9 pages web, 94 routes, 58 documents | **Risque de dispersion** : UNE page en démo (`/demo/stage`), le reste en coulisse |

## 6. Ce qui peut ÉCHOUER pendant la présentation
| Risque | Probabilité | Parade (vérifiée ?) |
|---|---|---|
| Réseau de la salle absent | moyenne | Tout tourne en local, aucune dépendance externe (vérifié : scène sans réseau) |
| Modèle d'IA absent ou lent | **certaine aujourd'hui** | La démo n'utilise AUCUNE IA générative (décision du 29.09) : risque éliminé ; ancienne parade : si un modèle est configuré, repli visible sur les règles en cas d'échec (testé avec un double) |
| Double clic, retour arrière, rafraîchissement | faible | Verrou serveur, rejeu déterministe (testé) |
| Texte sous la ligne de flottaison sur le projecteur | moyenne | Captures 1440×900 vérifiées ; A1 et B1 longues → dire l'essentiel, faire défiler |
| Question « c'est quoi le groupe robuste ? » | haute | Lexique affiché sous les plans |
| Navigateur qui plante | faible | Vidéo de secours (réenregistrée sur l'histoire en 11 étapes) |
| Jury : « vous ne faites que dire non » | haute | L'histoire montre d'abord une proposition acceptée, une relance fondée, une opportunité, un réseau réuni ; l'abstention vient APRÈS |

## 7. Matrice de différenciation (sources et limites)
**Limite de méthode** : les pages des éditeurs sont bloquées par le réseau de notre environnement (29.09.2026). Les
constats viennent d'extraits de moteur de recherche et de sites tiers ; aucun produit n'a été testé. **L'absence d'une
capacité dans ces sources n'est pas une preuve d'absence.**

| Capacité | Swapcard | Grip | Brella | Outils ONA (PARTNER, Polinode) | Nous (prototype) |
|---|---|---|---|---|---|
| Recommandation de personnes par IA | Oui : profil public, activité dans l'application, intérêts [S1] | Oui : « 16 stratégies » d'apprentissage, signaux de comportement [G1] | Oui : fondée sur l'intention déclarée [B1] | Non (analyse) | Oui, sans apprentissage : preuves citées du profil |
| Communauté toute l'année | Oui [S2] | Données qui se reportent d'un événement au suivant [G1] | Oui, offre associations [B2] | — | Oui (mémoire datée) |
| Explication « pourquoi cette personne » visible | Non documenté dans nos sources | Non documenté | Non documenté ; un comparatif tiers signale que ce point doit être demandé aux éditeurs [T1] | — | Oui, testée contre la décision (test de mutation) |
| Abstention (« personne ne convient ») | Non documenté | Non documenté | Non documenté | — | Oui, testée (20 scénarios de décision + scène) |
| Analytique organisateur | Connexions, rendez-vous acceptés [S3] | Taux de rendez-vous réalisés [G2] | Non documenté dans nos sources | Isolés, intermédiaires, cartographie [O1] | Phénomènes du réseau + contrefactuel + plans chiffrés |
| Actions proposées à l'organisateur, avec leur prix | Non documenté | Règles de mise en relation par segment [G2] | Non documenté | Non documenté | Oui : plans en conflit mesuré, aucun « meilleur » imposé |
| Suivi post-événement fondé sur une raison prouvée | Non documenté | Non documenté | Non documenté | — | Oui (relance ou silence, compté) |
| Consentement relationnel (double accord, refus jamais contourné) | Non documenté en détail | Non documenté | Non documenté | — | Oui, invariant testé sur toutes les paires |
| Échelle réelle, clients, données | Oui (plateforme commerciale) | « 70 M de recommandations par an » (déclaré) [G1] | Oui | Oui | **Non** : aucune donnée réelle, aucun client |

Sources : [S1] https://app.swapcard.com/event/revolve/product/UHJvZHVjdF82ODE4ODI= ; [S2] https://www.swapcard.com/features/event-networking ;
[S3] https://www.g2.com/products/swapcard/reviews (synthèse de recherche) ; [G1] https://www.grip.events/products/event-matchmaking et
https://www.grip.events/news/how-to-improve-your-event-networking-with-ai-matchmaking ; [G2] https://youreventkit.com/tools/grip/ (synthèse de recherche, non vérifiée à la source) ;
[B1] https://www.brella.io/event-matchmaking ; [B2] https://www.brella.io/associations ;
[T1] https://getperspective.ai/blog/best-conference-networking-matchmaking-software-2026-compared ;
[O1] https://visiblenetworklabs.com/partner-cprm/ et https://www.polinode.com/.

**Ce que nous pouvons dire honnêtement** : « Les plateformes existantes excellent à recommander des rencontres pendant
l'événement. Nous n'avons pas trouvé, dans leurs documents publics, de suivi fondé sur une preuve, d'abstention
explicite ni de plans d'organisation chiffrés avec leur prix. Nous ne prétendons pas qu'ils n'existent pas. »
**Ce que nous ne devons jamais dire** : « unique », « personne ne fait », « meilleur que Swapcard ».

## 8. Décisions prises par cet audit
1. Démo = une page, UNE histoire en 11 étapes (du nouveau membre au réseau qui change, puis l'abstention) — FAIT (`/demo/stage`) ; remplace la version en trois scènes (trop de démonstrations concurrentes).
2. L'IA n'apparaît que là où elle doit prouver quelque chose (comprendre une phrase libre) ; sans modèle, la scène le dit.
3. Le pitch n'ouvre pas sur l'IA ni sur « le réseau vu d'en haut », mais sur la question du Club : que reste-t-il des
   rencontres un mois plus tard, et que doit faire l'organisatrice ce mois-ci ?
4. Tout le reste (MCP, décision générique, scellé, invitations) passe en annexe technique.

# 13 — Questions du jury (44 questions difficiles)

Format : **Q** · **Réponse** · *Preuve* · Limite · Relance possible. Règle : ne jamais citer un chiffre absent de
`15_CLAIMS.md` ; dire « nous ne savons pas » quand c'est le cas.

## BUSINESS
1. **Q : Qui paie, et pourquoi ?** — Le Club, parce que la valeur d'une adhésion annuelle se joue entre les événements :
   des suites concrètes justifient le renouvellement. *Hypothèse de produit (INFERRED), non mesurée.* Limite : aucun
   entretien avec des membres réels. Relance : « Comment le vérifieriez-vous ? » → pilote après un seul événement,
   mesurer suites acceptées et renouvellements.
2. **Q : Quel indicateur montrerait le succès ?** — Suites acceptées après un événement, introductions acceptées,
   opportunités déclarées, membres isolés reliés. *Tous calculés par le prototype sur données fictives.* Limite :
   aucune donnée réelle.
3. **Q : Pourquoi le Club ne prendrait-il pas simplement un outil existant ?** — Il peut ; notre couche s'y ajoute
   (mémoire, suivis prouvés, consentement relationnel). *20_COMPETITIVE_ANALYSIS.* 
4. **Q : Quelle est la première chose à déployer ?** — Après le prochain événement : proposer seulement les suites
   justifiées, en silence pour le reste. Une seule fonction, mesurable en un mois.
5. **Q : Combien de membres faut-il pour que ça marche ?** — Nous l'avons mesuré sur données fictives : un petit club
   épuise vite les rencontres utiles sans besoins nouveaux (le club de démonstration n'a plus rien à proposer à la
   3e soirée, et le système s'abstient). *docs/EVALUATION.md §6 ter.* C'est pourquoi la boucle des besoins compte.

## TECHNIQUE
6. **Q : Pourquoi un solveur plutôt qu'un classement ?** — Un classement optimise une personne à la fois ; le solveur
   optimise le réseau sous contraintes (budget par membre, consentement, pas de répétition) et PROUVE l'optimum.
   *C10–C11, AD-03.* Limite : plus lent (0,4 s), et il perd sur la réciprocité face à une méthode dédiée.
7. **Q : Pourquoi un graphe temporel ?** — Pour savoir quand une relation s'éteint, ce qui s'est passé après et quand un
   suivi est dû ; tout l'état est rejouable. *AD-01.*
8. **Q : Pourquoi pas une base de graphe ?** — 16 à 150 membres : NetworkX en mémoire suffit ; complexité non méritée.
9. **Q : Comment garantissez-vous une seule source de vérité ?** — Le magasin des introductions est projeté dans la
   mémoire, jamais dupliqué ; nous avons trouvé et corrigé ce défaut. *FAILURES #1, AD-02.*
10. **Q : Comment gérez-vous le temps ?** — Une seule horloge, injectée partout ; nous avons découvert deux horloges
    incohérentes grâce à un test rouge. *FAILURES #4–5.*
11. **Q : Que se passe-t-il à 5 000 membres ?** — Non mesuré. Le solveur a tourné sur 150 membres générés ; au-delà,
    il faudrait découper par événement ou par communauté. Nous ne le prétendons pas testé.
12. **Q : Comment testez-vous ?** — Plus de 100 tests, lint, CI ; scénarios à attendu fixé avant exécution ; tests
    rouges écrits avant les corrections ; tests de mutation sur les explications. *C06, C13, C15.*

## IA
13. **Q : Pourquoi avez-vous besoin d'IA ?** — Pour comprendre le langage (besoins, profils) et proposer ; pas pour
    décider des permissions ou des règles. Sans clé, le produit fonctionne entièrement (règles locales + IA locale).
    *C14, AD-04.*
14. **Q : Pourquoi pas simplement des embeddings ?** — Ils rapprochent des domaines voisins sans pouvoir citer de preuve
    (« droit maritime » ≈ « droit des sociétés »). Nous utilisons un vocabulaire contrôlé et citons les phrases
    exactes ; l'IA locale ne fait que proposer. *AD-11.*
15. **Q : Avez-vous testé Claude ou Apertus ?** — Non contre leurs API réelles : aucune clé dans notre environnement.
    Testés contre des serveurs simulés ; la passerelle les déclare « configurés », jamais « vérifiés ». *C14.*
16. **Q : L'IA peut-elle être manipulée par un profil malveillant ?** — Les profils sont traités comme des données non
    fiables ; une injection est signalée et ne change pas le classement ; aucune règle n'est levée par un texte.
17. **Q : Y a-t-il des agents ?** — Des rôles à responsabilité démontrable (compilateur, solveur, validateurs, critique,
    gardien, médiateur), déterministes ; pas d'agent pour faire joli. *AD-09.*

## CONFIDENTIALITÉ
18. **Q : Comment protégez-vous les relations privées ?** — Le lien entre un intermédiaire et un candidat n'est jamais
    révélé ; la présentation est proposée d'abord à l'intermédiaire. *C04, FAILURES #2.*
19. **Q : Qui voit les coordonnées ?** — Personne, avant l'accord des deux ; le prototype n'en stocke aucune. *C02.*
20. **Q : Un nouveau membre est-il exposé ?** — Non : invisible par défaut, recommandable seulement s'il le choisit. *C17.*
21. **Q : Et les besoins sensibles (céder son entreprise) ?** — Un brouillon ou un besoin clos n'est jamais utilisé ; nous
    avons trouvé cette fuite et l'avons corrigée à la source. *C18, FAILURES #6.*
22. **Q : Faites-vous du scoring de personnes ?** — Non. Nous mesurons des phénomènes du réseau (ponts, isolement), jamais
    la « valeur » d'un membre.
23. **Q : Que voit l'administration du Club ?** — Dans la scène, une vue de démonstration ; en production, la vue du Club
    doit rester agrégée (le prototype affiche déjà des agrégats sans noms dans la vue du Club).

## DONNÉES
24. **Q : Que se passe-t-il quand les données sont fausses ?** — Les preuves sont citées, les profils anciens et les
    preuves déduites sont signalés comme inconnues ; une affirmation périmée fait échouer la validation (scénario S17).
25. **Q : Vos données sont-elles réelles ?** — Non. Tout est fictif ou synthétique, et étiqueté comme tel.
26. **Q : Et le démarrage à froid ?** — Un nouveau membre est servi par ses déclarations validées ; nous ne prétendons
    jamais avoir appris une préférence non observée.

## BENCHMARK
27. **Q : Quelle est la limite de votre benchmark ?** — Données générées ; vérité latente définie par nous ; 60 membres ;
    5 réseaux. Il montre des compromis, pas une performance réelle. *C10–C12 (SYNTHÉTIQUE).*
28. **Q : Pourquoi votre méthode serait meilleure qu'un classement ?** — Elle ne l'est pas partout : elle gagne sur les
    ponts, les membres servis et les isolés, perd sur la réciprocité. Nous le montrons.
29. **Q : Comment savez-vous que le benchmark n'est pas biaisé en votre faveur ?** — Nous y avons trouvé un biais
    (candidats différents) et l'avons corrigé, ce qui a réduit notre avantage. Mêmes candidats, même budget, vérité
    cachée à toutes les méthodes ; testé. *FAILURES #8.*
30. **Q : Le front de Pareto n'est-il pas artificiel ?** — Sur nos données de démo, il était dégénéré (1 point) : nous
    l'avons dit, puis construit un benchmark à conflits contrôlés (3 à 10 points). *C12.*

## ÉTHIQUE
31. **Q : Comment évitez-vous les bulles ?** — L'optimiseur valorise les ponts entre communautés ; « ami d'ami » et
    « similarité » enferment (mesuré, SYNTHÉTIQUE).
32. **Q : Ne favorisez-vous pas les membres populaires ?** — Un budget par membre limite la sollicitation ; notre
    benchmark de soirée ne discrimine pas ce biais. Depuis : budget d'attention (3 relances par membre et par jour, le reste
    reporté) testé sur un cas construit ; et sur le benchmark d'intervention, la méthode « relier les plus connectés » garde
    un léger avantage sur la taille du plus grand groupe : nous ne revendiquons rien de plus.
33. **Q : Que se passe-t-il si l'utilisateur refuse ?** — Le refus est un fait enregistré ; la relance n'est jamais
    reproposée ; aucune pénalité. *test_relance_refusee_n_insiste_pas.*

## UX
34. **Q : N'est-ce pas trop complexe pour un membre ?** — Le membre voit une boîte d'actions possibles maintenant ; la
    complexité reste dans le moteur.
35. **Q : Pourquoi le système se tait-il autant ?** — Parce qu'une relance sans raison est du bruit ; le silence est
    compté et affiché.
36. **Q : Et sur mobile ?** — Vérifié à 390 px (scène et espace membre), sans débordement.

## DÉPLOIEMENT / COÛT
37. **Q : Combien cela coûte ?** — Sans IA externe : le coût d'un petit serveur ; avec une IA externe, un coût par
    analyse que nous n'avons pas mesuré (aucune clé). Nous ne donnons pas de chiffre non mesuré.
38. **Q : Comment le Club pourrait-il le déployer ?** — Conteneur unique (Dockerfile), données du Club importées avec
    autorisation ; authentification des membres à ajouter (non implémentée).
39. **Q : Qu'est-ce qui manque pour la production ?** — Authentification, canal d'envoi réel, import des données réelles,
    vérification d'une IA externe, tests avec de vrais membres. *16_LIMITATIONS.*
40. **Q : Où sont les données hébergées ?** — Où le Club le décide : tout tourne en local ; Apertus (modèle suisse) est
    prévu en option, non vérifié.

## CONCURRENCE / FUTUR
41. **Q : Pourquoi pas LinkedIn ?** — Voir 20_COMPETITIVE_ANALYSIS (réseau fermé, annuel, consentement, événements).
42. **Q : Swapcard et Brella ont une communauté 365 jours.** — Oui ; ce n'est pas notre différenciation. La nôtre : ce
    qui se passe après la recommandation, prouvé et consenti.
43. **Q : Qu'avez-vous fait pendant les 24 heures ?** — À préciser honnêtement le jour J : le prototype a été préparé
    avant l'événement ; ne jamais présenter ce travail comme réalisé pendant Hack VS.
44. **Q : Et après ?** — Pilote sur un événement réel du Club, avec consentement ; mesurer suites acceptées et
    introductions ; puis micro-cercles et projets. *17_ROADMAP.*

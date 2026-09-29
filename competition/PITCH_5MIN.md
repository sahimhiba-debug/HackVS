# Pitch — 5 minutes (texte exact ; plus de place pour la méthode et le déploiement)

**[0:00]** À la Foire, on échange une carte. On se dit « on se rappelle ». Un mois plus tard, on ne sait plus pourquoi.
Le Club des Affaires organise les moments où l'on se rencontre. Mais ce qui se passe après dépend de la mémoire de chacun.

**[0:25]** Des plateformes existantes savent déjà recommander des contacts par IA et animer une communauté toute
l'année. Nous ne refaisons pas cela. Nous nous sommes posé une autre question : qu'est-ce qui fait qu'une rencontre
devient quelque chose ? Trois choses : une raison documentée de se reparler, un accord des deux côtés, et quelqu'un
qui regarde le réseau entier, pas seulement une personne.

**[0:55 — démo complète `/demo/stage`, 12 étapes]** (voir 09_DEMO_SCRIPT, version longue)

**[3:05 — méthode]** Tout ce que vous avez vu est calculé en direct ; la démonstration se rejoue à l'identique.
Les explications ne sont pas rédigées à part : elles sont recalculées et comparées à la décision par des tests —
nous avons même injecté de fausses explications pour vérifier que les tests les attrapent.
Sur un benchmark synthétique, à budget égal et avec les mêmes candidats pour tous, notre optimiseur crée plus de ponts
et sert plus de membres que 5 autres méthodes ; il perd sur la réciprocité face à la méthode qui ne vise qu'elle.
Nous avions d'abord publié un écart plus flatteur ; en attaquant notre propre benchmark, nous avons trouvé le biais
et corrigé le chiffre. Au total, 26 défauts réels trouvés et corrigés, chacun avec son test.

**[4:05 — déploiement]** Tout tourne sur une seule machine, sans clé d'API ; une IA externe est une option, jamais une
dépendance. Consentement, confidentialité et autorisations sont du code testé. Le Club pourrait commencer par une
seule chose : après chaque événement, proposer les suites justifiées — et se taire le reste du temps.

**[4:40]** Notre système a un défaut : il se tait souvent. Dans une démo, c'est angoissant. Dans un réseau, c'est une
qualité.
Chaque événement crée des rencontres. Nous faisons en sorte qu'elles deviennent quelque chose.

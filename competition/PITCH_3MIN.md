# Pitch — 3 minutes (texte exact)

<!-- Règle : tout chiffre cité ici doit être prouvé (scripts/validate_competition_claims.py le vérifie). -->

**[0:00 — diapositive 1]**
À la Foire, on échange une carte. On se dit : « on se rappelle ». Un mois plus tard, on ne sait plus pourquoi.
Le Club des Affaires organise les moments où l'on se rencontre. Mais ce qui se passe après dépend de la mémoire de chacun.
Nous avons construit la mémoire du réseau.

**[0:25 — passage en démo, `/demo/stage`]**
Voici un réseau fictif de 16 membres. Des rencontres ont eu lieu, mais le réseau reste fait d'îlots.
Sophie vient d'arriver. Elle ne connaît personne. Elle décrit son entreprise ; le système propose un profil, elle le
corrige. Par défaut, elle est invisible : c'est elle qui choisit d'être recommandée.
Elle écrit : « Je cherche un partenaire pour développer mon activité en Allemagne. »
Le système ne lui donne pas une liste de noms. Deux personnes, avec leurs preuves. Markus peut l'aider — et, dans
l'autre sens, Markus cherche ce que Sophie produit. Ce qui reste inconnu est écrit en toutes lettres.
Il ne donne pas le numéro de Markus. Et si Sophie demande un distributeur au Japon, il s'abstient :
nous avons préféré une abstention à une hallucination.
Sophie demande une introduction. Markus peut refuser. Il accepte : les coordonnées sont partagées maintenant, pas avant.
Ils se rencontrent. Dix jours plus tard — là où les cartes de visite finissent dans un tiroir — le système cherche
une raison réelle de se reparler. Il en trouve une, prouvée. Pour les 17 autres paires : rien de nouveau, donc silence.
Notre système a un défaut : il se tait souvent. Dans une démo, c'est angoissant. Dans un réseau, c'est une qualité.
Markus donne suite ; une affaire est en cours. Et le réseau voit ce qu'aucun membre ne voit seul : une présentation,
proposée d'abord à Markus, et un petit cercle de 5 personnes. Avant d'agir, on simule : 2 groupes n'en forment plus
qu'un. L'humain décide.

**[2:05 — diapositive benchmark]**
Nous avons mesuré, pas affirmé. Sur un benchmark synthétique, à budget égal, face à 5 autres méthodes, notre
optimiseur crée plus de ponts entre communautés et sert plus de membres. Il perd sur la réciprocité face à la méthode
qui ne vise qu'elle — et nous le montrons. Nous avons aussi trouvé et corrigé 26 défauts en essayant de casser notre
propre système.

**[2:30 — diapositive architecture]**
Tout tourne sans aucune clé d'API. Les règles de consentement et de confidentialité sont du code testé, pas une
consigne donnée à une IA. Aucune coordonnée n'est jamais affichée.

**[2:48 — diapositive de fin]**
Chaque événement crée des rencontres. Nous faisons en sorte qu'elles deviennent quelque chose.

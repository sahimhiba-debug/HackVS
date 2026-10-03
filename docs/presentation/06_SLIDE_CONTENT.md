# 06 — Contenu des slides, une par une

Pour le deck visuel, produit côté design à partir de ce fichier, dans le design system figé
(`docs/design/DESIGN_SYSTEM.md` : rouge `#CD2128`, encre `#141923`, Plus Jakarta Sans, JetBrains Mono pour les
reçus et références, tuile-sigle). Règle : **une slide, une idée, jamais un paragraphe.** Les cartons sont fond noir,
une phrase en Plus Jakarta Sans 800, rien d'autre — pas de logo, pas de numéro.

Les captures d'écran sont des **écrans réels** du produit, prises samedi pendant la répétition
(`04_DEMO_RUNBOOK.md` § 6). Aucune maquette présentée comme un écran. Si une planche du design system est utilisée,
elle porte la mention « maquette ».

| # | Temps | Titre (jamais affiché tel quel, c'est un repère) | Ce qu'on voit | L'idée (une seule) | Notes design |
|---|---|---|---|---|---|
| 1 | 0:00 | La carte | une vraie carte de visite, à plat, plein écran, lumière naturelle ; nom et entreprise **fictifs** (Sophie — tisanes de plantes alpines) ; pas de logo Club Pulse, pas de titre | « On s'appelle. » | photo, pas d'illustration ; fond neutre ; aucun élément d'interface |
| 2 | 0:35 | Et après ? (1/3) | fond noir, deux mots centrés : **Et après ?** | la question | Plus Jakarta Sans 800, blanc ; cette slide est réutilisée telle quelle en 8 et 17 |
| 3 | 0:45 | Carton DEMANDE | fond noir : **Ce qui se passe entre deux événements.** | annonce de l'acte | carton, une phrase |
| 4 | 1:00 | Le vide | fond clair ; deux dates sur une ligne de temps (« Foire du Valais » — « prochain événement du Club ») ; entre les deux, rien | entre deux événements, rien | pas de texte explicatif ; les deux dates sont génériques, sans année ni mois |
| 5 | 1:30 | Le oui | fond clair ; un seul mot, encre, très grand : **Oui.** ; en dessous, petit, `--secondary` : « (pas « on s'appelle ») » | ce qui change tout | — |
| 6 | 2:00 | Carton CONTRIBUTION | fond noir : **L'homme qui disait oui.** | annonce du film | 2 s, puis noir, puis le film (lancé à la main) |
| — | 2:00–5:21 | *Le film* | — | — | hors deck |
| 7 | 5:21 | Dernier plan | le dernier plan du film, figé (ou capture) | respiration | 3 s |
| 8 | 5:26 | Et après ? (2/3) | = slide 2 | la question, sans réponse | — |
| 9 | 5:36 | Carton ESSAI | fond noir : **Le même geste. Dans le vrai produit.** | annonce de la démo | — |
| 10 | 5:45 | L'Établi (réel) | **écran réel** : `/etabli`, carte « Accueillir une délégation d'acheteurs germanophones », statut « il manque une pièce », minibus en pointillés « Débloquerait 1 capacité », date « vendredi 09.10 », mention FICTIF | la demande existe pour de vrai | plein écran, sans cadre ni légende ; la slide est le secours de l'écran vivant (`etabli-1-manque.png`) |
| 11 | 6:20–11:00 | *Démo live* | l'Établi et le téléphone, en direct (écran réel : pas d'anneau, une bordure verte — D-PRES-2) ; en secours les captures du runbook § 6 dans l'ordre : `tel-1-demande`, `tel-1b-proposition`, `etabli-2-peut`, `tel-2-recu`, `etabli-3-retrait` (« un composant n'est plus disponible », rôle masqué), `tel-4-decouverte` (le passe découverte, Foire 2026), `suivi-1` | fiction → réalité | captures affichées seulement sur plan B (touche `B`, une par repère : 7 repères) |
| 11S | 10:40 | **Suivi** (Foire 2026) | **écran réel** : `/suivi`, capture `suivi-1.png` (scripts/capturer_presentation.py) — tuiles « demandes envoyées », « réponses oui < 3 », « invités ayant contribué < 3 », bandeau « monde de démonstration » | « Vous nous avez dit que le Club ne sait jamais où en sont les partenariats. Voilà l'écran. » | secours de l'écran vivant ; les chiffres sont ceux du monde de démonstration, et c'est écrit sur la capture |
| 12 | 11:00 | Carton RÉSULTAT | fond noir : **Ce qui est prouvé. Rien de plus.** | annonce des preuves | — |
| 13 | 11:10 | Trois preuves | trois lignes, encre, sans icône : **Le reçu** — daté, référencé, révocable. · **Le journal** — le serveur meurt, le monde revient. · **Le retrait** — un rôle, jamais un nom. | la techno comme preuve de sérieux | une ligne par preuve ; pas de sous-texte |
| 14 | 11:40 | Les chiffres du gel | cinq chiffres, grands, JetBrains Mono ; sous chacun, trois mots : `[GEL]` tests · `[GEL]` parcours de bout en bout, aussi réseau coupé · `[GEL]` / `[GEL]` mutants tués, survivants tous classés (cœur du registre) · **< 1 s** geste → écran commun (mesuré) · **0** écriture sans geste (lire ne capte rien) | mesuré, pas supposé | **à remplir après le tag `gel-demo`** depuis `PREUVES.md` ; valeurs au 01.10 pour calibrer la mise en page : 1 359 · 22 · 1 229 / 1 327 · 229–704 ms · 0. Chiffres `essai.py` : NE PAS les mettre ici (pré-fix, non classés) |
| 15 | 12:30 | L'IA | trois lignes, encre, centrées : **L'IA propose.** **Les règles vérifient.** **Le membre décide.** | la place de l'IA | aucun logo, aucun « propulsé par » |
| 16 | 13:00 | Ce qu'on a mesuré | une ligne mono, petite : « Apertus · swiss-ai/Apertus-v1.5-70B · API d'inférence CSCS » ; en dessous, un seul chiffre grand : **1 / 26** ; légende : « propositions justes du premier coup — 26 cas écrits avant l'appel » ; en bas, `--secondary` : « Interrupteur. Même état du Club, IA allumée ou éteinte — testé. » | la vérité sur l'IA, et le filet (c'est aussi la justification de la démo IA éteinte, D-PRES-1) | ce chiffre est la mesure du 01.10 (CLAIMS n° 39) ; si une nouvelle mesure est faite avant le gel, remplacer par la plus récente **et** dater ; ne jamais arrondir vers le haut |
| 17 | 13:40 | Carton REÇU | fond noir : **Et après, maintenant, il se passe quelque chose.** | la réponse | la phrase apparaît en deux temps si le deck le permet : « Et après ? » puis « , maintenant, il se passe quelque chose. » |
| 18 | 13:50 | La carte et le reçu | la carte de la slide 1, à gauche, même cadrage ; à droite, **le reçu réel** du téléphone (`tel-2-recu.png`, recadré sur la carte du reçu : titre, `valable`, « donné le 06.10 · jusqu'au 09.10 · référence … », référence longue telle quelle) | même geste, cette fois il engage | **D-PRES-3 : capture de l'écran réel, aucune maquette.** Le format `R-xxx-x` reste réservé aux planches et au film |
| 18b | 14:15 | **Les six prochains mois** (Foire 2026) | étiquette « prévu ensuite » ; entonnoir **Foire → Passe découverte (90 jours, sans être membre) → Membre (y compris à 200 km)** ; au clic : les cinq ajouts déjà dans le prototype, testés (Suivi · Clôture de reçu · Anonymat sous 3 · Passe découverte · Le Club cherche) ; au clic : « Pilote de 45 jours avec 50 volontaires : janvier – mi-février 2027 · Interreg France-Suisse : dépôt avant le 12.03.2027 » | « Un club qui prouve sa valeur toute l'année recrute, y compris à 200 kilomètres. » | la date Interreg vient du cadrage de l'équipe, à vérifier avant dépôt (`docs/roadmap/FINANCEMENT_JURIDIQUE.md`) ; rien n'y est présenté comme fait sauf les cinq ajouts |
| 19 | 14:25 | Phrase finale | fond noir : **La Foire crée la rencontre. Club Pulse crée l'après.** | — | 3 s ; le dernier membre — « Si Jean-Marc dit oui, c'est que c'est oui. », le carton de fin du film mot pour mot — se dit, il ne s'écrit pas |
| 20 | 14:40 | Noir | noir | — | puis, pour les questions : slide 21 |
| 21 | Q&R | Repères pour les questions | tuile-sigle + « Club Pulse » + une ligne : « Club des Affaires · Foire du Valais » ; en bas, petit : « monde de démonstration fictif · chaque affirmation : docs/audit/CLAIMS.md » | — | reste affichée pendant les questions |

## Rappels pour le deck

- **Pas de slide « équipe », pas de slide « architecture ».** Une seule slide d'avenir, la 18b (ajoutée le 03.10 à la
  demande de l'équipe), étiquetée « prévu ensuite » ; le reste du prévu-ensuite se dit à l'oral et dans les réponses
  (`07_QA_JURY.md`). Le détail est dans `docs/roadmap/`.
- Les slides avec des chiffres mesurés sont la 14 et la 16. La 11S montre des décomptes du **monde de démonstration**
  (écrit sur la capture) ; la 18b ne porte que des durées et une date de calendrier, aucun résultat.
- La slide 14 reste **vide** (gabarit avec `[GEL]`) tant que le tag `gel-demo` n'est pas posé. Elle est remplie
  vendredi soir depuis `PREUVES.md`, et le commit du dépôt est noté en bas de la slide, en mono, petit.
- Les mentions « FICTIF » et les dates simulées restent visibles sur toutes les captures : c'est une preuve d'honnêteté,
  pas un défaut.
- Aucune capture de l'ancien prototype (`docs/captures/*`, dossier `competition/`, en quarantaine).

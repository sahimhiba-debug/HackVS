# 10 — Pitch : récit, choix, storyboard

## Le récit (avant les diapositives)
PROBLÈME → INSIGHT → TENSION → NOUVELLE APPROCHE → PREUVE → DÉMO → IMPACT → VISION

- **Problème.** La Foire crée des rencontres. Un mois plus tard, on ne sait plus pourquoi on s'était parlé.
- **Insight.** La valeur d'un réseau n'est pas dans la liste des membres, mais dans ce qui se passe *entre* deux rencontres.
- **Tension.** Les outils existants savent recommander des contacts et animer une communauté. Recommander plus, c'est
  facile ; savoir *quand* se taire, *qui* peut présenter qui sans rien divulguer, et ce que le réseau entier y gagne, non.
- **Approche.** Une intelligence relationnelle : chaque rencontre devient un fait daté, chaque relance a une preuve,
  chaque introduction un double accord, et l'on simule le réseau avant d'agir.
- **Preuve.** Démo en direct, calculée par le moteur ; benchmark synthétique contre cinq méthodes ; 26 défauts trouvés
  en attaquant notre propre système.
- **Impact / vision.** Le Club garde ses moments forts ; nous leur donnons une suite toute l'année.

## Ouvertures candidates (5) — choix argumenté
1. « Imaginez que demain la Foire disparaisse de votre agenda… » — forte, mais hypothétique et un peu théâtrale.
2. « Levez la main si vous avez déjà dit “on se rappelle” à la Foire. » — interactive, risquée devant un jury.
3. « On échange une carte. On se dit “on se rappelle”. Un mois plus tard, on ne sait plus pourquoi. » — concrète.
4. « Le Club organise les moments où l'on se rencontre. Mais ce qui se passe après dépend de la mémoire de chacun. » — le cœur du brief (version initiale « personne n'organise ce qui se passe après » écartée : invérifiable et injuste envers le Club).
5. « Un réseau, c'est ce qui se passe entre deux rencontres. » — juste, mais abstraite.

**Retenue : 3 puis 4.** La plus claire, la moins théâtrale, directement reliée au challenge.

## Humour (une seule touche)
- Retenue : « Notre système a un défaut : il se tait souvent. Dans une démo, c'est angoissant. Dans un réseau, c'est
  une qualité. » — auto-référentielle, et elle prépare le moment intelligent (le silence justifié).
- Réserve (Q&R « pourquoi pas du matchmaking ? ») : « Nous avons commencé par le matchmaking. Puis nous avons compris
  qu'un réseau professionnel qui ressemble à une application de rencontres n'était probablement pas exactement le brief. »
- Écartées : toute plaisanterie sur les membres, la région, la confidentialité ou un groupe de personnes.

## Le moment intelligent
Étape 9 de la scène : dix jours après les rencontres, **une** relance fondée sur une preuve, et **17 silences**.
Puis l'étape 5 : pour une demande sans preuve (le Japon), le système s'abstient. Phrase : « Nous avons préféré une
abstention à une hallucination. »

## Le moment humain
Sophie ne connaît personne. Le système ne lui donne pas une liste : il lui donne **une bonne prochaine action** —
demander une introduction à Markus, qui peut l'aider et qu'elle peut aider en retour.

## Fins candidates (10)
1. « Nous ne voulons pas construire une meilleure liste de membres. Nous voulons un réseau qui ne s'oublie pas entre deux Foires. »
2. **« Chaque événement crée des rencontres. Nous faisons en sorte qu'elles deviennent quelque chose. »**
3. « Le Club crée les moments. Nous leur donnons une suite. »
4. « Une rencontre ne vaut que par sa suite. »
5. « Nous ne recommandons pas plus. Nous recommandons mieux — et nous savons nous taire. »
6. « Ce n'est pas un annuaire. C'est la mémoire du Club. »
7. « Entre deux Foires, le réseau continue. »
8. « Moins de cartes de visite, plus de suites. »
9. « La Foire crée les rencontres. Nous construisons ce qui leur survit. »
10. « Un réseau vivant, c'est un réseau qui se souvient. »

**Retenue : 2** — concrète, sans grandiloquence, identique à la fin de la vidéo (cohérence). Variante courte : 3.

## Storyboard (deck minimal — la démo est le cœur)
| # | Objectif | Message | Visuel | Parole | Temps | Transition | À retenir |
|---|---|---|---|---|---|---|---|
| 1 | Créer l'image | Les rencontres s'oublient | Une phrase sur fond blanc : « on se rappelle » | Ouverture 3 + 4 | 0:00–0:25 | « Voici Sophie. » | Le problème, en une image |
| 2 | Passer au produit | — | **Démo en direct `/demo/stage`** | voir 09_DEMO_SCRIPT | 0:25–2:05 | fin de l'étape 12 | Une boucle complète, calculée |
| 3 | Prouver | Nous avons mesuré, pas affirmé | Tableau benchmark (6 méthodes) avec « SYNTHÉTIQUE » | « Plus de ponts, plus de membres servis ; il perd sur la réciprocité, et nous le montrons. » | 2:05–2:30 | — | Méthode honnête |
| 4 | Rassurer | Déployable, confidentiel | Architecture en 7 blocs | « Tout tourne sans clé d'API. Aucune coordonnée n'est affichée. » | 2:30–2:48 | — | Crédible pour le Club |
| 5 | Finir | — | Phrase de fin | Fin 2 | 2:48–3:00 | — | La phrase à répéter |

Architecture en 10 secondes (diapositive 4) :
`MEMBRE → INTELLIGENCE RELATIONNELLE → GRAPHE TEMPOREL + PREUVES → OPTIMISATION → CONSENTEMENT / POLITIQUE → ACTION (simulée) → MÉMOIRE`

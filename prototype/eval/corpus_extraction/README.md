# Corpus d'extraction FR / DE / suisse allemand — énoncés FICTIFS et étiquettes-or

> Écrit et committé SEUL, **avant tout appel à un modèle** (le commit horodaté est la preuve de méthode).
> Aucune donnée réelle : aucun nom de personne, aucune entreprise, aucun contact. Les villes et la Foire du Valais
> (2–11.10.2026) sont le décor du monde de démonstration.

`corpus.json` : 50 énoncés de membres du Club, chacun avec son étiquette-or. Découpage **dev** (20 énoncés : on peut
ajuster les prompts sur eux) / **test** (30 énoncés : UNE seule passe, après gel des prompts, résultats publiés tels
quels, même mauvais).

## Étiquette-or

```json
{"id": "t08", "split": "test", "langue": "fr|de|gsw", "registre": "sms|poli|oral",
 "couverture": ["quantite", "creneau_relatif", "..."], "texte": "…",
 "or": {"issue": "EXTRACTION|FALLBACK|RIEN",
        "pieces": [{"type": "lieu|objet|competence", "piece": "salle", "quantite": {"places": 14},
                    "creneau": {"jour": "2026-10-09", "debut": "13:00", "fin": "18:00"} | null,
                    "validite": "offre|retrait"}]}}
```

- **issue** : `EXTRACTION` (au moins une pièce du membre est extractible), `FALLBACK` (énoncé ambigu : l'attendu est
  le FORMULAIRE, pas une extraction devinée — `pieces` vide), `RIEN` (injection ou hors-sujet : rien à extraire).
- **piece** (le « slot ») : vocabulaire canonique des pièces des patrons — `salle`, `minibus`, `traduction`,
  `traiteur`, `atelier`, `camion_frigorifique`, `logistique`, `formation`, `recrutement`, `cybersecurite`,
  `public_germanophone`, `public_alemanique`. Un lieu de dégustation, un caveau, une salle de conférence → `salle` ;
  un van, un bus, un transporteur de personnes → `minibus`.
- **quantite** : uniquement une valeur ÉCRITE EN CHIFFRES ou en mots exacts qui est un attribut d'un patron
  (`places`). Une approximation (« une vingtaine ») → `{}`. Un nombre qui n'est pas une quantité (date, numéro de
  stand, heure) → jamais une quantité. Une quantité sous le minimum d'un patron reste extraite : juger de sa validité
  est le travail du code, pas de l'extraction.
- **creneau** : relatif à l'horloge de démonstration, **mardi 06.10.2026** (« demain » = 07.10 ; mercredi 07.10,
  jeudi 08.10, vendredi 09.10, samedi 10.10, dimanche 11.10). Moments : matin 08:00–12:00 ; après-midi 13:00–18:00 ;
  soir 18:00–22:00 ; toute la journée 08:00–18:00 ; heures dites → ces heures. Une heure de 1 à 7 dite sans « du matin » (« de deux heures à cinq heures ») est
  une heure de l'après-midi (14:00–17:00). Jour sans moment → `debut` et `fin`
  à `null`. Heure de début seule → `fin` à `null`. Aucun jour dit → `creneau` à `null`.
- **validite** : `offre` (le membre propose) ou `retrait` (il ne peut plus : « je ne peux plus prêter la salle »).
- **Seulement les pièces DU MEMBRE** : ce qu'un tiers ferait (« ma collègue peut… ») n'est jamais extrait — le modèle
  ne décide pas qu'une autre personne accepte. Les ressources de son organisation (« deux personnes de chez nous »)
  sont les siennes.

## Mesures (fixées ici, avant toute exécution)

Par langue et au total, sur dev et sur test séparément :
- **issue** : exactitude, et matrice gold × prédit (EXTRACTION / FALLBACK / RIEN) ;
- **taux de fallback** : part des énoncés où la sortie montrée est la forme déterministe ;
- **précision / rappel par champ**, sur les pièces appariées par (`type`, `piece`) : `type+piece`, chaque attribut de
  `quantite`, `creneau.jour`, `creneau.debut`, `creneau.fin`, `validite` ;
- **extraction exacte** : l'énoncé entier est juste (issue + ensemble des pièces avec tous leurs champs) ;
- **latences** : médiane, p90, max (par appel, `AppelIA.latence_ms`) ; nombre d'essais (1 nouvel essai au plus) ;
- **échecs listés VERBATIM** : texte, or, sortie montrée, statut (`MODEL_CALLED` / `CACHE_REPLAY` / `FALLBACK_FORM`),
  raisons de rejet.
Un énoncé dont l'appel échoue (réseau, 5xx) compte comme FALLBACK, jamais comme succès ni comme exclu.

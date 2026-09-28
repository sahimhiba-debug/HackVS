# Résultats d'évaluation (exploratoire, données fictives)

Jeu : **reserve** · analyseur : **regles** · 14 cas · généré par `python -m eval.run_eval --jeu reserve`

Critères extraits conformes (type, valeur, obligatoire/souhaité ; critères interdits absents) : 0/0

| Mesure | Le Fil du Club | Mots-clés + mêmes filtres |
|---|---|---|
| succes@3 | 9/12 | 11/12 |
| violations | 0/14 | 4/14 |
| abstention_correcte | 11/14 | 13/14 |

Preuves citées retrouvées mot pour mot dans le profil : 19/19 (vrai par construction pour l'extraction par règles ; le garde-fou compte surtout si un LLM rédige un jour les explications).

Latence médiane : analyse 1.19 ms, recherche 8.06 ms (machine locale, 33 profils).

| Cas | Catégorie | Critères extraits | Moteur top 3 | ok | Référence top 3 | ok |
|---|---|---|---|---|---|---|
| r_agents_entree | paraphrase | texte_libre:Salut organise soirée clients faudrait agents gérer entrée | abstention | ✗ | p18, p01, p03 | ✓ |
| r_boutique | sans verbe de recherche | expertise:developpement_web | p26 | ✓ | p26 | ✓ |
| r_comptable_viege | contraintes | expertise:fiduciaire, langue:de, zone:Valais | p12 | ✓ | p16 | ✗ |
| r_photovoltaique | paraphrase | texte_libre:aimerait installer panneaux photovoltaïques toit cave | abstention | ✗ | p03, p22 | ✓ |
| r_droit_societes | familier | expertise:droit_affaires | p13 | ✓ | p13, p16 | ✓ |
| r_chariots | paraphrase | expertise:location_machines | p25 | ✓ | p25, p26 | ✗ (viol.) |
| r_epiceries_zurich | hors vocabulaire | texte_libre:vendre jus épiceries fines zurichoises idéalement, langue:de? | abstention | ✗ | p32, p15, p06 | ✓ |
| r_formateur_apprentis | absent | expertise:formation, expertise:logistique? | abstention | ✓ | p20, p01, p34 | ✗ (viol.) |
| r_traduire_site | paraphrase | expertise:traduction, langue:de | p16 | ✓ | p16, p26 | ✓ |
| r_chambres_froides | faux ami inverse | expertise:installation_froid | p03 | ✓ | p03, p02, p10 | ✗ (viol.) |
| r_allemand | allemand | expertise:transport_frigorifique, zone:Suisse alémanique | p01, p06, p05 | ✓ | p06, p01, p03 | ✗ (viol.) |
| r_veterinaire | absent | texte_libre:vétérinaire vaches | abstention | ✓ | abstention | ✓ |
| r_wifi | ambiguïté résolue | expertise:informatique | p11, p10 | ✓ | p11, p29 | ✓ |
| r_fiduciaire_pas_sion | négation de lieu | expertise:fiduciaire, zone:Valais | p12 | ✓ | p12 | ✓ |

**Limites** : cas écrits par l'auteur de la taxonomie (circularité), 33 profils fictifs, aucun utilisateur réel. Ces chiffres montrent que le mécanisme fonctionne comme conçu, pas qu'il est utile aux membres.

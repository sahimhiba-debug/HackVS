# Résultats d'évaluation (exploratoire, données fictives)

Jeu : **reserve4** · analyseur : **regles+semantique** · 20 cas · généré par `python -m eval.run_eval --jeu reserve4`


| Mesure | Le Fil du Club | Mots-clés + mêmes filtres |
|---|---|---|
| succes@3 | 4/15 | 7/15 |
| violations | 2/20 | 2/20 |
| abstention_correcte | 8/20 | 12/20 |

Preuves citées retrouvées mot pour mot dans le profil : 11/11 (vrai par construction pour l'extraction par règles ; le garde-fou compte surtout si un LLM rédige un jour les explications).

Latence médiane : analyse 92.28 ms, recherche 10.23 ms (machine locale, 37 profils).

| Cas | Catégorie | Critères extraits | Moteur top 3 | ok | Référence top 3 | ok |
|---|---|---|---|---|---|---|
| r4_yaourts_zurich | paraphrase | texte_libre:yaourts restent froids jusqu aux magasins zurichois | abstention | ✗ | p03, p20, p01 | ✗ (viol.) |
| r4_videurs | paraphrase | texte_libre:gens filtrer entrées lors fête | abstention | ✗ | p24, p15, p23 | ✗ |
| r4_vendangeurs | paraphrase | texte_libre:manque monde vendanges septembre | abstention | ✗ | p14 | ✓ |
| r4_toit_courant | paraphrase | texte_libre:aimerait produire propre électricité toit entrepôt | abstention | ✗ | abstention | ✗ |
| r4_visibilite_web | paraphrase | texte_libre:trouve internet faudrait améliorer visibilité | abstention | ✗ | p20, p18 | ✗ |
| r4_cartons | paraphrase | expertise:emballage | p27 | ✓ | p27, p16 | ✗ (viol.) |
| r4_retraite_pme | paraphrase | texte_libre:pars retraite deux ans sais pas confier | abstention | ✗ | p29, p24, p15 | ✓ |
| r4_employe_licencie | paraphrase | expertise:droit_travail | p13 | ✓ | p13 | ✓ |
| r4_de_logistik | allemand libre | texte_libre:jemanden Ware gekühlt nach bringt, zone:Suisse alémanique | abstention | ✗ | abstention | ✗ |
| r4_en_website | anglais | expertise:developpement_web | p26 | ✓ | abstention | ✗ |
| r4_en_security_event | anglais | texte_libre:need security staff for trade fair booth | abstention | ✗ | abstention | ✗ |
| r4_emprunt | paraphrase | texte_libre:voulons emprunter acheter nouveau pressoir | abstention | ✗ | abstention | ✗ |
| r4_ordis_lents | paraphrase | expertise:informatique | p11, p10 | ✗ (viol.) | p14, p22, p11 | ✓ |
| r4_video_promo | paraphrase | texte_libre:voudrait petit film présenter domaine réseaux | abstention | ✗ | p15, p28, p09 | ✓ |
| r4_dentiste | absent | texte_libre:dentiste employés | abstention | ✓ | abstention | ✓ |
| r4_electricien | faux ami | texte_libre:électricien refaire tableau électrique | abstention | ✓ | abstention | ✓ |
| r4_cuisinier | absent, faux ami | texte_libre:cuisinier saison | abstention | ✓ | abstention | ✓ |
| r4_camion_neuf | faux ami | expertise:transport_frigorifique | p09, p01, p02 | ✗ (viol.) | p06, p03, p34 | ✗ |
| r4_graphiste_logo | paraphrase | texte_libre:nouveau logo identité visuelle | abstention | ✗ | abstention | ✗ |
| r4_nettoyage | absent | expertise:immobilier_commercial | abstention | ✓ | p24, p15, p06 | ✗ |

**Limites** : cas écrits par l'auteur de la taxonomie (circularité), 37 profils fictifs, aucun utilisateur réel. Ces chiffres montrent que le mécanisme fonctionne comme conçu, pas qu'il est utile aux membres.

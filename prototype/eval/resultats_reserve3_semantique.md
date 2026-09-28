# Résultats d'évaluation (exploratoire, données fictives)

Jeu : **reserve3** · analyseur : **regles+semantique** · 20 cas · généré par `python -m eval.run_eval --jeu reserve3`


| Mesure | Le Fil du Club | Mots-clés + mêmes filtres |
|---|---|---|
| succes@3 | 5/15 | 7/15 |
| violations | 1/20 | 4/20 |
| abstention_correcte | 11/20 | 14/20 |

Preuves citées retrouvées mot pour mot dans le profil : 7/7 (vrai par construction pour l'extraction par règles ; le garde-fou compte surtout si un LLM rédige un jour les explications).

Latence médiane : analyse 82.27 ms, recherche 7.66 ms (machine locale, 37 profils).

| Cas | Catégorie | Critères extraits | Moteur top 3 | ok | Référence top 3 | ok |
|---|---|---|---|---|---|---|
| r3_bouteilles_au_frais | paraphrase | texte_libre:voulons bouteilles arrivent frais clients bâlois | abstention | ✗ | p02, p01, p03 | ✗ (viol.) |
| r3_gala | paraphrase | texte_libre:pourrait sécuriser accès soirée gala | abstention | ✗ | p18 | ✓ |
| r3_comptes | paraphrase (mot connu) | expertise:fiduciaire | p12 | ✓ | p12 | ✓ |
| r3_cueillette | paraphrase | texte_libre:bras cueillette abricots juillet | abstention | ✗ | p26 | ✗ |
| r3_energie | paraphrase | texte_libre:rendre bâtiment moins gourmand énergie | abstention | ✗ | p22 | ✓ |
| r3_google | paraphrase | texte_libre:aimerait apparaître Google tape abricots, zone:Valais | abstention | ✗ | p18, p26, p25 | ✓ |
| r3_mise_en_bouteille | paraphrase | expertise:boissons | p06, p28 | ✗ (viol.) | p06 | ✗ (viol.) |
| r3_ceder_pme | paraphrase (mot connu) | expertise:transmission_entreprise | p29 | ✓ | p23, p19, p13 | ✗ |
| r3_litige | paraphrase (mot connu) | expertise:droit_affaires | p13 | ✓ | p13, p23, p19 | ✓ |
| r3_de_website | allemand libre | texte_libre:jemanden Website auf übersetzt, langue:de | abstention | ✗ | abstention | ✗ |
| r3_en_accountant | anglais | texte_libre:are looking for accountant who speaks German | abstention | ✗ | abstention | ✗ |
| r3_veterinaire_equin | absent | texte_libre:vétérinaire équin | abstention | ✓ | abstention | ✓ |
| r3_dj | faux ami sémantique | texte_libre:soirée personnel | abstention | ✓ | p14 | ✗ |
| r3_pelouse | faux ami sémantique | texte_libre:tondre pelouses domaine | abstention | ✓ | p28 | ✗ (viol.) |
| r3_former_ia | mot connu | expertise:ia_donnees | p30 | ✓ | p05 | ✗ |
| r3_preter_argent | paraphrase | texte_libre:prêter argent agrandir cave | abstention | ✗ | p03 | ✗ |
| r3_stand_exposant | contrainte (exposant non inclus) | expertise:evenementiel | abstention | ✓ | p18 | ✗ |
| r3_assurance_camions | faux ami | expertise:assurance, expertise:transport_frigorifique? | p24 | ✓ | p06, p03, p34 | ✗ |
| r3_photo_culinaire | paraphrase | texte_libre:prendre photo plats carte | abstention | ✗ | p15 | ✓ |
| r3_plombier | absent, faux ami | texte_libre:plombier fuite cave | abstention | ✓ | p03 | ✗ (viol.) |

**Limites** : cas écrits par l'auteur de la taxonomie (circularité), 37 profils fictifs, aucun utilisateur réel. Ces chiffres montrent que le mécanisme fonctionne comme conçu, pas qu'il est utile aux membres.

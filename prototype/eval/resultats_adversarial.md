# Résultats d'évaluation (exploratoire, données fictives)

Jeu : **adversarial** · analyseur : **regles** · 20 cas · généré par `python -m eval.run_eval --jeu adversarial`

Critères extraits conformes (type, valeur, obligatoire/souhaité ; critères interdits absents) : 18/18

| Mesure | Le Fil du Club | Mots-clés + mêmes filtres |
|---|---|---|
| succes@3 | 13/13 | 12/13 |
| violations | 0/20 | 5/20 |
| abstention_correcte | 20/20 | 16/20 |

Preuves citées retrouvées mot pour mot dans le profil : 47/47 (vrai par construction pour l'extraction par règles ; le garde-fou compte surtout si un LLM rédige un jour les explications).

Latence médiane : analyse 1.51 ms, recherche 9.88 ms (machine locale, 37 profils).

| Cas | Catégorie | Critères extraits | Moteur top 3 | ok | Référence top 3 | ok |
|---|---|---|---|---|---|---|
| pref_basé_valais_livrer_geneve | préférence ≠ obligation | expertise:transport_frigorifique, implantation:Valais?, zone:Suisse romande | p02, p01, p05 | ✓ | p01, p33, p02 | ✓ |
| pref_langue_avant | préférence ≠ obligation | langue:de?, expertise:traduction, expertise:emballage? | p16 | ✓ | p16, p27 | ✓ |
| pref_fiduciaire_si_possible | préférence ≠ obligation | expertise:fiduciaire, langue:de? | p12 | ✓ | p12 | ✓ |
| neg_pas_installateur | négation | expertise:transport_frigorifique, zone:Suisse alémanique | p01, p06, p05 | ✓ | p06, p01, p03 | ✗ (viol.) |
| neg_pas_cyber | négation | expertise:informatique | p11 | ✓ | p11, p10 | ✗ (viol.) |
| neg_sous_aspect | négation | expertise:marketing | p15 | ✓ | p15, p05 | ✓ |
| spec_juriste_contrats_travail | spécialité | expertise:droit_travail | p13 | ✓ | p13, p19, p16 | ✓ |
| spec_cyber_iso | spécialité | expertise:certification_iso27001 | abstention | ✓ | p12 | ✗ |
| citation_client_pas_fournisseur | citation non probante | expertise:transport_frigorifique, zone:Suisse alémanique | p01, p06, p05 | ✓ | p06, p01, p03 | ✗ (viol.) |
| citation_garage | citation non probante | expertise:logistique, zone:Valais | p05, p01, p02 | ✓ | p34, p01, p24 | ✗ (viol.) |
| implantation_vs_zone_sion | implantation ≠ zone d'intervention | expertise:transport_frigorifique, zone:Suisse alémanique | p01, p06, p05 | ✓ | p06, p01, p03 | ✓ |
| implantation_exigee | implantation ≠ zone d'intervention | expertise:marketing, implantation:Suisse alémanique | abstention | ✓ | abstention | ✓ |
| zone_intervention_traducteur | implantation ≠ zone d'intervention | expertise:traduction, zone:Suisse alémanique | p16 | ✓ | p06, p01, p03 | ✗ |
| hors_taxo_apiculteur | hors vocabulaire | texte_libre:apiculteur polliniser vergers abricotiers | p35 | ✓ | p35 | ✓ |
| hors_taxo_distillation | hors vocabulaire | texte_libre:distiller abricots invendus eau-de-vie | p36 | ✓ | p36, p26 | ✓ |
| hors_taxo_taille | hors vocabulaire, absent | texte_libre:tailler abricotiers | abstention | ✓ | abstention | ✓ |
| hors_taxo_deneigement | hors vocabulaire, absent | texte_libre:déneigement parking | abstention | ✓ | p24, p15, p23 | ✗ |
| hors_taxo_droit_maritime | hors vocabulaire, faux ami partiel | texte_libre:droit maritime | abstention | ✓ | p13, p12 | ✗ (viol.) |
| info_manquante_aide | information manquante | — | abstention | ✓ | abstention | ✓ |
| info_manquante_zone_seule | information manquante | zone:Suisse alémanique | abstention | ✓ | p06, p01, p03 | ✗ |

**Limites** : cas écrits par l'auteur de la taxonomie (circularité), 37 profils fictifs, aucun utilisateur réel. Ces chiffres montrent que le mécanisme fonctionne comme conçu, pas qu'il est utile aux membres.

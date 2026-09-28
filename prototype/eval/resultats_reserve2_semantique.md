# Résultats d'évaluation (exploratoire, données fictives)

Jeu : **reserve2** · analyseur : **regles+semantique** · 18 cas · généré par `python -m eval.run_eval --jeu reserve2`


| Mesure | Le Fil du Club | Mots-clés + mêmes filtres |
|---|---|---|
| succes@3 | 15/15 | 7/15 |
| violations | 0/18 | 0/18 |
| abstention_correcte | 18/18 | 14/18 |

Preuves citées retrouvées mot pour mot dans le profil : 21/21 (vrai par construction pour l'extraction par règles ; le garde-fou compte surtout si un LLM rédige un jour les explications).

Latence médiane : analyse 1.86 ms, recherche 12.6 ms (machine locale, 37 profils).

| Cas | Catégorie | Critères extraits | Moteur top 3 | ok | Référence top 3 | ok |
|---|---|---|---|---|---|---|
| r2_vigiles | paraphrase | expertise:securite_evenement | p18 | ✓ | p20 | ✗ |
| r2_de_treuhand | allemand | expertise:fiduciaire | p12 | ✓ | abstention | ✗ |
| r2_de_uebersetzer | allemand | expertise:traduction, langue:fr, langue:de, expertise:emballage? | p16 | ✓ | abstention | ✗ |
| r2_etiquettes | pluriel | expertise:emballage | p27 | ✓ | p27, p16 | ✓ |
| r2_nacelles | pluriel | expertise:location_machines, expertise:tourisme? | p25 | ✓ | p25 | ✓ |
| r2_photographes | pluriel | expertise:photo_video | p15 | ✓ | p28 | ✗ |
| r2_audits_energie | pluriel, sans verbe | expertise:efficacite_energetique, zone:Valais | p22 | ✓ | p22, p18, p25 | ✓ |
| r2_pac_pas_transport | négation | expertise:installation_froid | p03 | ✓ | p33, p34 | ✗ |
| r2_tessin_italien | contraintes incompatibles | expertise:transport_frigorifique, langue:it, zone:Tessin | abstention | ✓ | abstention | ✓ |
| r2_mentor_reprise | paraphrase | expertise:mentorat, expertise:transmission_entreprise? | p29 | ✓ | p29, p24, p15 | ✓ |
| r2_leasing | paraphrase | expertise:financement, expertise:vins? | p23 | ✓ | p28, p23 | ✓ |
| r2_rancongiciels | pluriel | expertise:cybersecurite | p10 | ✓ | p24, p15, p23 | ✗ |
| r2_drones | pluriel | expertise:photo_video | p15 | ✓ | p02, p10 | ✗ |
| r2_couvreur | absent, faux ami | texte_libre:couvreur refaire toit | abstention | ✓ | abstention | ✓ |
| r2_traducteur_pas_anglais | négation de langue | expertise:traduction, langue:de | p16 | ✓ | p16 | ✓ |
| r2_assurance_flotte | paraphrase | expertise:assurance | p24 | ✓ | p24, p06, p01 | ✓ |
| r2_apero_80 | absent | expertise:traiteur | abstention | ✓ | p20, p18, p05 | ✗ |
| r2_banque | court | expertise:financement | p23 | ✓ | abstention | ✗ |

**Limites** : cas écrits par l'auteur de la taxonomie (circularité), 37 profils fictifs, aucun utilisateur réel. Ces chiffres montrent que le mécanisme fonctionne comme conçu, pas qu'il est utile aux membres.

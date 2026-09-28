# Résultats d'évaluation (exploratoire, données fictives)

Jeu : **base** · analyseur : **regles+semantique** · 20 cas · généré par `python -m eval.run_eval --jeu base`


| Mesure | Le Fil du Club | Mots-clés + mêmes filtres |
|---|---|---|
| succes@3 | 16/16 | 14/16 |
| violations | 0/20 | 8/20 |
| abstention_correcte | 20/20 | 17/20 |

Preuves citées retrouvées mot pour mot dans le profil : 41/41 (vrai par construction pour l'extraction par règles ; le garde-fou compte surtout si un LLM rédige un jour les explications).

Latence médiane : analyse 2.22 ms, recherche 11.63 ms (machine locale, 37 profils).

| Cas | Catégorie | Critères extraits | Moteur top 3 | ok | Référence top 3 | ok |
|---|---|---|---|---|---|---|
| clair_transport_zurich | besoin clair + contraintes | expertise:transport_frigorifique, zone:Suisse alémanique, langue:de? | p01, p05 | ✓ | p32, p01, p03 | ✗ (viol.) |
| clair_transport_geneve | besoin clair | expertise:transport_frigorifique, zone:Suisse romande | p02, p01, p05 | ✓ | p33, p02, p01 | ✓ |
| fauxami_securite_stand | faux ami sémantique | expertise:securite_evenement, expertise:evenementiel? | p18 | ✓ | p18, p19, p10 | ✗ (viol.) |
| fauxami_securite_info | faux ami sémantique | expertise:cybersecurite | p10 | ✓ | p10, p18, p19 | ✗ (viol.) |
| fauxami_securite_chantier | faux ami sémantique | expertise:sante_securite_travail | p19 | ✓ | p19, p13, p18 | ✗ (viol.) |
| fauxami_plateforme_web | faux ami sémantique | expertise:developpement_web, expertise:tourisme? | p26 | ✓ | p26, p25, p05 | ✗ (viol.) |
| fauxami_plateforme_machine | faux ami sémantique | expertise:location_machines | p25 | ✓ | p20, p26, p19 | ✗ (viol.) |
| fauxami_chaine_froid | faux ami sémantique | expertise:transport_frigorifique, zone:Suisse romande | p02, p01, p05 | ✓ | p03, p02, p01 | ✗ (viol.) |
| contrainte_langue | contrainte explicite | expertise:fiduciaire, langue:de | p12 | ✓ | p12 | ✓ |
| contrainte_incompatible | contraintes incompatibles | expertise:transport_frigorifique, langue:it, zone:Tessin | abstention | ✓ | abstention | ✓ |
| profil_incomplet | profil incomplet | expertise:transport_frigorifique, zone:Valais | p02, p01, p06 | ✓ | p01, p03, p02 | ✓ |
| clair_droit_travail | besoin clair | expertise:droit_travail | p13 | ✓ | p13, p19 | ✓ |
| clair_saisonniers | besoin clair (sans verbe de recherche) | expertise:recrutement | p14 | ✓ | p14 | ✓ |
| clair_solaire | besoin clair | expertise:energie_solaire | p22 | ✓ | p20, p19, p34 | ✗ |
| clair_mentor | besoin clair | expertise:mentorat | p29 | ✓ | p29, p24, p15 | ✓ |
| clair_distributeur | besoin clair | expertise:export_suisse_alemanique | p32 | ✓ | p32, p05, p06 | ✓ |
| clair_photo | besoin clair | expertise:photo_video | p15 | ✓ | p02, p15, p32 | ✓ |
| absent_iso | absence de bonne correspondance | expertise:certification_iso27001 | abstention | ✓ | p33 | ✗ |
| absent_droit_maritime | absence de bonne correspondance | texte_libre:droit maritime | abstention | ✓ | p13, p12 | ✗ (viol.) |
| absent_traiteur | absence de bonne correspondance | expertise:traiteur | abstention | ✓ | p20, p18 | ✗ |

**Limites** : cas écrits par l'auteur de la taxonomie (circularité), 37 profils fictifs, aucun utilisateur réel. Ces chiffres montrent que le mécanisme fonctionne comme conçu, pas qu'il est utile aux membres.

# Mémo red team (travail) — attaques menées pendant les cycles techniques 1 à 8 et le sprint d'innovation

| Cycle | Attaque | Résultat | Preuve |
|---|---|---|---|
| 1 | Deviner QUI refuse les introductions (comptes exacts, messages d'erreur différents) | Fuite réelle → k-anonymat (K=3) et réponse uniforme | FAILURES 21, `test_confidentialite_reseau.py` |
| 1 | Déduire le graphe des autres depuis une carte candidat | Fuite réelle → vue membre = ses relations seulement | FAILURES 22 |
| 2 | Faire passer une rencontre d'il y a 300 jours pour une relation actuelle | Défaut réel → `graphe_actuel` | FAILURES 23, propriété sur 100 historiques |
| 3 | Réseau de 500 à 5000 membres | Quadratique → corrigé, test de complexité | FAILURES 24 |
| 4 | Proposer un collègue en écrivant l'entreprise autrement | Défaut réel → clé d'organisation | FAILURES 25 |
| 4 | Contourner un refus d'introduction par une table de soirée, y compris en levant une contrainte | Défaut réel → contrainte NON levable | FAILURES 26 |
| 5 | Un tiers agit sur chaque transition de chaque état | Aucun défaut (403 sans état ni nom) | `test_securite_api.py` (8 cas) |
| 5 | Double clic / double soumission | Aucun défaut (une seule transition) | idem |
| 5 | Entrées surdimensionnées (100 000 caractères, 5000 offres) | Défaut réel → toutes les entrées bornées, test d'introspection | FAILURES 27 |
| 5 | Injection SQL dans un identifiant, date invalide | Aucun défaut (requêtes paramétrées, 4xx propres) | idem |
| 6 | Optimiser l'activation du réseau « naïvement » (isolés d'abord) | Effet de second ordre : îlots de deux | BENCHMARK_MEMO §2 |
| 8 | Deux soirées le même jour ; refus postérieur à l'approbation d'un plan | Collisions réelles → refus explicites | FAILURES 29–30 |
| 7 | Un membre rencontre 8 personnes qui peuvent l'aider, puis publie un besoin | Saturation réelle (8 relances le même jour) → budget d'attention | FAILURES 28 |
| Sprint | Membre fermé aux introductions dans un ravivement, une présentation, une opportunité, une relance après retrait | **3 violations de consentement** (dont une antérieure au gel) → modèle à deux niveaux (invisible par défaut / retrait explicite) | FAILURES 35–37 |
| Sprint | Enregistrer une « décision » avec une paire arbitraire (membre fermé) | Refusé (409) : seules les actions proposables | `test_boucle.py` |
| Sprint | Deux groupes reliés par UNE personne | Angle mort de l'observatoire → PASSAGE_UNIQUE | FAILURES 31 |
| Sprint | Aucune action possible ; non-membre dans les relations ; 500–1000 membres | Plan vide « idéal » ; KeyError ; lenteur → corrigés | FAILURES 32–34 |

## Surfaces NON attaquées (déclarées)
- Authentification réelle : absente (identité de démonstration par en-tête ; le mode réel refuse tout, testé).
- LLM réel : aucune clé ; seuls des serveurs simulés ont été attaqués (panne, refus, JSON invalide, balises).
- Rôle « animateur » : les vues d'organisation (plan de soirée, tableau du Club, interventions) sont ouvertes en démo.

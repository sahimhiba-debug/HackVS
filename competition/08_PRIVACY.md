> ⛔ **OBSOLÈTE — produit d'avant le pivot, ne pas présenter.** Ce dossier décrit l'ancien produit (« intelligence relationnelle »), pas le registre des capacités. La réécriture du pitch est en cours (équipe) ; voir `TODO-DEMO.md`.

# 08 — Confidentialité (par conception, par défaut)

| Principe | Mise en œuvre | Test |
|---|---|---|
| Invisible par défaut | nouveau membre non recommandable tant qu'il ne l'accepte pas | `test_explications.py` |
| Jamais de coordonnées | aucune coordonnée stockée ; partage seulement après double accord | `test_scene.py`, `test_parcours.py` |
| Lien d'un tiers protégé | intermédiaire jamais nommé ; présentation proposée d'abord à lui | `test_reseau.py` |
| Refus respecté et non révélé | un membre qui refuse n'est ni proposé ni nommé ; refus jamais reproposé | `test_scene.py`, `test_cycle.py` |
| Brouillons privés | jamais utilisés comme raison (fuite trouvée et corrigée) | `test_confidentialite_reseau.py` |
| Besoins anonymes | jamais projetés dans la mémoire (une relance nommerait l'auteur) | `reseau.projeter` |
| Aucun score de personne | seulement des phénomènes du réseau (ponts, isolement) | revue de code |
| Profils = données non fiables | injections signalées, sans effet sur les règles | `test_parcours.py` |
| Ce qui est utilisé / déduit / inconnu | affiché sur chaque carte | `test_explications.py` |

Limites : authentification non implémentée (mode réel → 501) ; la vue « graphe » de la scène est une vue de
démonstration — en production, un membre ne voit que ses relations et le Club des agrégats.

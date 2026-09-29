# Preuves de validation (2026-09-29, environnement de développement, Linux x86-64, Python 3.11)

Commandes réellement exécutées et résultats lus (codes de sortie réels). Aucun secret, aucune donnée personnelle réelle.

| Commande (depuis la racine) | Résultat |
|---|---|
| `make quality-check` | code 0 — secrets : aucun ; ruff : OK ; mypy : 72 fichiers sans erreur ; pytest : **486 réussis** ; bout en bout : **5 réussis** (1 scène historique + 4 banc d'essai) ; évaluations : non-régression OK, décisions 20/20, registre des affirmations OK |
| `cd prototype && python -m pytest -q tests/test_essai.py tests/test_essai_securite.py tests/test_essai_cas_inedits.py` | 17 + 16 + 10 réussis |
| `cd prototype && HACKVS_E2E_OBLIGATOIRE=1 python -m pytest -q tests/test_e2e_pulse.py` | 4 réussis (deux contextes de navigateur indépendants ; captures : `captures/`) |
| mutation : retirer `_verifier_version` de `Banc.decider` | 2 tests échouent (restauré) |
| mutation : `niveau_partage` prend le niveau le PLUS permissif | 2 tests échouent (restauré) |
| mutation : ignorer la durée maximale d'une offre | 2 tests échouent (restauré) |
| `cd prototype && python scripts/reproduire_sprint.py` puis `git status eval/` | tous les bancs OK ; aucun résultat publié modifié |
| `cd prototype && python -m eval.eval_apertus` | Apertus : **NON EXÉCUTÉ** (aucun identifiant) ; secours : `structurer_essai` objet reconnu 5/5, aucun geste proposé |
| `env \| grep -c '^APERTUS_'` | 0 — aucun identifiant Apertus : pas de test réel possible, rien n'a été créé ni payé |
| clone neuf + environnement neuf + `make setup` + `make quality-check` (avant le pivot, commit 4fe344e) | vert en ≈ 3 min — non rejoué après le pivot (aucune dépendance ajoutée) |

## Non exécuté (et pourquoi)
- Fournisseur Apertus réel : aucun identifiant fourni.
- Deux téléphones physiques sur un réseau de salle : remplacé par deux contextes de navigateur indépendants.
- Construction de l'image Docker : pas de démon ; `tests/test_image.py` reconstitue les fichiers de l'image et la démarre.
- Toute mesure auprès d'utilisateurs (temps, corrections, adoption) : aucun utilisateur.

## CI
GitHub Actions s'exécute à chaque poussée sur la branche (qualité, dépendances, reproductibilité avec bout en bout).
Le résultat se lit sur GitHub ; il n'est pas recopié ici pour ne pas figer une affirmation qui dépend d'un tiers.

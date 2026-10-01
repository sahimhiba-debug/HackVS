> **HISTORIQUE — rédigé avant le registre des capacités (28–30.09.2026).** Conservé pour la traçabilité des décisions ; ne décrit PAS le produit actuel, et ses chiffres, routes et noms de fichiers peuvent être faux aujourd'hui. État actuel : [README](/README.md) · [index de la documentation](/docs/README.md).

# État de reprise (lot 4, 28.09.2026)

Pour reprendre le travail sans relire toute la conversation.

## Où en est-on
- Branche `claude/modest-bohr-xvk53n`, poussée ; CI GitHub Actions verte (lint, 53 tests, non-régression).
- Lots 1 à 3 : Bourse des besoins, scène, vue du Club, profil en 30 s, présentation, Docker.
- Lot 4 (sprint « niveau supérieur ») : IA locale multilingue (suggérer / confirmer, hybride mesuré), « pourquoi / pourquoi pas »,
  plan de soirée optimisé (langue commune, .ics), serveur MCP (stdio + HTTP avec jetons, confirmation humaine, codes d'erreur),
  sécurité (profils non fiables, télémétrie onnxruntime coupée), faux amis composés, reconnaissance de 20 projets open source,
  CI. Détails : DECISIONS.md §9, EVALUATION.md, OPEN_SOURCE_RECON.md.
- **Aucun retour d'audit ChatGPT reçu à ce jour** : rien n'est présenté comme audité.

## Ce qui attend une entrée extérieure
| Élément | Bloque | Débloque |
|---|---|---|
| Clé Anthropic ou Apertus + accès réseau à l'API | Mesure réelle des LLM ; démo « agent en direct » | Variables d'environnement de l'environnement (jamais dans le chat) ; `python scripts/verifier_llm.py --confirmer` |
| Accès à huggingface.co | Reranker neuronal (BGE-reranker-v2-m3), BGE-M3 | Liste d'autorisation réseau |
| Brief et règlement de Hack VS | Direction finale ; réutilisation du code | Brief officiel |
| Décision de déploiement public | QR de la présentation | Hiba (voir DEPLOIEMENT.md) |

## Prochaines actions proposées
1. Avec une clé : mesurer Claude et Apertus sur les jeux (post-hoc) ; faire tourner la démo agent en direct.
2. Faire écrire 10 à 20 cas **indépendants** (équipe, auditeur) ; les exécuter une fois.
3. Disponibilités (créneaux) : aujourd'hui un simple booléen.
4. Interface bilingue FR/DE.

## Commandes de vérification rapide
```bash
cd prototype && ruff check . && python -m pytest -q && python -m eval.run_eval --verifier
uvicorn app.main:app & python scripts/parcours_demo.py && python scripts/demo_agent_mcp.py
```

## Pièges connus
- `--reload` ne recharge pas `web/` (rafraîchir le navigateur suffit).
- Les jeux réservés déjà exécutés sont désormais **post-hoc** ; tout nouveau jeu réservé doit être commité avant le code qu'il mesure.
- `run_eval` sans `--verifier` réécrit `eval/resultats_*.md` (latences) : ne pas les commiter par accident.
- Le journal (`/api/journal`, `/api/flux`) expose les identités : réservé à la démo.
- `onnxruntime` envoie de la télémétrie si `ORT_DISABLE_TELEMETRY` n'est pas posé avant son import (fait dans `app/semantique.py`).

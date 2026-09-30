> ⛔ **OBSOLÈTE — produit d'avant le pivot, ne pas présenter.** Ce dossier décrit l'ancien produit (« intelligence relationnelle »), pas le registre des capacités. La réécriture du pitch est en cours (équipe) ; voir `TODO-DEMO.md`.

# 04 — Architecture

## En 10 secondes
```
MEMBRE
  ↓
INTELLIGENCE RELATIONNELLE   (compréhension du besoin : règles locales, IA locale en suggestion, LLM optionnel)
  ↓
GRAPHE TEMPOREL + PREUVES    (journal d'événements, affirmations à statut, source unique par fait)
  ↓
OPTIMISATION                 (solveur sous contraintes, frontière de Pareto, simulation)
  ↓
CONSENTEMENT / POLITIQUE     (code déterministe testé : double accord, confidentialité, gardien)
  ↓
ACTION                       (aperçu → autorisation humaine → exécution SIMULÉE → vérification)
  ↓
MÉMOIRE                      (tout est rejouable)
```

## Pour le jury technique
- `prototype/app/` : API FastAPI, magasin SQLite (workflow d'introduction en double accord), moteur de mise en
  relation (preuves citées), analyse du besoin, scène.
- `prototype/plateforme/` (générique) : affirmations et statuts, spécification et compilateur d'intention, solveur
  HiGHS, graphe, validation L0–L8, critique / gardien / médiateur, exécution et rejeu, certificat, passerelle de
  modèles, plan d'action, **mémoire temporelle**.
- `prototype/adaptateurs/club/` (propre au Club) : vocabulaire, cycle des relations, réseau (projection, état de
  relation, chemin chaud, boîte), micro-cercles (hors démo).
- Frontière d'interopérabilité : serveur MCP (jetons, portées, confirmation humaine). Pas de bus d'événements, pas de
  microservices : une instance suffit (ARCHITECTURE_DECISIONS AD-08).

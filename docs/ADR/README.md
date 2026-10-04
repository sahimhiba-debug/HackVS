# Décisions d'architecture (ADR)

Rédigées le 29.09.2026. Statut relu le 01.10.2026 contre le code (chaque module cité existe, ou la décision est dite remplacée).

| # | Décision | Statut au 01.10 |
|---|---|---|
| [0001](0001-adaptateur-apertus.md) | Adaptateur Apertus : client HTTP compatible OpenAI, sans SDK | en vigueur |
| [0002](0002-coffre-d-identites.md) | Coffre d'identités séparé du moteur | en vigueur (`intelligence/identite.py`, `Coffre`) |
| [0003](0003-reseau-pseudonymise.md) | Réseau pseudonymisé et rendu par spectateur | en vigueur ; `intelligence/vues.py` cité a été scindé en `vues_intelligence.py`, `vues_capacites.py`, `vues_essai.py` |
| [0004](0004-machine-d-etats-de-l-activation.md) | Machine d'états explicite pour l'activation | **remplacée** : `intelligence/activation.py` a été retiré avec l'ancien moteur ; la machine d'états vivante est `TRANSITIONS` dans `intelligence/essai.py` (essais), et les statuts du registre dans `intelligence/capacites.py` |
| [0005](0005-journal-d-evenements-et-audit.md) | Journal d'événements comme source de vérité du cycle de vie | en vigueur (`plateforme/memoire.py`) |
| [0006](0006-abstraction-du-fournisseur-ia.md) | Un seul point d'entrée IA, repli déterministe déclaré, sortie non fiable | en vigueur (`intelligence/ia.py`, `intelligence/roles_ia.py`) |
| [0007](0007-integration-des-adhesions.md) | Intégration des adhésions par adaptateur | en vigueur (`intelligence/identite.py`) |
| [0008](0008-pwa-sans-framework.md) | Application du membre : PWA sans framework ni étape de construction | en vigueur (`web/pulse/`) |
| [0009](0009-file-hors-ligne-des-reponses.md) | File d'attente hors ligne des réponses (exception à l'ADR 0008) | **branche annee-1, pas dans la démo** (`HACKVS_HORS_LIGNE`) |
| [0010](0010-coherence-visuelle-annee-1.md) | Lot 12 : cohérence avec le Design System d'abord, refonte plus profonde à côté seulement | **branche annee-1** |

# Club Pulse — le registre vivant de ce que le Club peut faire ensemble (Hack VS 2026)

**IA → moteur déterministe → décision humaine.** Un modèle de langage peut seulement *proposer* (relever une quantité
dans une phrase, rapprocher un mot du catalogue, raconter des faits fermés) ; un moteur déterministe compose, vérifie
et invalide ; une personne décide et consent. Aucune capacité, aucun consentement, aucun destinataire n'est jamais
choisi par un modèle.

Une **capacité** du Club (ex. « Accueillir une délégation d'acheteurs germanophones ») est un assemblage de pièces
déclarées par des membres — une salle ≥ 15 places, un minibus ≥ 12 places, une interprétation FR–DE — valables à une
date et **consenties pour cette finalité**. S'il en manque une seule, le système formule une demande minimale (Ask) à
une catégorie de membres ; une réponse la rend ACTIVE. Si une pièce disparaît (retrait, horaire changé, membre
indisponible), la capacité est DÉGRADÉE, la cause est dite par son rôle — jamais la personne — et une recomposition
est calculée, jamais appliquée.

| Statut | Ce qui l'est |
|---|---|
| **RÉEL** (code + tests) | registre des capacités (patrons, composition, distance 0/1, Ask, levier, pièces critiques, recomposition), consentement de finalité (reçu, retrait, re-consentement), Pulse par rejeu du journal, action collective (banc d'essai), rôles IA EXTRACT / NORMALIZE / NARRATE en *propositions* validées, parité IA ON/OFF, QR juré, « Tout effacer », journal rejouable (redémarrage à l'identique) |
| **SYNTHÉTIQUE** | tous les membres, entreprises, offres, horaires et patrons (marqués FICTIF, statut `SYNTHETIQUE` dans le journal) |
| **SIMULÉ / JOUÉ** | l'horloge de démonstration ; les gestes des personnages absents, joués depuis la console (statut `JOUE`, affiché) |
| **NON DÉMONTRÉ** | la qualité d'un vrai modèle sur les tâches du Club : Apertus (`swiss-ai/Apertus-v1.5-70B`, API d'inférence CSCS) répond depuis cet environnement (sonde du 01.10, [probe](docs/audit/probe_publicai.md)), mais la démo tourne sans modèle ; l'évaluation EXTRACT est prête et gelée mais n'a pas tourné ([EXTRACTION_EVAL](docs/audit/EXTRACTION_EVAL.md)). Utilité auprès de vrais membres : non mesurée |

## Lancer

```bash
make setup && make demo        # http://127.0.0.1:8000
```

`make demo` garde le journal dans un fichier (`prototype/var/club_pulse.db`) et tire **une fois** un secret stable
(`prototype/var/secret_demo`, hors dépôt) : un `kill -9` puis `make demo` rend le même monde, les mêmes sessions, le
même passe juré, et rejoue les sorties IA sans rappeler le modèle (`tests/test_redemarrage_kill9.py`). Nouvelle
démonstration : bouton de la régie.

Pages servies : `/app` (téléphone d'un membre) · `/projection` (écran commun, en rôles, sans noms) · `/etabli`
(l'Établi : le registre pour l'animation) · `/console` · `/demo/regie` (les deux téléphones côte à côte). Rien
d'autre n'est servi : l'ancien prototype répond 404 sauf `HACKVS_ANCIEN_PROTOTYPE=1`, et alors à cette machine
seulement ([historique](docs/ANCIEN_PROTOTYPE.md)).

| Variable | Effet |
|---|---|
| `HACKVS_ESSAIS_DB`, `HACKVS_SECRET` | journal fichier et secret stable (posés par `make demo`) ; sans eux : mémoire et secret aléatoire |
| `HACKVS_CONSOLE_JETON` | exigé par la console hors de la machine locale |
| `APERTUS_BASE_URL`, `APERTUS_API_KEY`, `APERTUS_MODEL` | branche Apertus (API compatible OpenAI) ; absent → forme déterministe, dite telle |

## Vérifier

```bash
make quality-check             # secrets, lint, types, suite complète, E2E Chromium, évaluations
make mutation                  # mutation (mutmut) du registre des capacités ; jamais sur la machine de démonstration
```

Mesuré, pas supposé : ~1 500 tests et 28 E2E hermétiques (aussi en « mode salle », réseau coupé) ; oracle en force
brute contre le compositeur ; mutation **sur `intelligence/capacites.py` seulement** (campagne locale du 01.10) :
1 229 / 1 327 mutants tués, 98 survivants tous classés — confirmé en CI par la porte durcie (campagne GitHub #15) ([liste](docs/audit/mutants_survivants.txt)).

## Documentation

- **Audit final avant le gel** (architecture, sécurité, tests, performance, limites, risques) : [FINAL_AUDIT](docs/audit/FINAL_AUDIT.md) ·
  registre des affirmations : [CLAIMS](docs/audit/CLAIMS.md) · index de la documentation (à jour / historique) : [docs/README](docs/README.md)
- État réel, constats et corrections : [SENIOR_ENGINEERING_AUDIT](docs/audit/SENIOR_ENGINEERING_AUDIT.md) ·
  [SENIOR_ENGINEERING_FINDINGS](docs/audit/SENIOR_ENGINEERING_FINDINGS.md) · phases : [PHASE_3](docs/audit/PHASE_3.md)
- Démonstration : [DEMO_SCRIPT](docs/audit/club-pulse-pivot/DEMO_SCRIPT.md) · [TODO-DEMO](TODO-DEMO.md)
- Menaces : [THREAT_MODEL](docs/THREAT_MODEL.md) · décisions : [ADR](docs/ADR/README.md)
- `docs/ARCHITECTURE.md` décrit encore le produit d'avant le pivot (constat F02, réécriture en cours) ; le dossier
  `competition/` est en quarantaine (bannière sur chaque fichier).

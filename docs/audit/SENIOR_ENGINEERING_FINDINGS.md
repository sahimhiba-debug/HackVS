# Findings — audit d'ingénierie senior (état au 2026-10-01)

> Sources : [SENIOR_ENGINEERING_AUDIT.md](SENIOR_ENGINEERING_AUDIT.md) (audit profond, commit `53e87cd` : preuves,
> expériences E1–E7) et [VAGUES_CORRECTIONS.md](VAGUES_CORRECTIONS.md) (chaque correction : test rouge, changement,
> contre-épreuve, commit). Gravité : CRITICAL / HIGH / MEDIUM / LOW / INFO. États : FERMÉ (commit), OUVERT,
> ACCEPTÉ (risque connu, borné, expliqué), MESURÉ (constat chiffré, sans correction). Aucun CRITICAL trouvé.
> Gel du code : vendredi 02.10.2026, 18:00 — après, documentation, artefacts de démonstration et répétition seulement.
> Revue publique du 01.10 (R-01 à R-15, classés, preuves, correctifs) : [REVUE_PUBLIQUE.md](REVUE_PUBLIQUE.md).

| ID | Gravité | Domaine | Constat | État |
|---|---|---|---|---|
| F01 | HIGH | Frontière IA | `POST /moi/demandes` écrivait un BESOIN interprété par le modèle sans confirmation | FERMÉ `bcf2710` — interpréter n'écrit rien ; `…/confirmer` publie exactement ce qui a été montré |
| F02 | HIGH | Documentation | `docs/ARCHITECTURE.md` et ADR 0004 décrivent le produit d'avant le pivot | OUVERT — signalé dans le README (`d3e53eb`) ; réécriture : travail de documentation d'après le gel |
| F03 | MEDIUM | Tests E2E | sonde de disponibilité sur `/api/stage` (404) : 20 s aveugles | FERMÉ `762db1f` (+ `36faa4e`) |
| F04 | MEDIUM | Tests | signature forgée égale à la vraie 1 fois sur 256 | FERMÉ `a652690` |
| F05 | MEDIUM | Journal | `ACCORD`/`RETRAIT` à deux sens ; charges `dict[str, Any]` ; 31+ types sans catalogue | OUVERT (lecteurs actuels corrects) ; reporté après la démo |
| F06 | MEDIUM | Architecture | `Banc` God object (1 247 l.) | ACCEPTÉ (reporté) |
| F07 | MEDIUM | Rejeu | rejeu des types récents non gardé | FERMÉ `8d4c98a` |
| F08 | MEDIUM | API | routes sans écran ; balayage IDOR | balayage fait (aucun IDOR) et figé en test pour les essais (`298adab`) ; classement DELETE/KEEP/DEPRECATE : OUVERT |
| F09 | MEDIUM | Sécurité | `/acces` limité par IP (salle derrière un NAT) | FERMÉ `2712f5b` — par code + plafond global, jamais par IP |
| F10 | MEDIUM | Tests | 4 tests de frontière qui ne vérifient que l'absence | OUVERT |
| F11 | MEDIUM | Architecture | 39 modules hérités co-résidents | OUVERT — frontière dite (README, `docs/ANCIEN_PROTOTYPE.md`) |
| F12–F15, F18 | LOW | divers | partage de note non idempotent ; coût de `candidats` ; `type: ignore` ; cycle hérité ; `date.today()` hérité | ACCEPTÉ |
| F16 | LOW | Documentation | `docs/` sans statut historique | OUVERT (`docs/ANCIEN_PROTOTYPE.md` créé) |
| F17 | LOW | Rejeu | configuration hors journal (patrons, budgets, secret) | OUVERT — contrat à écrire |
| F19–F21 | INFO | — | console locale ; démo seulement ; Hypothesis | OUVERT (documentation) |
| F22 | INFO | Mutation | campagne GitHub | FERMÉ — run #4 vert ; campagne locale du 01.10 : 1 229 / 1 327, 98 survivants classés (`0fa7620`) |
| F23 | MEDIUM | Tests / périmètre | E2E hors configuration produit ; `/demo/stage` | FERMÉ — tests (`762db1f`), README sans `/demo/stage` (`d3e53eb`) ; périmètre inchangé |
| F24 | MEDIUM | Rejeu IA | clé de rejeu liée au secret ; aucun lanceur ne posait de secret | FERMÉ `4c3975e` (avec F29) |
| F25 | HIGH | CI | CI rouge par deux régressions de `762db1f` | FERMÉ `36faa4e` |
| F26 | HIGH | Capacités | consentement « valable » d'une offre qui ne couvre plus sa pièce | FERMÉ `378277c` — DÉGRADÉE, cause dite et journalisée, reçu exact |
| F27 | MEDIUM | Journal | état en mémoire appliqué avant la validation ; cache par comptage | FERMÉ `02b6655` |
| F28 | MEDIUM | Concurrence | réinitialisation : deux mondes dans un journal ; TOCTOU session / commande | FERMÉ `9ca23cb` — passage lecteurs / rédacteur, journal de l'ancien monde fermé |
| F29 | MEDIUM | Démo | le lancement par défaut ne persistait rien | FERMÉ `4c3975e` — `kill -9` + relance : état, sessions, passe juré, rejeu IA intacts |
| F30 | HIGH | Documentation | README contradictoire | FERMÉ `d3e53eb` |
| F31 | MEDIUM | Frontière IA | provenance « proposé par l'IA, confirmé » jamais écrite | FERMÉ `bc939e4` |
| F32 | LOW | Capacités | acquittement tombant sur des traces | FERMÉ `e33e1f6` |
| F33 | LOW | Vie privée | fragments de sortie du modèle dans les journaux | FERMÉ `af7837c` |
| F34 | LOW | Vie privée | effacement inatteignable et non durable | FERMÉ `4ac6f81` — « Tout effacer », journalisé, rejoué |
| F35 | INFO | Rejeu | activations de comptes hors journal | FERMÉ `4c3975e` (`ACTIVATION` journalisée) |
| F36 | LOW | Sécurité | oracle d'existence d'un essai (403 / 404) | FERMÉ `298adab` |
| F37 | MEDIUM | Tests | mutation limitée à `capacites.py` | MESURÉ — campagne locale sur `essai.py` terminée le 02.10 : 3 528 mutants, 2 311 tués, 1 150 survivants NON classés, 67 sans test (population d'avant H2 ; VAGUES_CORRECTIONS § 4.1) ; non bloquante en CI ; classification après le gel |
| F38 | LOW | Hygiène | `BUDGET_NOEUDS` muté ; garde par `assert` ; `httpx.Client` non fermé | OUVERT (après la démo) |
| F39 | INFO | Horloges | heure murale dans un journal à dates simulées | OUVERT (documentation) |
| F40 | INFO | Essai | un brouillon n'expire jamais | OUVERT (décision produit) |

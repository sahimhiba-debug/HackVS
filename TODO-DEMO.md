# TODO — artefacts de démonstration

## Régénérés à la fin de la Phase 3 (commit `a03bfa6`, 2026-09-30)

Aux dates actuelles (horloge au mardi **06.10.2026**, action collective le jeudi **08.10**, registre le vendredi **09.10**) :

| Artefact | Comment | Résultat |
|---|---|---|
| `docs/audit/club-pulse-pivot/captures/action/demo_action.webm` + `.json` | `scripts/enregistrer_demo.py --commit a03bfa6` (serveur démo, port 8767) | 87 s, exécution continue sans montage |
| `…/captures/action/p0…p6, a1…a4, b1` + `delais.json` | `HACKVS_CAPTURES=… pytest tests/test_e2e_action.py` | dates 08.10 à l'écran ; accord → écran 678 ms, perturbation → écran 394 ms |
| `DEMO_SCRIPT.md` § 2 et § 6 | réalignés sur le nouveau `demo_action.json` | horodatages et délai « 1 accord sur 3 » mesurés |
| `PREUVES.md`, `REVUE_JURY.md` § 1 | commit et vidéo mis à jour ; constats de la revue gardés, datés | — |

## RESTE À FAIRE — à décider avant de présenter

| Artefact | État | Pourquoi ce n'est pas mécanique |
|---|---|---|
| **`competition/*`** (dossier de pitch, `competition/video/demo.webm`, captions, timeline) | décrit le produit **d'AVANT le pivot** (« intelligence relationnelle », « Sophie rejoint le Club », vidéo de l'ancien prototype par `scripts/enregistrer_video.py`) | le réécrire pour le registre des capacités est un choix de récit et de pitch, pas une régénération ; **ne pas le présenter tel quel** |
| Captures du registre (Établi, passeport, QR juré, interrupteur IA) | aucune capture versionnée ; seuls les E2E les vérifient | à produire avec le récit ci-dessus |
| `…/captures/essai-*.png` | ancien scénario « étiquette » | à vérifier, sans doute à archiver |

Non concernés : `docs/captures/*` (ancien prototype « Le Fil du Club ») ; `eval/resultats_*` (vérifiés à l'octet par la CI).

## Redémarrage du serveur = nouvelle démonstration

Depuis `18829d4`, le serveur **reprend** son journal au démarrage (`HACKVS_ESSAIS_DB`) au lieu de l'effacer ; le
scénario guidé, lui, ne reprend pas au milieu (son contexte n'est pas journalisé : la console affiche « état repris du
journal »). **Règle de scène : après tout redémarrage, console → « Nouvelle démonstration » avant de commencer.**

## Aucune campagne de mutation sur la machine de démonstration

Pendant le hackathon, **jamais** `make mutation` (ni mutmut) sur l'ordinateur de la salle : une campagne occupe tous
les cœurs pendant ≈ 30 min et ralentit le serveur de démonstration (constaté : un test de délai a échoué en local
pendant une campagne). Les campagnes tournent sur GitHub (workflow « Mutation », non bloquant) : la nuit, quand le
registre change, et avant tout tag `demo-*` — le tag n'est posé qu'après une campagne verte.

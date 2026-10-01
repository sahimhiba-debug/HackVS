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
| **`competition/*`** (dossier de pitch, `competition/video/demo.webm`, captions, timeline) — **EN QUARANTAINE** : bannière « OBSOLÈTE — produit d'avant le pivot, ne pas présenter » en tête de chaque fichier Markdown (et `OBSOLETE.md` dans chaque dossier non-Markdown), gardée par `tests/test_quarantaine_competition.py` et réécrite par les générateurs ; **la réécriture du pitch est faite par l'équipe** | décrit le produit **d'AVANT le pivot** (« intelligence relationnelle », « Sophie rejoint le Club », vidéo de l'ancien prototype par `scripts/enregistrer_video.py`) | le réécrire pour le registre des capacités est un choix de récit et de pitch, pas une régénération ; **ne pas le présenter tel quel** |
| Captures du registre (Établi, passeport, QR juré, interrupteur IA) | aucune capture versionnée ; seuls les E2E les vérifient | à produire avec le récit ci-dessus |
| `…/captures/essai-*.png` | ancien scénario « étiquette » | à vérifier, sans doute à archiver |

Non concernés : `docs/captures/*` (ancien prototype « Le Fil du Club ») ; `eval/resultats_*` (vérifiés à l'octet par la CI).

## Redémarrage du serveur : le monde REVIENT — ne PAS faire « Nouvelle démonstration »

Corrigé le 01.10 : cette section disait l'inverse (« après tout redémarrage, console → Nouvelle démonstration »). C'était
vrai avant F29 ; depuis, l'étape de la régie (`DEMO_ETAPE`), les sessions, le passe juré, l'interrupteur IA et les sorties
IA sont journalisés et rejoués (`tests/test_redemarrage_kill9.py`). Après un plantage : `make demo`, et l'on reprend où
l'on était (`DEMO_SCRIPT.md` § 8 et rituel § 9.5). « Nouvelle démonstration » EFFACE le monde : seulement pour
recommencer volontairement, jamais pour « réparer » après un redémarrage.

## Aucune campagne de mutation sur la machine de démonstration

Pendant le hackathon, **jamais** `make mutation` (ni mutmut) sur l'ordinateur de la salle : une campagne occupe tous
les cœurs pendant ≈ 30 min et ralentit le serveur de démonstration (constaté : un test de délai a échoué en local
pendant une campagne). Les campagnes tournent sur GitHub (workflow « Mutation », non bloquant) : la nuit, quand le
registre change, et avant tout tag `demo-*` — le tag n'est posé qu'après une campagne verte.

# TODO — artefacts de démonstration périmés par le décalage de dates

Depuis le commit `1a855b1` (2026-09-30), le monde de démonstration vit **pendant la Foire du Valais 2026** : horloge au
mardi **06.10.2026**, scène le jeudi **08.10.2026** (avant : 03.11 / 05.11). Le code, les données et les tests sont à
jour ; les artefacts ci-dessous ont été produits AVANT et n'ont **pas** été régénérés (volontairement, fin de session).

| Artefact | Pourquoi il est périmé | Comment le régénérer |
|---|---|---|
| `docs/audit/club-pulse-pivot/captures/action/demo_action.webm` | enregistré au commit `dd75a7c` : dates 03.11 / 05.11 à l'écran ; antérieur aussi au consentement de projection journalisé, aux statuts JOUE et au nettoyage IA | serveur démo (port 8767) puis `python scripts/enregistrer_demo.py --sortie ../docs/audit/club-pulse-pivot/captures/action --commit $(git rev-parse --short HEAD)` |
| `…/captures/action/demo_action.json` | horodatage des étapes et textes de la vidéo ci-dessus (« 05.11 », commit `dd75a7c`) | produit par la même commande |
| `…/captures/action/p0…p6*.png`, `a1…a4*.png`, `b1*.png` | captures du test navigateur à l'ancienne date (« Jeudi 05.11 », « 05.11 16:00–16:45 ») | `HACKVS_CAPTURES=../docs/audit/club-pulse-pivot/captures/action python -m pytest -q tests/test_e2e_action.py` |
| `…/captures/action/delais.json` | mesures de la même exécution (valeurs non liées à la date, mais à remesurer avec les captures) | même commande que les captures |
| `docs/audit/club-pulse-pivot/DEMO_SCRIPT.md` § 6 (storyboard) | temps et libellés calés sur la vidéo `dd75a7c` ; § 2 porte déjà l'avertissement | réaligner sur le nouveau `demo_action.json` |
| `docs/audit/club-pulse-pivot/REVUE_JURY.md` § 1 | cite « Jeudi 05.11 » et « 05.11 16:00–16:45 » (constats datés de la revue : garder la trace, ajouter une note) | note en tête du § 1 |
| `docs/audit/club-pulse-pivot/PREUVES.md` | commit d'enregistrement `dd75a7c`, 514 tests (désormais 523 + 6 E2E), délais de cette exécution | mettre à jour après réenregistrement |
| `docs/audit/club-pulse-pivot/captures/essai-*.png` | captures de l'ancien scénario « étiquette » (monde antérieur au décalage) : à vérifier, sans doute à archiver | `tests/test_e2e_pulse.py` avec `HACKVS_CAPTURES` si conservées |

Non concernés : `docs/captures/*` (ancien prototype « Le Fil du Club », horloge propre) ; `eval/resultats_*`
(régénérés au commit `9f2d0e9`, vérifiés à l'octet par la CI).

## Redémarrage du serveur = nouvelle démonstration

Depuis `18829d4`, le serveur **reprend** son journal au démarrage (`HACKVS_ESSAIS_DB`) au lieu de l'effacer ; le
scénario guidé, lui, ne reprend pas au milieu (son contexte n'est pas journalisé : la console affiche « état repris du
journal »). **Règle de scène : après tout redémarrage, console → « Nouvelle démonstration » avant de commencer.**

## Aucune campagne de mutation sur la machine de démonstration

Pendant le hackathon, **jamais** `make mutation` (ni mutmut) sur l'ordinateur de la salle : une campagne occupe tous
les cœurs pendant ≈ 30 min et ralentit le serveur de démonstration (constaté : un test de délai a échoué en local
pendant une campagne). Les campagnes tournent sur GitHub (workflow « Mutation », non bloquant) : la nuit, quand le
registre change, et avant tout tag `demo-*` — le tag n'est posé qu'après une campagne verte.

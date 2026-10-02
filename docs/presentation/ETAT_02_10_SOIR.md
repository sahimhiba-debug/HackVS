# État au vendredi 02.10, soir — reprise sur une autre machine

Tout ce qui suit est dans le dépôt (branche `claude/modest-bohr-xvk53n`), sauf ce qui est marqué **hors dépôt**.

## Où est quoi

| Quoi | Où |
|---|---|
| Deck de la finale (lumière, mode jour/nuit, répétition) | `docs/presentation/deck/` — lancer : `python3 docs/presentation/deck/lancer.py` |
| Texte à dire, simple | `docs/presentation/03b_SCRIPT_A_DIRE.md` |
| Minutage (15 min, film 3:21, fin visée 13:30) | `docs/presentation/02_STRUCTURE.md` |
| Démo live, plans B, test de salle jour/nuit | `docs/presentation/04_DEMO_RUNBOOK.md` |
| Chiffres figés au gel | `docs/audit/club-pulse-pivot/PREUVES.md`, section « Gel du 02.10.2026, 18:00 » (commit `b1d4c66`, CI #179 verte) |
| PDF, vidéo motion (exports datés) | `docs/presentation/livrables/` |
| Le film (3:21, 242 Mo) | **hors dépôt** (ignoré par git) — iMac, clé USB, MacBook : `docs/presentation/deck/assets/film.mp4` |

## Reste à faire

1. **Tag `gel-demo`** — la session cloud ne peut pas pousser de tag (refus du proxy). Depuis un Mac :
   `git fetch origin && git tag -a gel-demo b1d4c66 -m "Gel de la démo — 02.10.2026 18:00, CI #179 verte" && git push origin gel-demo`
2. **Dossier du film** (script, cartons, page de contrôle, rapport) sur l'iMac : `git pull`, le placer dans
   `docs/presentation/film/`, committer, pousser (après le gel, seul `docs/` change).
3. **Film sur le MacBook** (AirDrop + clé USB), puis passage complet du deck Wi-Fi coupé : film du début à la fin,
   dernier plan figé, « Et après ? ».
4. ~~Chiffres du deck~~ — **fait le 02.10 au soir** : `deck/data/gel.json` rempli depuis PREUVES (`1 359` · `22` ·
   `1 229 / 1 327` · `< 1 s` · `0`, commit `b1d4c66`) ; revue refaite (`deck/review/final/`, slide 16-14).
5. **Samedi matin** : rituel DEMO_SCRIPT § 9.5, test D-PRES-1 (IA 3/3 ou éteinte), captures reprises sur la machine de
   démo (mêmes noms, `deck/assets/captures/`), test de salle jour/nuit (`04_DEMO_RUNBOOK.md` § 8, point 6).

## Décisions en cours

- Carton « L'homme qui disait oui. » du deck, en doublon avec le titre du film : **laissé tel quel** (décision du
  02.10 au soir).
- Le créneau de 15 minutes est supposé **sans** les questions du jury ; s'il les inclut, resserrer le minutage.

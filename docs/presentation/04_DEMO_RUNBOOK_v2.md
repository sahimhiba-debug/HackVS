# 04 v2 — Runbook de la démo (deck v2, 18 min)

La démo publique tourne **sur le Mac du pitch**, exposée en HTTPS par un tunnel ([DEMO_TUNNEL.md](../DEMO_TUNNEL.md)).
Le runbook v1 ([04_DEMO_RUNBOOK.md](04_DEMO_RUNBOOK.md)) reste le plan B complet (démo Établi + téléphone).

## 0. Fenêtres et matériel

| Fenêtre / appareil | Adresse | Qui |
|---|---|---|
| Deck v2 (écran 1, plein écran) | `python3 docs/presentation/deck/lancer.py` puis `http://127.0.0.1:8765/v2.html` (ajouter `?carte=1` **seulement** si la vraie carte a fait 5/5) | V1 (télécommande) |
| Écran géant de la salle (écran 1, autre fenêtre plein écran) | `http://127.0.0.1:8000/salle/ecran` | V2 bascule (⌘-Tab) |
| Régie (portable de V2, ou onglet) | `http://127.0.0.1:8000/salle/regie` — le jeton de console est demandé une fois | V2 |
| Téléphones de la salle | QR → `<PUBLIC_BASE_URL>/salle#s=…` (servi en direct : `/qr/salle.svg`) | le public |
| Téléphone de secours de V2 | le même QR, scanné avant le pitch (un participant garanti) | V2 |

## 1. Avant le pitch (H-30 min)

1. Alimentation branchée ; partage 4G prêt ; `./demo-tunnel.sh` lancé (PUBLIC_BASE_URL + HACKVS_CONSOLE_JETON).
2. Tunnel lancé (Funnel ; sinon Cloudflare) ; `curl "$PUBLIC_BASE_URL/sante"` répond.
3. Régie → **Purger**, puis **Ouvrir la salle**. `curl http://127.0.0.1:8000/qr/salle.txt` (sur le Mac) donne l'adresse attendue.
4. Deck v2 → slide « Sortez vos téléphones » : le QR s'affiche (sinon l'emplacement dit « QR servi en direct »).
5. Scanner le QR avec 2 téléphones de l'équipe, à travers le tunnel (4G, pas le Wi-Fi du Mac).
6. Constellation : `/salle/ecran` affiche les points ; mode jour ou nuit selon la salle (touche J).

## 2. Pendant l'acte 3 (5:30–9:30)

| Temps | Action exacte | Ce qu'on doit voir | Plan B |
|---|---|---|---|
| 5:30 | V1 sur la slide « Sortez vos téléphones » ; **V2 régie : « 1 bis · Sortez vos téléphones »** (la minute de bascule part de là, jamais de l'ouverture à H-30) | le QR en grand | QR absent : lire l'adresse de `/qr/salle.txt` ; ou passer à la vidéo (B) |
| 5:50 | V2 : ⌘-Tab vers `/salle/ecran` | les points arrivent (rien sous 3 : « la constellation s'allume à trois ») | moins de 5 participants une minute après l'invitation : la bascule scriptée se lance (bandeau « démonstration scriptée dans 5 s ») |
| 7:30 | V2 régie : **Lancer la demande** | l'anneau se dessine à 3/4, la demande sous l'anneau | rien ne bouge : recharger `/salle/ecran` |
| 7:45 | les oui arrivent | une ligne courbe par oui, halo rouge à l'instant, anneau vert « 4/4 » | pas de oui sur une pièce : le téléphone de secours de V2 répond « Oui » |
| 8:30 | V2 régie : **Retrait (simulé)** | la ligne se rétracte, « un composant n'est plus disponible », l'anneau se rouvre puis se referme (réserve) | — |
| 9:00 | V2 régie : **Bilan** | tableau final, compteurs, phrase « En N minutes… » | — |
| 9:20 | V2 : ⌘-Tab vers le deck | — | — |

**Plan B global de l'acte 3** : deck, slide « constellation », touche **B** : la vidéo de 30 s (séance simulée sur
le vrai écran, `review/constellation/<mode>/seance-<mode>.webm`). On dit que c'est une séance simulée.

## 3. Après l'acte 7

- Régie → **Purger** (la clé de séance tourne ; plus aucun passe ne vaut). C'est la promesse faite à la salle.
- Arrêter le tunnel (`tailscale funnel reset`, ou Ctrl-C sur cloudflared).

## 4. Captures de secours (réelles)

Dans `deck/assets/captures/` : `tel-4-decouverte.png`, `suivi-1.png`, `tel-2-recu.png`, `etabli-*` (v1). Vidéo de la
constellation : `deck/review/constellation/{nuit,jour}/seance-*.webm`. Elles sont regénérables :
`prototype/scripts/capturer_presentation.py` et `prototype/scripts/revue_constellation.py`.

## 5. Vérifications du deck v2 (faites le 03.10)

- 24 slides rendues en jour et en nuit (`deck/review/v2/{nuit,jour}`), aucune erreur JS ; seule requête en échec :
  `assets/film.mp4`, absent du dépôt (à copier sur la machine de la salle — plan B texte sinon).
- Aucune requête hors de `127.0.0.1` (deck + serveur Club Pulse pour les QR).
- Chiffres du deck : `data/gel.json` (bloc `v2`), recalculés par `prototype/tests/test_deck_v2.py`.

# 04 v2 — Runbook de la démo (deck v2, 18 min)

La démo publique tourne **sur le Mac du pitch**, exposée en HTTPS par un tunnel ([DEMO_TUNNEL.md](../DEMO_TUNNEL.md)).
Le runbook v1 ([04_DEMO_RUNBOOK.md](04_DEMO_RUNBOOK.md)) reste le plan B complet (démo Établi + téléphone).

## 0. Fenêtres et matériel

| Fenêtre / appareil | Adresse | Qui |
|---|---|---|
| Tout lancer | double-clic sur **« 1 - Lancer Club Pulse »** (racine du dépôt) : prototype, tunnel, deck, Chrome, check-list ([COMMENT_PRESENTER.md](COMMENT_PRESENTER.md)) | Hiba |
| Deck v2 (écran 1, plein écran) | `http://127.0.0.1:8765/v2.html` (ouvert par le lanceur ; ajouter `?carte=1` **seulement** si la vraie carte a fait 5/5) | V1 (télécommande) |
| Écran géant de la salle | **dans le deck**, slide « constellation » (iframe vers `/salle/ecran`) : plus de changement de fenêtre | — |
| Régie sur le Mac (onglet ouvert par le lanceur) | `http://127.0.0.1:8000/salle/regie` — y coller le jeton **une fois** ; l'onglet reste ouvert : c'est lui qui passe le jeton à l'écran intégré | Hiba, avant le pitch |
| Régie de V2 (son téléphone ou son portable) | `https://clubpulse.tailfcbc50.ts.net/salle/regie` — le même jeton, collé une fois | V2 |
| Téléphones de la salle | QR → `<PUBLIC_BASE_URL>/salle#s=…` (servi en direct : `/qr/salle.svg`) | le public |
| Téléphone de secours de V2 | le même QR, scanné avant le pitch (un participant garanti) | V2 |

## 1. Avant le pitch (H-30 min)

1. Alimentation branchée ; partage 4G prêt ; double-clic sur **« 1 - Lancer Club Pulse »** ; la check-list dit
   **« FEU VERT v2 »** (« RÉPARER D'ABORD » : la raison est écrite ; « PASSER EN v1 » : double-clic sur
   **« 3 - Passer en v1 »**, puis le runbook v1). Détail manuel : [DEMO_TUNNEL.md](../DEMO_TUNNEL.md).
2. Régie du Mac : coller le jeton (⌘-V). Régie de V2 : la même chose sur son appareil.
3. Régie → **« 1 · Ouvrir la salle (QR) »** (le lanceur a déjà réinitialisé la salle).
4. Deck v2 → slide « Sortez vos téléphones » : le QR s'affiche (sinon l'emplacement dit « QR servi en direct »).
5. Scanner le QR avec 2 téléphones de l'équipe, à travers le tunnel (4G, pas le Wi-Fi du Mac).
6. Constellation : la slide « constellation » du deck affiche l'écran en direct ; mode jour ou nuit selon la salle (touche J du deck, l'écran suit).

## 2. Pendant l'acte 3 (5:30–9:30)

| Temps | Action exacte | Ce qu'on doit voir | Plan B |
|---|---|---|---|
| 5:30 | V1 sur la slide « Sortez vos téléphones » ; **V2 régie : « 1 bis · Sortez vos téléphones »** (la minute de bascule part de là, jamais de l'ouverture à H-30) | le QR en grand | QR absent : lire l'adresse de `/qr/salle.txt` ; ou passer à la vidéo (B) |
| 5:50 | V1 passe à la slide « constellation » | l'écran de la salle, en direct dans le deck ; les points arrivent (rien sous 3 : « la constellation s'allume à trois ») | moins de 5 participants une minute après l'invitation : la bascule scriptée se lance (bandeau « démonstration scriptée dans 5 s ») |
| 7:30 | V2 régie : **« 2 · Lancer la demande vers la salle »** | l'anneau se dessine à 3/4, la demande sous l'anneau | rien ne bouge : recharger le deck (⌘-R, il revient sur la même slide) ; sinon touche B |
| 7:45 | les oui arrivent | une ligne courbe par oui, halo rouge à l'instant, anneau vert « 4/4 » | pas de oui sur une pièce : le téléphone de secours de V2 répond « Oui » |
| 8:30 | V2 régie : **« 3 · Déclencher un retrait (simulé en démonstration) »** | la ligne se rétracte, « un composant n'est plus disponible », l'anneau se rouvre puis se referme (réserve) | — |
| 9:00 | V2 régie : **« 4 · Afficher le bilan »** | tableau final, compteurs, phrase « En N minutes… » | — |
| 9:20 | V1 avance (slide suivante) | — | — |

**Plan B global de l'acte 3** : deck, slide « constellation », touche **B** : la vidéo de 30 s (séance simulée sur
le vrai écran, `review/constellation/<mode>/seance-<mode>.webm`). On dit que c'est une séance simulée.

## 3. Après l'acte 7

- Double-clic sur **« 2 - Arrêter et effacer »** : purge vérifiée (la clé de séance tourne ; plus aucun passe ne vaut —
  la promesse faite à la salle), tunnel fermé, tout arrêté, « Tout est éteint et effacé. »

## 4. Captures de secours (réelles)

Dans `deck/assets/captures/` : `tel-4-decouverte.png`, `suivi-1.png`, `tel-2-recu.png`, `etabli-*` (v1). Vidéo de la
constellation : `deck/review/constellation/{nuit,jour}/seance-*.webm`. Elles sont regénérables :
`prototype/scripts/capturer_presentation.py` et `prototype/scripts/revue_constellation.py`.

## 5. Vérifications du deck v2 (faites le 03.10)

- 24 slides rendues en jour et en nuit (`deck/review/v2/{nuit,jour}`), aucune erreur JS ; seule requête en échec :
  `assets/film.mp4`, absent du dépôt (à copier sur la machine de la salle — plan B texte sinon).
- Aucune requête hors de `127.0.0.1` (deck + serveur Club Pulse pour les QR).
- Chiffres du deck : `data/gel.json` (bloc `v2`), recalculés par `prototype/tests/test_deck_v2.py`.

# 06 v2 — Contenu des slides du deck v2

Le deck : [deck/v2.html](deck/v2.html) (même moteur et même design system que le v1 : Plus Jakarta Sans, JetBrains
Mono, rouge `#CD2128` au seul instant d'un oui, vert `#0DA254` pour « couvert », 240 / 480 / 720 ms, un seul easing).
Touches : → / ← / Espace, `J` jour/nuit, `N` noir, `R` répétition (8 repères), `B` plan B (vidéo de la constellation),
`F` plein écran. `?carte=1` ajoute la slide carte → profil (**seulement si 5/5 au rituel**). `?app=` donne l'adresse
du serveur qui sert les QR (défaut `http://127.0.0.1:8000`).

**Règles.** Chaque chiffre vient de `data/gel.json` (bloc `v2`), recalculé par `prototype/tests/test_deck_v2.py`
depuis la liste du Club, `etat.yaml` et `PREUVES.md`. Les faits externes portent leur source en petit. Aucun nom de
membre, aucune phrase Tally, aucun partenaire présenté comme acquis.

| # | id | Acte | Ce qu'on voit | Source |
|---|---|---|---|---|
| 1 | `1` | 1 | la carte de Sophie (fictive) | — |
| 2 | `matin` | 1 | « Ce matin, vous nous avez dit… » / « Cette nuit, nous l'avons construit. » | — |
| 3 | `stat` | 1 | « La statistique la plus citée du monde des salons est invérifiable. » / « personne ne mesure l'après. » | american-image.com, PREUVES « Contexte » |
| 4 | `2` | 1 | Et après ? (1/3) | — |
| 5 | `cinema` | 2 | carton « Cette année, la Foire fait son cinéma. Nous aussi. » | — |
| 6 | `film` | 2 | le film (3:21) ; plan B texte | 05_FILM_INTEGRATION |
| 7 | `8` | 2 | Et après ? (2/3) | — |
| 8 | `salle` | 3 | « Sortez vos téléphones. » + **QR en direct** (`/qr/salle.svg`) ; ensuite petit QR en coin jusqu'à l'acte 6 | serveur, PUBLIC_BASE_URL |
| 9 | `constellation` | 3 | repères de l'écran géant ; **B** = vidéo de 30 s (séance simulée) | `review/constellation/` |
| 10 | `cote-club` | 4 | carton « Et pour le Club, toute l'année ? » | — |
| 11 | `cherche` | 4 | écrans réels : passe découverte (téléphone), Suivi | captures réelles |
| 12 | `chiffres-club` | 4 | **145** entreprises, **173** représentants, **8 / 9**, la pièce qui manque (interprète) | gel.json v2 ← liste du Club (audit : les faits non vérifiés sur des membres précis sont retirés) |
| 13 | `assembler` | 4 | la grille des 9 capacités ; « Votre liste dit ce que le Club pourrait faire. Club Pulse dit ce qu'il peut faire cette semaine. » | `intelligence/assembler.py` |
| 13b | `carte-profil` | 4 | **seulement avec `?carte=1`** | règle des 5/5 |
| 14 | `science` | 5 | Flynn & Lake (~50 %), Reciprocity Ring (24 / 114), liens faibles (Science 2022) | PREUVES « Contexte » |
| 15 | `preuves` | 5 | reçu ; 80 téléphones, 0 erreur, p95 ≤ 210 ms (serveur local) ; 21 phrases Tally (agrégats, Apertus seulement) ; 1 / 26 (Apertus 1.5, CSCS) + parité | gel.json v2 ← PREUVES |
| 16 | `ou` | 6 | construit / validé / prévu (22 / 1 / 8 au 03.10) ; QR de la feuille de route en direct | gel.json v2 ← etat.yaml |
| 17 | `jalons` | 6 | 30 jours / 45 jours ; Mondiaux 1er – 14.02.2027 ; risque nommé ; critères « à valider avec le Club » | ROADMAP.md |
| 18 | `suisse` | 6 | Apertus servi par le CSCS ; e-ID swiyu dès décembre 2026 (prévu) ; Haute-Savoie à contacter, puis Vallée d'Aoste, Crans-Montana 2027 — aucun acquis | ROADMAP.md, PREUVES « Contexte » |
| 19 | `demande` | 6 | « Un pilote de 45 jours avec 50 membres volontaires parmi vos 173 représentants. » + Oui / Non / Pas cette fois | — |
| 20 | `regardez` | 7 | carton « Regardez votre téléphone : vous avez un reçu. » | — |
| 21 | `18` | 7 | la carte et le reçu réel | capture réelle |
| 22 | `19` | 7 | « La Foire crée la rencontre. Club Pulse crée l'après. » | identique au v1 |
| 23 | `20` | 7 | noir | — |
| 24 | `21` | — | repères pour les questions ; « démo servie depuis notre machine, à Martigny, via un tunnel chiffré » | DEMO_TUNNEL.md |

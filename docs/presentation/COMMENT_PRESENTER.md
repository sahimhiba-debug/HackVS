# Comment présenter — le guide (MacBook Air)

Écrit le 03.10, avant le gel, pour Hiba. Le jour J, **aucune commande à taper, aucune fenêtre à jongler.**

## La version simple

1. **Poser le film sur le Bureau** du Mac — la seule vidéo du Bureau.
2. **Double-clic sur « 1 - Lancer Club Pulse »** (dans le dossier HackVS).
3. **Coller le jeton dans la régie** quand Chrome la montre (⌘-V : il est déjà dans le presse-papiers).
4. **Attendre « FEU VERT v2 »** (dernière ligne du Terminal, ou la page qui s'ouvre), puis présenter. « RÉPARER
   D'ABORD » : la raison est écrite à côté. « PASSER EN v1 » : double-clic sur **« 3 - Passer en v1 »**.
5. **Après le pitch : double-clic sur « 2 - Arrêter et effacer »** — attendre « Tout est éteint et effacé. »

Sur papier : [carte de régie de V2](livrables/CARTE_REGIE_V2.pdf), [carte de V1](livrables/CARTE_V1.pdf),
[script v2 par intervenant](livrables/SCRIPT_v2_IMPRIMABLE.pdf).

## Ce que fait chaque double-clic

**« 1 - Lancer Club Pulse »**

- **Le film** : il cherche les vidéos posées directement sur le Bureau (`.mp4`, `.m4v`, `.mov`, pas dans les
  sous-dossiers) et en copie **une seule** dans le deck (`docs/presentation/deck/assets/film.mp4`, jamais commité).
  - Aucune vidéo → voyant rouge « FILM ABSENT DU BUREAU ».
  - Plusieurs → voyant rouge avec la liste : il ne devine jamais.
  - Une icône iCloud vide → voyant rouge : dans le Finder, clic droit sur le film → « Télécharger maintenant ».
  - Un `.mov` → orange : Chrome ne le lit pas toujours (exporter en MP4 si possible).
  - Il recopie seulement si le film a changé. Si `ffprobe` est installé, il affiche la durée et le codec.
  - Sans film, le deck (v1 comme v2) passe tout seul sur son plan B raconté : ce n'est pas une raison de changer de
    version.
- **Le jeton de la console** : créé une fois, rangé hors du dépôt (`~/.clubpulse/jeton`), copié dans le presse-papiers.
- **En arrière-plan** : le prototype, le tunnel Tailscale (`https://clubpulse.tailfcbc50.ts.net`), le serveur du deck,
  et l'anti-veille. Journaux : `~/.clubpulse/logs`.
- **Il attend** que tout réponde, **réinitialise la salle**, ouvre Chrome sur la **régie** et sur le **deck v2**.
- **La check-list** (dans le Terminal et sur `http://127.0.0.1:8000/preflight`, qui se met à jour seule) : film,
  serveur local, adresse publique (vue **depuis Internet**, comme un téléphone en 4G), deck, Mac sur secteur, salle
  réinitialisée. Dernière ligne :
  - **« FEU VERT v2 »** : tout est vert ;
  - **« RÉPARER D'ABORD »** : il manque quelque chose dont la v1 aurait aussi besoin (serveur, deck, secteur, salle) —
    la raison est écrite ; la page `/preflight` repasse au vert toute seule une fois réparé ;
  - **« PASSER EN v1 »** : seule l'adresse publique ne passe pas (le tunnel) — double-clic sur « 3 - Passer en v1 ».
- La fenêtre du Terminal attend **Entrée** avant de se fermer.

**« 3 - Passer en v1 »** : arrête le prototype du tunnel, ferme le tunnel, relance la démo v1 joignable sur le réseau
du Mac (son partage de connexion, ou le Wi-Fi), ouvre l'Établi et le deck v1, et affiche l'adresse à ouvrir sur le
téléphone de Pauline. La suite : [04_DEMO_RUNBOOK.md](04_DEMO_RUNBOOK.md) § 2.

**« 2 - Arrêter et effacer »** : réinitialise la salle et vérifie qu'elle est vide (la promesse faite à la salle),
ferme le tunnel, arrête tout, puis « Tout est éteint et effacé. ». Il ne touche jamais au film du Bureau.

**Pendant le pitch** : l'écran géant de la salle s'affiche **dans le deck** (slide « constellation ») — personne ne
change de fenêtre. S'il ne répond pas, la slide le dit : touche **B**, la vidéo de 30 s. V2 pilote la régie depuis
**son** téléphone ou portable (`https://clubpulse.tailfcbc50.ts.net/salle/regie`, même jeton, envoyé par AirDrop ou
message). L'onglet régie du Mac reste ouvert : c'est lui qui passe le jeton à l'écran du deck.

## Une seule fois, avant le jour J

1. Récupérer le code et créer l'environnement Python : [A2](#a2-récupérer-le-code-sur-le-mac).
2. Installer **Tailscale** (App Store), se connecter ; dans sa console web, activer **HTTPS** et **Funnel** pour ce
   Mac ; vérifier que le Mac s'appelle **`clubpulse`**.
3. Installer **Google Chrome**.
4. Premier double-clic : macOS demande « Terminal souhaite accéder aux fichiers de votre Bureau » → **OK** (sinon le
   film n'est pas trouvé : Réglages Système → Confidentialité et sécurité → Fichiers et dossiers → Terminal → Bureau).
   Si macOS refuse d'ouvrir le fichier (téléchargé en zip plutôt que cloné) : Réglages Système → Confidentialité et
   sécurité → en bas, **« Ouvrir quand même »** (sur macOS 14 et avant, clic droit → Ouvrir suffit).
5. Faire une répétition complète ([A6](#a6-répéter)) avec les deux double-clics.

---

# Annexe — la procédure détaillée (dépannage)

Tout ce qui suit est ce que les deux double-clics font à votre place. À n'utiliser que si l'un d'eux échoue.

## A1. Quelle version présenter

| | **v1 — le plan B** (15 min) | **v2 — la nouvelle** (18 min) |
|---|---|---|
| Deck | `docs/presentation/deck/index.html` | `docs/presentation/deck/v2.html` |
| Le cœur | le film, puis une **démo sur l'écran** : l'Établi + un téléphone d'équipe (Pauline), le reçu, le retrait anonyme, le passe découverte, Suivi | le film, puis **« Sortez vos téléphones »** : la salle scanne un QR, l'écran géant montre la constellation, V2 pilote depuis la régie ; puis le côté Club (145 entreprises, 8 sur 9), la science, la feuille de route, la demande du pilote |
| Internet | **pas besoin** : tout tourne sur le Mac et son point d'accès | **besoin** : le tunnel Tailscale rend le Mac joignable par les téléphones du jury |
| Textes | `02_STRUCTURE.md`, `03_SCRIPT_ORAL.md`, `03b_SCRIPT_A_DIRE.md`, `04_DEMO_RUNBOOK.md` | les mêmes noms avec `_v2` |

**La plus testée : la v1.**

- **v1** : deck vérifié le 01.10 (navigation complète, réseau coupé, contrastes) ; démo couverte par les tests de
  bout en bout ; captures de secours réelles ; fiches présentateur imprimées existent.
- **v2** : 24 slides rendues sans erreur en jour et en nuit (nuit du 03.10) ; le mode salle passe ses tests de bout en
  bout et un test de charge à 80 téléphones **sur une seule machine**. Mais elle n'a **jamais été répétée en entier**
  avec le vrai tunnel et de vrais téléphones, ni chronométrée : les 18 minutes sont une estimation (15–16 min de
  contenu).

Conseil : présenter la **v2** si la répétition complète (§ 6) passe sans accroc ; sinon la **v1**, qui ne dépend
d'aucun réseau.

---

## A2. Récupérer le code sur le Mac

### La toute première fois

1. Installer Python 3.11 (une fois) : télécharger l'installeur macOS sur python.org (version 3.11), double-cliquer,
   suivre. Puis, dans le Finder : Applications → Python 3.11 → double-clic sur **« Install Certificates.command »**
   (sans cela, ce Python ne vérifie aucune adresse HTTPS ; la check-list utilise de toute façon les certificats de
   `certifi`, installés avec le prototype). Si `git` manque, macOS propose de l'installer à la première commande : accepter.
2. Dans Terminal :

```sh
cd ~
git clone https://github.com/sahimhiba-debug/HackVS.git
cd HackVS
git checkout foire-2026
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r prototype/requirements.txt
```

### Les fois suivantes (mettre à jour)

```sh
cd ~/HackVS
git fetch origin
git checkout foire-2026
git pull
source .venv/bin/activate
pip install -r prototype/requirements.txt
```

- **Après la fusion de 08:00** dans `main` et le tag `gel-final` : remplacer `foire-2026` par `main` dans les deux
  blocs. Pour présenter exactement la version gelée : `git checkout gel-final`.
- **Dans chaque nouveau Terminal**, refaire `cd ~/HackVS` puis `source .venv/bin/activate`.

---

## A3. Ouvrir le deck à la main

### Le film

Copier `film.mp4` (AirDrop, clé USB) ici, avec exactement ce nom :

```
~/HackVS/docs/presentation/deck/assets/film.mp4
```

Les deux versions du deck lisent ce même fichier. Il ne va jamais dans le dépôt (ignoré par git).

### Lancer (toujours par le petit serveur, pas en double-clic)

```sh
cd ~/HackVS
python3 docs/presentation/deck/lancer.py
```

Ça ouvre le navigateur. Dans **Chrome**, taper l'adresse :

- v2 : **`http://127.0.0.1:8765/v2.html`**
- v1 : **`http://127.0.0.1:8765/index.html`**

Puis appuyer sur **F** (plein écran).

Options à ajouter au bout de l'adresse :

- `?mode=jour` : salle éclairée ;
- `?carte=1` (v2) : **seulement** si la vraie carte a fait 5/5 au rituel.

Exemple : `http://127.0.0.1:8765/v2.html?mode=jour`

**Pourquoi pas le double-clic ?** Chrome refuse alors de lire `data/gel.json`. Les slides de chiffres affichent en
rouge « data/gel.json non lu — lancer le deck avec lancer.py ». Le deck ne ment pas, mais les chiffres manquent.

**Le QR de la v2** vient du prototype (`http://127.0.0.1:8000`). Sans le prototype lancé (§ 5), la slide « Sortez vos
téléphones » affiche un cadre « QR servi en direct — lancer ./demo-tunnel.sh puis ouvrir la salle (régie) ».

### Les touches (télécommande de présentation comprise)

| Touche | Effet |
|---|---|
| → · ↓ · Espace · Entrée · Page Down · clic | avancer (étape suivante, puis slide suivante) |
| ← · ↑ · Page Up · Retour arrière · clic droit | reculer |
| **F** | plein écran |
| **J** | bascule jour / nuit pour tout le deck |
| **N** | écran noir (gris en mode jour), et retour |
| **R** | mode répétition : chrono + 8 points de contrôle en bas. **Maj+R** remet le chrono à zéro. Jamais devant le jury |
| **B** | v2 : sur la slide « constellation », lance la vidéo de secours de 30 s (séance simulée). v1 : sur la slide de démo, capture réelle de l'étape en cours |
| Début / Fin | première / dernière slide |

Après un incident, **recharger la page** (⌘-R) revient au même endroit (l'adresse garde la slide, `#14.3`).

### Si le film ne se lance pas

Sur la slide du film, le **premier clic** lance le film ; à la fin, le dernier plan reste figé ; le **clic suivant**
passe à « Et après ? ».

Si le fichier manque ou ne se charge pas en 2,5 s, la slide affiche tout seule le **plan B** : l'étiquette
« Plan B · le film ne se lance pas · on vous le raconte », puis trois phrases, une par clic :

1. « Jean-Marc est membre du Club depuis vingt ans. … Avec sa carte, et un « on s'appelle ». »
2. « Il a dit oui cent fois. Il a été rappelé trois fois. »
3. « Ce n'est pas Jean-Marc, le problème. C'est ce qui vient après le oui. »

Sans le film, tout le reste avance d'environ 1:40 : ignorer les cibles du chrono après 2:00.

---

## A4. Le pitch

### Les fichiers (dans `~/HackVS/docs/presentation/`)

| Quoi | Fichier |
|---|---|
| Script v2 complet (ce qui se dit + indications de scène) | `03_SCRIPT_ORAL_v2.md` |
| Le texte seul, à apprendre | `03b_SCRIPT_A_DIRE_v2.md` |
| **Version imprimable** : une colonne par intervenant, chronos | `livrables/SCRIPT_v2_IMPRIMABLE.pdf` (et `.html`) |
| Carte de régie de V2 · carte de V1 (une page chacune) | `livrables/CARTE_REGIE_V2.pdf` · `livrables/CARTE_V1.pdf` |
| Runbook de la démo v2 (boutons exacts de la régie, plans B) | `04_DEMO_RUNBOOK_v2.md` |
| Minutage et points de contrôle v2 | `02_STRUCTURE_v2.md` |
| Questions du jury | `07_QA_JURY.md` |
| Fiches présentateur (A4, texte à gauche, écrans à droite) | `livrables/CLUB_PULSE_FICHES_PRESENTATEUR.pdf` — **v1 seulement** (pas de fiches v2 : utiliser la version imprimable) |
| Le tunnel en détail | `../DEMO_TUNNEL.md` |

Pour régénérer la version imprimable après une modification du script :
`python3 docs/presentation/outils/script_imprimable.py`.

### Qui dit quoi (v2)

**V1 parle du début à la fin.** **V2 ne parle pas** : V2 pilote la régie et les fenêtres.

| Acte | Chrono | Durée | V1 dit | V2 fait |
|---|---|---|---|---|
| 1 · La carte | 0:00–2:00 | 2:00 | la carte, les mains levées, « Hier, vous nous avez dit… On y a travaillé jusqu'au soir. Et on a construit de quoi le savoir. », la statistique, « Et après ? » | — |
| 2 · Le film | 2:00–5:30 | 3:30 | « Cette année, la Foire fait son cinéma. Nous aussi… Il s'appelle Jean-Marc. » — silence pendant le film (3:21) — « Jean-Marc a dit oui. Et après ? » | — |
| 3 · Sortez vos téléphones | 5:30–9:30 | 4:00 | les deux gestes, « En dessous de trois… », la demande, le retrait simulé, le tableau final ; V1 passe à la slide « constellation » (l'écran géant y est en direct) | régie : **1 bis** à 5:30 → **2** à 7:30 → **3** à 8:30 → **4** à 9:00 |
| 4 · Le côté Club | 9:30–12:15 | 2:45 | Le Club cherche / invite / suit ; 145 entreprises, 173 représentants ; 8 sur 9 ; « Votre liste dit ce que le Club pourrait faire… » | manœuvre les écrans réels si on les montre en direct |
| 5 · La science et les preuves | 12:15–14:00 | 1:45 | la science de la demande ; les preuves ; « Une fois sur vingt-six » | — |
| 6 · La feuille de route | 14:00–16:20 | 2:20 | où nous en sommes, 30/45 jours, la pile suisse, **la demande au Club** | — |
| 7 · Le reçu | 16:20–17:20 | 1:00 | « Regardez votre téléphone… », phrase finale, « Merci. » | — |
| marge | 17:20–18:00 | 0:40 | on ne meuble pas ; slide 21 pour les questions | — |

### Par cœur, mot pour mot

- « **Et après ?** » (trois fois : fin de l'acte 1, après le film, avant le reçu).
- « **Cette année, la Foire fait son cinéma. Nous aussi.** »
- « **En dessous de trois, le Club ne compte pas : il protège.** » (trois **entreprises**, pas trois personnes).
- « **Un pilote de 45 jours avec 50 membres volontaires parmi vos 173 représentants.** » puis « **Oui, non, ou pas
  cette fois.** »
- « **Regardez votre téléphone : vous avez un reçu.** »
- « **La Foire crée la rencontre. Club Pulse crée l'après.** » puis « **Si Jean-Marc dit oui, c'est que c'est
  oui.** »
- Si on demande où tourne la démo : « **la démo est servie depuis notre machine, à Martigny, via un tunnel
  chiffré** ». Ajouter « le relais ne peut pas lire les données » **seulement** sur Tailscale, **jamais** sur le
  secours Cloudflare.

**Ne jamais dire** : « validé sur le terrain », « certifié », « Public AI » (dire « CSCS »), « nos utilisateurs »,
une phrase Tally, un nom de membre.

---

## A5. Les moments en direct, à la main (si un double-clic échoue)

Il faut **trois fenêtres Terminal** (⌘-N dans Terminal pour en ouvrir une). Dans chacune :
`cd ~/HackVS && source .venv/bin/activate`.

### Une fois pour toutes : Tailscale

1. Installer Tailscale (App Store), se connecter.
2. Dans la console web de Tailscale : activer **HTTPS** et autoriser **Funnel** pour ce Mac.
3. Vérifier dans le menu Tailscale que ce Mac s'appelle bien **`clubpulse`** : l'adresse sera alors
   **`https://clubpulse.tailfcbc50.ts.net`**.
4. Si la commande `tailscale` est introuvable dans Terminal : menu Tailscale → Réglages → « Install CLI » (ou
   utiliser `/Applications/Tailscale.app/Contents/MacOS/Tailscale` à la place de `tailscale`).

### Le jeton de la console

**Il n'existe nulle part à l'avance : c'est toi qui le crées**, une fois par séance. Dans le **Terminal 1** :

```sh
export HACKVS_CONSOLE_JETON="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
echo "$HACKVS_CONSOLE_JETON"
```

La deuxième ligne l'affiche : le copier dans une note sur le Mac (**jamais** dans un fichier du dépôt, jamais sur
une slide). Pour le revoir plus tard dans ce même Terminal : `echo "$HACKVS_CONSOLE_JETON"`. Un autre Terminal ne le
connaît pas : il faut l'y recoller avec `export HACKVS_CONSOLE_JETON="<le jeton>"`.

### Lancer

**Terminal 1 — le prototype** (laisser ouvert ; il empêche aussi le Mac de se mettre en veille) :

```sh
export PUBLIC_BASE_URL="https://clubpulse.tailfcbc50.ts.net"
./demo-tunnel.sh
```

Il refuse de démarrer sans jeton ou sans adresse en `https://` : c'est voulu.

**Terminal 2 — le tunnel** :

```sh
tailscale funnel 8000
```

**Terminal 3 — le deck** : `python3 docs/presentation/deck/lancer.py`, puis l'adresse du § 3.

**Vérifier** (dans le Terminal 1 bis, ou n'importe lequel avec les variables) :

```sh
curl -fsS https://clubpulse.tailfcbc50.ts.net/sante
curl -fsS http://127.0.0.1:8000/qr/salle.txt
```

La première répond ; la seconde donne l'adresse du QR (une fois la salle ouverte).

### Les écrans (dans Chrome, sur le Mac)

- **La télécommande (régie)** : `http://127.0.0.1:8000/salle/regie`. Elle demande le jeton **une fois** : coller le
  jeton. Ouvrir la régie **en premier**.
- **L'écran géant** : il s'affiche **dans le deck v2**, slide « constellation ». Il reçoit le jeton de la régie ouverte
  dans le même Chrome du Mac : garder cet onglet ouvert. (À la main, pour vérifier : `http://127.0.0.1:8000/salle/ecran`.)

Les boutons de la régie, dans l'ordre :

1. **« Réinitialiser : tout effacer »** — avant de commencer (H-30).
2. **« 1 · Ouvrir la salle (QR) »** — à H-30. Puis scanner le QR avec 2 téléphones de l'équipe **en 4G**.
3. **« 1 bis · « Sortez vos téléphones » (en séance) »** — à 5:30, sur scène. La minute de bascule automatique part
   de ce bouton, pas de l'ouverture.
4. **« 2 · Lancer la demande vers la salle »** — 7:30.
5. **« 3 · Déclencher un retrait (simulé en démonstration) »** — 8:30.
6. **« 4 · Afficher le bilan (Suivi de la salle) »** — 9:00.

Plans B :

- **Moins de 5 téléphones une minute après « 1 bis »** : une démonstration scriptée prend le relais toute seule
  (bandeau « démonstration scriptée dans 5 s »).
- **Plus rien ne marche** : revenir au deck, slide « constellation », touche **B** : la vidéo de 30 s. Dire « Voici
  ce que vous auriez vu — une séance simulée, enregistrée hier. »
- **Tailscale en panne** : le secours Cloudflare est décrit dans `docs/DEMO_TUNNEL.md` (son adresse change à chaque
  fois ; il faut relancer le Terminal 1 avec la nouvelle adresse). Avec lui, ne **jamais** dire « le relais ne peut
  pas lire les données ».

### Après le pitch : tout purger (c'est la promesse faite à la salle)

1. Régie → **« Réinitialiser : tout effacer »**.
2. Vérifier, dans un Terminal qui a le jeton et l'adresse :

   ```sh
   ./purge.sh
   ```

   Il doit afficher **« OK : salle vide. »** (Ne pas utiliser `./purge.sh --tout` : il sert au serveur de production,
   pas au Mac.)
3. Couper le tunnel : `tailscale funnel reset` (ou Ctrl-C dans le Terminal 2).
4. Couper le prototype : Ctrl-C dans le Terminal 1.

### La v1 (plan B), pour mémoire

Pas de tunnel. `make demo HOTE=0.0.0.0 URL_PUBLIQUE=http://<ip-du-Mac>:8000`, puis tout est dans
`04_DEMO_RUNBOOK.md` (Établi sur `http://127.0.0.1:8000/etabli`, téléphone de Pauline sur le point d'accès du Mac).

---

## A6. Répéter

### Répétition complète (compter 45 min)

1. [ ] `git pull` ([A2](#a2-récupérer-le-code-sur-le-mac)) ; le film sur le Bureau ; Mac **sur secteur** ; partage 4G prêt.
2. [ ] Double-clic sur **« 1 - Lancer Club Pulse »** ; coller le jeton dans la régie du Mac ; **« FEU VERT v2 »**.
   Une fois aussi : **« 3 - Passer en v1 »**, pour savoir le faire (puis « 2 - Arrêter », et relancer « 1 »).
3. [ ] V2 ouvre sa régie sur son appareil (`https://clubpulse.tailfcbc50.ts.net/salle/regie`, même jeton).
4. [ ] Régie → « 1 · Ouvrir la salle » ; deck en plein écran (F), **mode répétition (R)**.
5. [ ] Le QR s'affiche sur « Sortez vos téléphones ».
6. [ ] **3 téléphones ou plus, en 4G (pas le Wi-Fi du Mac)** : scan, deux gestes ; les points arrivent sur l'écran
   géant, **dans le deck** (slide « constellation »).
7. [ ] Jouer les 18 minutes en entier, avec les boutons 1 bis → 2 → 3 → 4 (carte de régie).
8. [ ] Le film se lance, se fige à la fin ; un téléphone affiche son reçu.
9. [ ] Noter le chrono réel de chaque point de contrôle ; si on dépasse, appliquer la coupe affichée.
10. [ ] Tester une fois la touche **B** sur « constellation » (vidéo de secours).
11. [ ] Double-clic sur **« 2 - Arrêter et effacer »** → « Tout est éteint et effacé. »

### Avant de monter sur scène (H-30)

1. [ ] Secteur branché ; notifications coupées (Concentration → Ne pas déranger) ; luminosité au maximum.
2. [ ] « 1 - Lancer Club Pulse » a dit **« FEU VERT v2 »** (la page `/preflight` le redit en direct).
3. [ ] Régie : « 1 · Ouvrir la salle » ; 2 téléphones de l'équipe ont scanné, en 4G.
4. [ ] Jour ou nuit choisi selon la salle (touche J du deck : l'écran géant suit).
5. [ ] Deck v2 à la **slide 1**, plein écran, **mode répétition éteint** (pas de barre en bas).
6. [ ] Slide du film vérifiée (pas d'étiquette « Plan B » affichée = le film est chargé).
7. [ ] L'onglet régie du Mac est resté ouvert ; V2 a sa régie et son téléphone de secours (QR déjà scanné).
8. [ ] Les deux cartes et le script imprimés.
9. [ ] Respirer. « Et après ? »

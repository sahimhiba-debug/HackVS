# Club Pulse — Design System v1.0 (figé)

> Source de vérité : les 5 planches de l'artefact Design (version `1790845074-84fa`, 01.10.2026) :
> `Cover` · `Main` (Établi 1440×810) · `Passeport` (1200×760) · `Phone-Ask` (390×844) · `Phone-Retrait` (390×844).
> Direction : « Truecaller premium » — fond gris clair, cartes blanches, aplats de marque, langage de confiance vérifié/manquant.
> Toute implémentation doit être pixel-fidèle à ces planches. En cas de doute : la planche gagne.

---

## 1. Fondations

### 1.1 Couleurs (tokens CSS à créer dans `tokens.css`)

```css
:root {
  /* Marque */
  --brand:        #CD2128;   /* rouge Club Pulse — figé (rouge Foire +5 % noir) */
  --brand-tint:   #FDEDEE;   /* fond des chips/badges rouges */
  --brand-tint-2: #FDF5F5;   /* fond des zones « manquant » */
  --brand-dash:   #EFC3C5;   /* pointillés des zones manquantes */
  --brand-muted:  #B06A66;   /* texte secondaire sur fond manquant */

  /* Encres */
  --ink:          #141923;   /* texte principal, boutons noirs, pilule nav active */
  --ink-2:        #3A414B;   /* corps de texte dense */
  --secondary:    #596273;   /* libellés, méta */
  --tertiary:     #9AA3B0;   /* méta discrète, placeholders */
  --disabled:     #C2C8D1;   /* valeurs absentes « — », chevrons */
  --faint:        #B4BBC5;   /* icônes onglets inactifs, colophons */

  /* Surfaces */
  --bg:           #F2F3F5;   /* fond d'app (desktop et mobile) */
  --card:         #FFFFFF;
  --card-sub:     #FAFBFC;   /* pieds de carte, cartes internes */
  --hover:        #F7F8FA;   /* ligne survolée */
  --chip-neutral: #F2F3F5;   /* chips neutres */
  --slate:        #1C222C;   /* en-tête « Mes données » (zone privée) */

  /* Filets */
  --hairline:     #EEF0F2;   /* séparateurs internes de carte */
  --hairline-2:   #E7EAEE;   /* bordures de barres (top bar, tab bar) */
  --hairline-3:   #F3F4F6;   /* lignes de table */
  --border-btn:   #E2E5E9;   /* boutons outline neutres */

  /* Sémantique */
  --green:        #0DA254;   /* consenti / actif — fonds pleins, médaillons */
  --green-deep:   #0A7A3F;   /* texte vert sur tint */
  --green-tint:   #E7F6EE;
  --amber:        #E8A23C;   /* « attend une décision » (pastille uniquement) */
}
```

**Monogrammes membres** (pastilles d'identité pseudonyme — paires fond/texte, jamais d'autres) :

| Membre | Fond      | Texte     |
|--------|-----------|-----------|
| M-04   | `#E6F4F1` | `#0E7569` |
| M-09 / M-11 | `#EAEAFB` | `#4F46E5` |
| M-17   | `#FCE7F0` | `#BE185D` |
| M-23   | `#FBF0DC` | `#B45309` |
| M-02 / M-06 (neutres) | `#E8E9EC` | `#596273` / `#9AA3B0` |

Attribution déterministe : `palette[hash(pseudonyme) % 5]` — un membre garde sa couleur partout, toute la session.

### 1.2 Typographie

- **Plus Jakarta Sans** 400 / 500 / 600 / 700 / 800 — tout le texte UI.
- **JetBrains Mono** 400 / 500 — uniquement : reçus `R-118-2`, IDs `C-084` / `A-118` / `M-17`, versions `v2`, extraits de journal, `⌘K`.
- `font-variant-numeric: tabular-nums` sur **tout** chiffre aligné (heures, dates, compteurs, KPI).
- Échelle (px) : `9.5` en-têtes de colonnes (800, uppercase, letter-spacing `0.07em`) · `10–10.5` labels d'onglets, méta mono · `11` badges, méta · `12–12.5` corps, clés/valeurs · `13–13.5` titres de lignes (700) · `15` titres de cartes (800) · `19–22` questions/héros téléphone (800) · `22` chiffres KPI (800) · Cover : `58` lockup.
- Letter-spacing : `-0.015em` à `-0.03em` sur les 15 px+ en 800 ; jamais positif sauf uppercase.

### 1.3 Géométrie, ombres, espacement

- Rayons : cartes `18` · carte chevauchante téléphone `20` · fiche Passeport `22` · en-têtes téléphone (bas) `28` · tuiles icône/QR `10–12` · zones manquantes `12` · pilules & boutons `999` · avatars `50%`.
- Ombres (uniquement celles-ci) :
  - carte : `0 1px 2px rgba(16,24,40,.05), 0 10px 28px rgba(16,24,40,.07)` (variante légère `0 8px 22px …,.06`)
  - carte chevauchante : `0 1px 2px rgba(16,24,40,.05), 0 12px 30px rgba(16,24,40,.10)`
  - fiche modale : `0 2px 6px rgba(16,24,40,.06), 0 28px 70px rgba(16,24,40,.18)`
  - CTA rouge : `0 6px 16px rgba(205,33,40,.30)` · bouton top bar : `0 2px 8px rgba(205,33,40,.26)` · bloc QR : `0 10px 26px rgba(205,33,40,.30)` · cercle Retirer : `0 4px 12px rgba(205,33,40,.40)`
- Grille 4 px. Paddings de carte : `≈14px 20px` desktop, `≈10px 16px` mobile. Lignes de liste : `40–44px` de haut.

---

## 2. Marque

### 2.1 La tuile-sigle (logo)

Sens : l'anneau aux ¾ fermé = une capacité à une pièce près ; le **point dans la brèche** = la pièce qui arrive ; le pouls du Club.

Construction SVG (ne pas redessiner, copier) :
```svg
<svg viewBox="0 0 24 24">
  <rect x="0.5" y="0.5" width="23" height="23" rx="7" fill="var(--brand)"/>
  <circle cx="12" cy="12" r="7" fill="none" stroke="#FFF" stroke-width="2.7"
          stroke-linecap="round" stroke-dasharray="33 11" transform="rotate(-90 12 12)"/>
  <circle cx="7.05" cy="7.05" r="1.8" fill="#FFF"/>
</svg>
```
- Déclinaisons : tuile rouge/sigle blanc (défaut) · tuile blanche/sigle rouge (sur aplat rouge ou slate) · sigle seul en cercle plein (onglet « Demandes ») · anneau de progression `3/4` (gros, blanc sur rouge) · filigrane géant (Cover : stroke `rgba(255,255,255,.08)`, point `.10`).
- Lockup : tuile + « Club Pulse » 800 + sous-ligne « Club des Affaires · Foire du Valais » 10/600 `--tertiary`.
- Le point est TOUJOURS dans la brèche (gap à 315°, arc démarrant en haut, rotation −90°). Favicon artefacts/app : la tuile.

### 2.2 Les deux aplats

- **Rouge `--brand`** = zone d'action collective (en-tête Demandes, bloc QR, Cover).
- **Slate `--slate`** = zone privée (en-tête « Mes données »).
- Tout le reste vit sur `--bg` en cartes blanches. Aucun autre aplat de couleur.

---

## 3. Langage de confiance (le cœur du système)

| Signal | Forme | Usage |
|---|---|---|
| **Consenti** | médaillon vert `--green` avec coche blanche, bord blanc `1.4`, en bas-droite de l'avatar (15–16 px) | toute pièce couverte par un accord |
| **Critique** | même médaillon en `--brand` avec `!` blanc | pièce à 1 support, sans alternative |
| **Manquant** | avatar fantôme : cercle `2px dashed var(--brand)`, `?` rouge ; zone `--brand-tint-2` bord `1px dashed var(--brand-dash)` | la pièce attendue |
| **Badge Actif** | pilule pleine `--green`, coche + texte blanc 800 (« Active », « Accord actif · reçu R-118-2 ») | capacités actives, accords |
| **Badge À une pièce** | pilule `--brand-tint`, texte `--brand` 800, pastille/`!` | capacités incomplètes |
| **Badge Dégradée** | pilule `--chip-neutral`, texte `--secondary` 700 | retrait/expiration |
| **Zéro vérifié** | « 0 » dans pilule `--green-tint` + coche verte + « tout vient de vous » | capté passivement |
| **Preuves** | reçus `R-xxx-x`, IDs `C-xxx`/`A-xxx`, horodatages — JetBrains Mono | partout où un accord est montré |

Règle : le rouge n'est jamais décoratif. Il signifie : marque, manquant, critique, Retirer. **Jamais** sur un refus (« Non » = outline neutre).

---

## 4. Composants (référence par planche)

- **Top bar** (Main) : 58 px, blanc, hairline-2 ; lockup · recherche pilule `--chip-neutral` + `⌘K` · nav (pilule active `--ink` blanche, compteur rouge sur « Demandes ») · date tabular · bouton outline « QR juré » · CTA rouge « Déclarer une offre » · avatar M17.
- **Carte KPI** : tuile 36 teintée + chiffre 22/800 (le chiffre « À une pièce » en `--brand`) + label 11 + delta en pilule teintée.
- **Carte vedette** : en-tête (badge + titre 15/800 + ID mono + fenêtre) / corps (pièces séparées par filets verticaux, la manquante en zone rouge pointillée) / pied `--card-sub` (levier `×3` rouge 800 + CTA noir).
- **Table** : chips de filtre comptés ; en-têtes de colonnes 9.5/800 uppercase ; piles d'avatars 26 px (bord blanc 2, chevauchement −8) ; statut en badge ; MÀJ relative ; une ligne `--hover` possible.
- **Rail droit** : Le Pulse (sparkline `--ink` 2.2, aire dégradée `rgba(205,33,40,.13)→0` — seule exception dégradé, point final rouge cerclé blanc, axe S D L M M J V 7.5/600 `--faint`) · Attend une décision (pastille ambre + « depuis 2 h » + Relancer noir / Acquitter gris) · Récit · IA (pastille ACTIVÉE verte, citations `[f-201]` mono, pied `MODEL_CALLED · 678 ms · chaque phrase cite ses faits`) · bloc QR rouge (QR réel : 3 carrés de repérage + modules `--ink` sur tuile blanche, « Apportez la pièce. » / « Sans compte · sans nom · 10 s » / « passe 15 min · usage unique »).
- **En-tête téléphone** : barre de statut iOS (9:41 + signal/wifi/batterie SVG blancs) · rangée app (tuile blanche + nom + chip date ou `M-17` mono) · héros centré (anneau 74 px `3/4` OU avatar 64 cerclé blanc + badge vert) · rayon bas 28 · **carte blanche chevauchante** (margin-top −16/−20).
- **Rangée d'actions rondes** (Mes données) : 3 cercles 45 px — Reçu, Exporter (blanc 12 %), **Retirer** (`--brand` plein, ombre rouge) — glyphes stroke blanc 1.7, labels 10/700.
- **Tab bar** : icônes PLEINES 21 px (sigle en cercle plein / bouclier, avec coche quand actif / cercle `?`) ; actif `--brand` label 800, inactif `--faint` 600 ; hairline-2 ; **home indicator** 134×5 `--ink`.
- **Fiche Passeport** : en-tête (anneau 4/4 vert + titre + méta `C-084 · fenêtre · levier ×3 · steward M-09` + pilule Active + ✕ SVG) ; colonnes ACCORD/EXPIRE avec reçus mono ; ligne critique en zone rouge ; barres de robustesse 7 px (rouge si 1 support) ; cartes Analyse / Récit·IA / **Simulation en pointillés** (« rien n'est écrit · jamais affiché comme réel ») ; pied : **extrait journal mono** (pastilles vertes, `16:02:11 CAPACITE C-084 → ACTIVE (4/4)`, « chaîne HMAC vérifiée ✓ ») + boutons + compteur + tuile-sceau.

---

## 5. Interdits (purgés — ne pas réintroduire)

1. Dégradés décoratifs, halos, glassmorphism, glow — seule exception : l'aire sous le sparkline.
2. Inter, Roboto, system-ui — Jakarta + JetBrains Mono uniquement.
3. Rouge sur les actions de refus ou secondaires ; plus de 1 CTA rouge par zone.
4. Émojis dans l'UI ; icônes en caractères texte (✕ › ↓) — tout en SVG.
5. Ombres dures simples (`0 2px 4px` seul) ; coins < 10 px sur les surfaces.
6. Vocabulaire « IA magique » ; afficher un hypothétique comme réel (invariant I3) ; nom ou raison lors d'un retrait (toujours « un composant n'est plus disponible »).
7. Avatars photo ou initiales réelles — monogrammes pseudonymes M-xx uniquement.

## 6. États & accessibilité

- Hover lignes : `--hover` ; focus visible : anneau `2px var(--brand)` offset 2 ; cibles tactiles ≥ 44 px ; contrastes validés (blanc sur `#CD2128` ≈ 5.9:1, `--ink` sur blanc ≥ 15:1) ; ne jamais porter un état par la couleur seule (toujours icône ou texte).

## 7. Mise en œuvre (ordre, sans casser la démo)

1. Committer ce fichier : `docs/design/DESIGN_SYSTEM.md` + créer `static/tokens.css` (§1.1).
2. Appliquer **CSS seulement** aux gabarits existants : tokens, polices (Google Fonts, fallback locale pour le mode hors-ligne salle), boutons, badges, cartes, top bar — sans toucher à la structure HTML ni à la logique.
3. Puis, si le temps le permet avant gel : médaillons de consentement sur avatars, en-têtes téléphone, extrait journal du passeport.
4. Parité IA on/off et invariants inchangés ; aucune donnée nouvelle requise par le style.

---

## 8. Mise en œuvre — état et écarts assumés (01.10.2026)

Ce qui précède est la spécification figée, recopiée telle quelle. Ce qui suit dit comment elle est appliquée dans le dépôt.

- **Tokens** : `prototype/web/pulse/tokens.css`, servi à `/static/pulse/tokens.css`. Le chemin `static/tokens.css` du § 7
  correspond à ce dossier : `/static` est servi depuis `prototype/web/`. Le fichier contient les § 1.1 verbatim, plus les
  monogrammes, les rayons et ombres du § 1.3, la tuile-sigle du § 2.1 (copiée, en data-URI) et le médaillon « consenti ».
  `pulse.css` l'importe ; les anciens noms de variables (`--encre`, `--rouge`…) pointent maintenant sur ces tokens.
- **Polices auto-hébergées, et non Google Fonts.** La CSP du serveur (`default-src 'self'`), les E2E hermétiques et le mode
  salle hors ligne bloquent toute police distante. Plus Jakarta Sans (variable 200–800) et JetBrains Mono 400/500 sont donc
  servies depuis `prototype/web/pulse/polices/` : woff2 issus de Fontsource 5.3.0, licence SIL OFL 1.1 jointe. Le rendu
  est le même et la page ne fait aucun appel réseau. Le service worker les met en cache (enveloppe `club-pulse-v2`).
- **Clair seulement.** Les planches n'ont pas de mode sombre, et la planche gagne : les surcharges sombres de l'ancien
  `pulse.css` sont retirées.
- **CSS seulement (§ 7.2).** Aucune structure HTML ni logique n'a été touchée, à trois exceptions près, toutes des valeurs
  d'attributs : `theme-color`, les couleurs du manifeste, et `icone.svg`, qui devient la tuile.
  - Les icônes en caractères de la tab bar (◉ ⧉ ＋ ◈ ✦, interdit § 5.4) sont remplacées par des icônes SVG pleines en
    masque CSS. Le texte reste dans le DOM, `aria-hidden`.
- **Pas encore fait** (§ 7.3, ces changements touchent le HTML) :
  - médaillons sur avatars monogrammes : les écrans actuels n'ont pas d'avatars ;
  - en-têtes téléphone rouge et slate avec carte chevauchante ;
  - extrait de journal du Passeport ;
  - « Oui » en CTA rouge sur le téléphone : il reste noir (`btn plein`).
- **Écarts connus**, à trancher par Hiba :
  - le bleu « accepté » de l'ancien thème n'existe pas dans la palette. Il devient une chip neutre (`--chip-neutral` /
    `--ink-2`) : l'état reste porté par le texte ;
  - l'ambre n'est plus qu'une pastille (§ 1.1) ; le texte des états « en attente » passe en `--secondary`.
- **Accessibilité mesurée — écarts aux planches, assumés (revue publique R-03 / R-04).** Le § 6 affirme « contrastes
  validés » ; mesuré dans Chromium, trois couleurs des planches échouent WCAG AA sur du petit texte :
  - libellés d'onglets inactifs en `--faint` : 1,93:1 → `--secondary` (6:1). L'icône reste `--faint`.
  - en-têtes de colonnes en `--tertiary` : 2,55:1 → `--secondary`.
  - texte secondaire en `--brand-muted` dans la zone manquante : 3,83:1 → `--brand`.

  Cibles tactiles : boutons « petit » à 36 px, champs et `summary` à 24–30 px → 44 px (§ 6). La règle est figée par
  le test navigateur `test_lisible_et_touchable_au_telephone_et_sur_les_ecrans`, et les planches devraient la suivre.
- **Ne jamais afficher ce que le produit ne prouve pas** (revue publique R-06). Les planches portent des contenus
  d'illustration qui ne sont PAS des fonctions du produit :
  - « chaîne HMAC vérifiée ✓ » : le journal n'a pas de chaîne HMAC ; il a des identifiants de faits par empreinte de
    contenu, ce qui n'est pas une chaîne ;
  - « 1 198 événements », « MODEL_CALLED · 678 ms » ;
  - « 0 capté passivement » : aucun compteur n'existe ;
  - « Répondre à une demande : 10 secondes, sans compte, sans nom » : non mesuré, et répondre exige un compte activé
    par code d'invitation — seul le passe juré est sans compte.

  Implémenter le § 7.3 « pixel-fidèle » ne doit pas les reproduire tels quels. Chaque chiffre ou badge affiché vient
  du journal, ou n'est pas affiché.
- **Couverture (décision D1 de Hiba, 01.10)** : « 0 capté passivement » → « Lire ne capte rien : aucune écriture sans
  geste » ; « Répondre à une demande : 10 secondes, sans compte, sans nom » → « Répondre : trois boutons · passe juré
  15 min, sans compte ». Chaque formulation a son test (`docs/audit/CLAIMS.md` n° 28–29). La durée ne revient qu'après
  chronométrage (§ 9.5 du script de démo, la pire de 3 mesures). Report sur la planche Cover : à faire à la main.
- **Vérifié** sur ce changement :
  - 1239 tests ;
  - E2E 16/16, en réseau normal et en mode salle (réseau local seul, IA OFF) ;
  - aucune requête externe : `requestfailed` vide et polices chargées (`document.fonts.check`) dans Chromium.

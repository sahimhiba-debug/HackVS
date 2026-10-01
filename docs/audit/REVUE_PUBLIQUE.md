# Revue publique avant la finale — 01.10.2026

> Posture : cinq ingénieurs seniors relisent le dépôt en public et cherchent ce qui peut être attaqué. Règle appliquée :
> aucune modification sans preuve, et seulement ce qui rend le produit plus robuste. Chaque correctif a son test rouge
> d'abord, sa contre-épreuve et son propre commit.
>
> Vérification finale sur `0fdd4dc` :
> - `make secrets lint typecheck` : vert ;
> - **1 246** tests ;
> - **17/17** E2E, en réseau normal et en mode salle (réseau local seul, IA OFF).
>
> Constats antérieurs : [SENIOR_ENGINEERING_FINDINGS.md](SENIOR_ENGINEERING_FINDINGS.md) (F01–F40). Cette revue numérote
> **R-01 à R-15** et ne recopie pas ce qui y est déjà.

## Synthèse

| Gravité | Trouvés | Corrigés | Restants |
|---|---|---|---|
| CRITICAL | 0 | — | — |
| HIGH | 2 | 1 (R-01) | R-06 : la base de code est protégée ; le deck reste à trancher par Hiba |
| MEDIUM | 5 | 3 (R-02, R-03, R-04) | R-08 (en cours), R-09 (mesure en cours) |
| LOW / INFO | 8 | 2 (R-05, R-07) | 6, dits ci-dessous, sans effet sur une garantie démontrée |

Aucun CRITICAL : aucune fuite de données, aucun contournement d'autorisation, aucune perte d'état trouvés, malgré une
recherche ciblée.
- Front : aucun `innerHTML` ; tout passe par un constructeur DOM qui crée des nœuds texte.
- Console : réservée à la machine locale, ou exige un jeton comparé en temps constant.
- Pages : CSP par empreintes.
- Requêtes : corps limités à 64 Kio.
- Sessions et passes : signés HMAC.
- Image Docker : utilisateur non-root.
- Dépendances : versions exactes (`constraints.txt`), `pip-audit` en CI.

## Constats

### HIGH

**R-01 — Les vrais téléphones ne pouvaient pas joindre la démonstration** · CORRIGÉ `ab9c07a`
- *Preuve.*
  - `DEMO_SCRIPT` prévoit « téléphones sur son point d'accès » et un juré qui scanne un QR.
  - Mais `make demo` écoutait `127.0.0.1`.
  - Le QR encodait l'adresse vue par l'Établi : `http://127.0.0.1:8000/app?jure=…`, qu'un téléphone prend pour
    lui-même.
  - `HACKVS_URL_PUBLIQUE` existait, documentée seulement pour l'ancien prototype.
- *Correctif.*
  - `make demo HOTE=0.0.0.0 URL_PUBLIQUE=http://<ip-du-portable>:8000` ; le défaut est inchangé, rien n'est exposé.
  - Test rouge : `test_demo_salle_telephones.py`.
  - Contre-épreuve : un autre appareil reçoit 403 sur la console.
- *Vérifié en direct* (serveur sur `0.0.0.0`, atteint par l'adresse réseau) :
  - `/app` répond 200 au « téléphone » ; la console lui répond 403, et 200 au portable ;
  - dans Chromium, Sophie s'active par code ;
  - le lien juré ouvre « Jury : vous jouez Markus ».
- `DEMO_SCRIPT` § 2, § 8 et rituel § 9.5 : ajout d'un contrôle avec un vrai téléphone et le QR juré.

**R-06 — Les maquettes portent des affirmations que le produit ne prouve pas** · CLÔTURÉ côté code, deck à trancher
- *Preuve.*
  - Planche Passeport : « chaîne HMAC vérifiée ✓ ». Le journal n'a pas de chaîne HMAC : `plateforme/memoire.py` donne
    des identifiants de faits par empreinte de contenu, sans chaînage.
  - Planches : « 1 198 événements », « MODEL_CALLED · 678 ms ».
  - Couverture : « 0 capté passivement ». Aucun compteur n'existe.
  - Couverture : « Répondre à une demande : 10 secondes, sans compte, sans nom ». Non mesuré, et faux pour
    « sans compte » : répondre exige un compte activé par code d'invitation ; seul le passe juré est sans compte.
- *Correctif (code).* `DESIGN_SYSTEM.md` § 8 : chaque chiffre ou badge affiché vient du journal, ou n'est pas
  affiché. Le § 7.3 « pixel-fidèle » ne doit pas les reproduire.
- *Reste — décision de Hiba.* La couverture sert de diapositive : retirer « sans compte » et « 10 secondes », ou les
  mesurer. Ce dernier point peut se faire au rituel de samedi, chronomètre en main.

### MEDIUM

**R-02 — Mémoire du serveur sans borne via les limiteurs** · CORRIGÉ `e0f6545`
- *Preuve.*
  - Chaque clé jamais vue restait en mémoire pour toujours : 10 000 clés inventées toujours présentes après leur
    fenêtre.
  - `POST /api/pulse/jure` n'avait aucun plafond global : 310 passes inventés, 310 × 401 et jamais 429.
  - Un client non authentifié du réseau de la salle faisait donc croître la mémoire à la vitesse de ses requêtes.
- *Correctif.*
  - Purge des clés expirées une fois par fenêtre ; la mémoire est bornée par le débit × la fenêtre.
  - Plafond global doux de 300/min sur `/jure`, la même règle que `/acces` (jamais par IP).
  - Contre-épreuve : une clé encore dans sa fenêtre reste freinée.

**R-03 — Contraste insuffisant, introduit par l'application littérale des planches** · CORRIGÉ `e67b20f`
- *Preuve* : mesure WCAG dans Chromium, sur le fond effectif.

  | Élément | Couleur des planches | Contraste |
  |---|---|---|
  | Libellés d'onglets inactifs | `--faint` | 1,93:1 |
  | En-têtes de colonnes de la console | `--tertiary` | 2,55:1 |
  | Texte de la zone manquante | `--brand-muted` | 3,83:1 |

  Le § 6 de la spécification affirme pourtant « contrastes validés ».
- *Correctif.*
  - `--secondary` (6:1) pour les libellés et les en-têtes ; `--brand` pour la zone manquante. Les icônes restent
    `--faint`.
  - Écarts aux planches écrits dans `DESIGN_SYSTEM.md` § 8.

**R-04 — Cibles tactiles sous 44 px au téléphone** · CORRIGÉ `e67b20f`
- *Preuve.*
  - Boutons « petit » à 36 px, dont « Proposer à partir de mon texte », sur le parcours de démonstration.
  - Champs et `summary` à 24–30 px.
- *Correctif.* 44 px minimum.
- *Test rouge* (pour R-03 et R-04) : `test_e2e_pulse.py::test_lisible_et_touchable_au_telephone_et_sur_les_ecrans`.
  Il mesure contrastes et cibles sur chaque onglet du téléphone, sur `/etabli` et sur `/console`.
- *Contre-épreuve* : un bouton remis à 36 px fait rougir le test.

**R-08 — La campagne de mutation GitHub n'a plus abouti depuis le run #4** · EN COURS `953073f`
- *Preuve.*
  - Runs #7 à #10 annulés par la concurrence (une poussée plus récente).
  - Run #11 coupé par la limite de 150 min. La sélection a grandi : les tests F26, F31, F32 et R3 construisent le
    monde de démonstration.
  - Le chiffre public (1 229 / 1 327) repose donc aujourd'hui sur la campagne LOCALE (`0fa7620`).
- *Correctif.* Limite portée à 330 min (sous le plafond GitHub de 360). Campagne relancée par la poussée de
  `953073f`.

**R-09 — Mutation de `essai.py` (F37) incomplète** · MESURE EN COURS
- La campagne locale a été interrompue deux fois par un redémarrage du conteneur de travail, puis reprise : mutmut
  garde ses résultats.
- Partiel à 13:00 : 2 643 / 3 528 ; 1 639 tués, 937 survivants non classés, 67 sans test.
- Les chiffres définitifs iront, bruts, dans `VAGUES_CORRECTIONS` § 4.1 et `PREUVES`. Aucune classification de masse
  avant le gel.

### LOW / INFO

| ID | Constat (preuve) | État |
|---|---|---|
| R-05 | `/projection` et `/demo/regie` servis SANS CSP, alors que les empreintes de leurs scripts étaient calculées | CORRIGÉ `e37f31e` (test étendu à chaque page ; Chromium : aucune violation, les 3 cadres de la régie s'affichent) |
| R-07 | README : « 15 E2E » et « 1 197 / 1 299, 102 survivants » contre 17 et « 1 229 / 1 327, 98 » dans le dépôt ; `THREAT_MODEL` S3 disait la console ouverte au réseau local | CORRIGÉ `0fdd4dc` (chiffres dérivés du dépôt, figés par `test_readme.py`) |
| R-10 | `PREUVES.md` daté du 30.09 (« 514 réussis ») | à rafraîchir au gel, comme prévu (chiffres finaux) |
| R-11 | Titre OpenAPI hérité « Le Fil du Club » v0.2.0 | INFO : `/docs`, `/openapi.json` et `/redoc` répondent 404 ; jamais visible |
| R-12 | La régie passe des sessions de membres dans l'URL de ses cadres (`/app?session=…`) | ACCEPTÉ. L'application les retire de l'URL au chargement (`history.replaceState`) et `Referrer-Policy: no-referrer`. Les sessions viennent de la console, réservée à la machine locale |
| R-13 | Téléphones en HTTP local : pas de service worker, donc pas d'enveloppe hors ligne | INFO, dit dans `DEMO_SCRIPT` § 2. Aucune API de l'application n'exige un contexte sécurisé (vérifié) |
| R-14 | Lancer `uvicorn` à la main dans un dépôt où le modèle sémantique est téléchargé charge e5-large (≈ 1,6 Go, démarrage lent) | INFO : `make demo` et la CI posent `HACKVS_SEMANTIQUE=0` (démarrage mesuré : 4 s) |
| R-15 | `Limiteur` de `/acces` : les clés n'étaient jamais oubliées, borné seulement par le plafond global | couvert par le correctif R-02 |

## Mesures (pas des suppositions)

- **Démarrage** (`make demo`, journal fichier) : 4 s jusqu'au premier 200.
- **Lectures courantes** : 5–10 ms. Première projection des capacités : 0,9 s à froid, puis 5 ms (cache par comptage
  du journal).
- **Rafraîchissements** : Établi toutes les 1 s, écran commun toutes les 0,7 s, chacun en millisecondes : aucun
  risque de saturer le verrou du monde.
- **Front** : aucune requête externe (`requestfailed` vide) ; polices auto-hébergées chargées.

## Reporté sciemment (déjà au registre, non bloquant pour la démonstration)

- F02 : `docs/ARCHITECTURE.md` décrit l'avant-pivot (le README le signale).
- F05 : charges d'événements non typées.
- F06 : `Banc`, 1 247 lignes.
- F08 : classement des routes sans écran.
- F10 : quatre tests d'absence.
- F11 / F16 : héritage co-résident.
- F17 : contrat de configuration du rejeu.
- F38 à F40.

Chacun est une dette réelle. Aucun ne touche une garantie montrée en scène, et les corriger à la veille du gel
coûterait plus de risque que de robustesse.

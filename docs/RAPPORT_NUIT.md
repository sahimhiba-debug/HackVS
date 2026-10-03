# Rapport de la nuit du 3 au 4 octobre 2026 — « Foire 2026 »

Branche `foire-2026`. Travail commencé le 03.10 à 13:52, **terminé le 03.10 vers 15:30** — bien avant l'arrêt
impératif de 07:30. Plan et statut heure par heure : [NUIT.md](NUIT.md). Toutes les nouveautés sont derrière
l'interrupteur `HACKVS_FOIRE` (allumé par défaut ; `HACKVS_FOIRE=0` rend le produit d'hier, à l'identique).

## 1. Fait / non fait / abandonné

| Lot | État | Commit(s) | Remarque |
|---|---|---|---|
| C — anonymat à petite échelle (k = 3), nouveau message de retrait | ✅ fait | `65d507d`, `e778d6e` | le rôle « transport » n'est plus dit (1 porteur) |
| A — Suivi (console `/suivi`) | ✅ fait | `ff68046`, `5d9adb7`, `bb4bf02` | agrégats, k = 3, canari « aucune donnée personnelle », double accord pour le nominatif |
| B — clôture de reçu, machine à états explicite | ✅ fait | `ff68046` | **écart de méthode : A et B dans le même commit** (routes communes) |
| D — passe découverte 90 jours | ✅ fait | `a880d01` | signé, usage unique, révocable, limité, 3 demandes, scénario « exposant invité d'Annecy » en E2E |
| E — « Le Club cherche » + inviter un contact FR / DE | ✅ fait | `ee8f0d7`, `eefd1a7` | liste d'entreprises : comptes seulement ; **fichier `docs/data/entreprises.csv` absent du dépôt** → « non fournie » à l'écran |
| I — `docs/roadmap/*` | ✅ fait | `f33b60a` | six documents, tableau daté |
| J — présentation (03, 03b, 02, 06 + deck, 07, 04) | ✅ fait | `e1c6576`, `b2b6eb9` | deck : slides 11S et 18b ; captures réelles ; PNG jour / nuit ; AA 0 échec ; fiches et PDF régénérés |
| F — membre à distance, réponse depuis l'e-mail | ✅ fait | `da23a2a`, `7ca7be7` | envoi **simulé en démonstration** (boîte de sortie, aucun SMTP) ; chaînes DE : e-mails et page de réponse, pas l'écran de demande du téléphone |
| G — `make bilan` | ✅ fait | `2d2d6de` | récit IA vérifié par le code ; **aucun récit Apertus réel généré** (testé avec un faux fournisseur) ; tests écrits juste après le code, leur pouvoir de détection démontré par sabotage |
| H — pipeline Tally, taxonomie, harnais | 🟡 partiel | `3ae1d9c` | tout le code et la mesure Apertus sur les 26 cas ; **les 21 réponses Tally ne sont pas dans le dépôt** (ni sur une autre branche) : non ingérées |
| Abandonné | — | — | rien |

Correctifs trouvés en route (chacun avec son test rouge d'abord) : une demande rouverte par un retrait disparaissait
de Suivi et de « le Club cherche » (`5d9adb7`) ; « null » affiché dans Suivi (`bb4bf02`) ; interrupteur éteint, deux
404 dans la console du navigateur qui auraient rendu rouge le job E2E de la CI (`7ca7be7`).

## 2. Chiffres de fin de nuit (mesurés sur le dernier commit)

| Contrôle | Résultat |
|---|---|
| `make lint` · `make typecheck` · `make secrets` | propres (87 fichiers typés) |
| `make test` (hors E2E) | **1 434 tests verts** (1 363 au début de la nuit) |
| `make e2e`, interrupteur allumé (défaut, comme la machine de démo) | 25 / 25 |
| `make e2e-salle` (réseau coupé, IA éteinte) | 25 / 25 |
| `HACKVS_FOIRE=0 make e2e` (le produit d'hier) | 25 / 25 |
| Vérification du deck (`outils/verif_deck.py`, `verif_jour.py`) | contraste AA 0 échec en jour et en nuit, 0 erreur JS, 0 requête externe |
| `validate_competition_claims.py --verifier` | aucun chiffre non prouvé dans le pitch |
| **CI GitHub** | **verte jusqu'à `bb4bf02` ; depuis `e1c6576`, les jobs ne démarrent pas** — refus de GitHub : « recent account payments have failed or your spending limit needs to be increased ». Ce n'est pas un échec du code ; à régler dans *Settings → Billing & plans* avant le gel. |

## 3. Claims ajoutées

CLAIMS n° **41 à 65** (25 nouvelles lignes), plus la mise à jour des n° 9 (compteurs) — toutes de classe A sauf la
mesure Apertus (B). PREUVES : une section « Foire 2026 » avec les seules mesures de la nuit (classification Apertus
des 26 cas : 25 / 26 sorties acceptées, 8 abstentions, 1 rejet ; langues des 26 cas ; Tally non ingéré).

## 4. Ce qui est simulé (étiqueté à l'écran ET dans CLAIMS)

- **Le monde** : 150 profils fictifs, horloge simulée — « monde de démonstration » sur Suivi, « Le Club cherche », la
  boîte de sortie, le passe découverte, la page de réponse, les bilans, la slide 11S.
- **L'envoi d'e-mails** : aucun ; la boîte de sortie montre ce qui partirait (CLAIMS n° 59).
- **La suite d'une intention d'adhésion** : « un membre de la commission vous écrit » est simulé (CLAIMS n° 52).
- **Le délai médian** : en jours de l'horloge du monde.

## 5. Prévu ensuite (non fait, dit comme tel)

Pilote avec les membres réels ; annotation humaine du jeu Tally (colonnes `metier_attendu`, `domaine`) puis mesure
d'exactitude ; écran de demande du téléphone en allemand ; vrai envoi d'e-mails (fournisseur suisse, nLPD) ;
adhésion croisée ; analyse d'impact nLPD / RGPD — voir [roadmap/ROADMAP.md](roadmap/ROADMAP.md).

## 6. Décisions prises seul cette nuit (à valider)

1. **k = 3 appliqué strictement** à tout décompte de personnes : sur scène, Suivi affiche « invités ayant contribué :
   < 3 », pas « 1 invité a contribué » comme le disait le scénario. La règle de confidentialité passe avant la réplique ;
   le script dit « moins de trois ».
2. **Le demandeur des capacités du registre est le Club** : la clôture d'un reçu se fait depuis la console.
3. **Une proposition d'invité ne remplit jamais une capacité** : « Le Club cherche » affiche « un invité propose son
   aide — à confirmer par le Club » (le manque comblé, confirmé par une personne).
4. **« Inviter un contact »** (passe lié à la demande du minibus) plutôt que le QR générique du stand pour la scène :
   le juré répond à la demande que le Club n'arrivait pas à couvrir.
5. **Phrases Tally hors dépôt** (`prototype/data/eval/`, `docs/data/tally_phrases.csv` ignorés par git) et feuille
   d'annotation dans `prototype/var/` : seuls les agrégats sont versionnés.
6. Le re-minutage (acte 6 : 2:10, marge 0:20) est une **estimation** (130 mots/min) — **pas chronométré**.

## 7. Trois risques pour le pitch, et leur parade

| Risque | Parade |
|---|---|
| Le QR du passe découverte n'ouvre rien sur le téléphone du juré (Wi-Fi de la salle, `HACKVS_URL_PUBLIQUE` absent) | COUPE PRÉVUE nommée dans 02 et 04 : on saute l'étape, la démo reste celle d'hier ; secours : captures `tel-4-decouverte.png`, `suivi-2-propose.png` |
| Le minutage déborde (acte 6 allongé, marge de 20 s) | point de contrôle à 8:40 dans le mode répétition du deck (`R`) : passé 8:40, on saute le passe découverte ; à 11:40, trois chiffres sur cinq |
| Un juré demande « combien d'invités ? » et l'écran dit « < 3 » | c'est la règle, et c'est la réponse : « sous trois personnes, l'écran ne compte pas — dans un club de cinquante, un chiffre désignerait quelqu'un » (07_QA) |

## 8. Ce qu'Hiba doit vérifier au rituel de 08:00, avant de poser le tag

1. **CI** : régler la facturation GitHub (*Billing & plans*), relancer la CI sur la tête de `foire-2026` et attendre
   le vert (jobs `qualite`, `salle`, `reproductibilite`, `dependances`). Sans CI verte, ne pas annoncer « CI verte ».
2. **Sur la machine de démo** : `make e2e` puis `make e2e-salle` (25 / 25 chacun) ; `/etabli`, `/suivi` et un téléphone
   réel sur le point d'accès.
3. **Le passe découverte sur un vrai téléphone** (étape 9 du runbook) : scanner « Inviter un contact », déclarer,
   « Je peux aider », voir « à confirmer par le Club ». Si ça n'ouvre rien : décider de la coupe (on la joue sans).
4. **Chronométrer l'acte 6** une fois (deck, touche `R`) et noter le temps dans 02_STRUCTURE.
5. **Le CSV Tally** : s'il doit compter, le déposer en `docs/data/tally_phrases.csv` (hors dépôt, ignoré par git),
   lancer `make ingest-tally` puis `make eval-classification FOURNISSEUR=apertus` ; seuls des agrégats sortent.
6. **Le film** : `docs/presentation/deck/assets/film.mp4` n'est pas dans ce clone (LFS / machine locale) — vérifier
   qu'il est sur la machine de la salle.
7. **Le tag** — depuis une machine qui a le droit de pousser des tags (le proxy de la session cloud les refuse, 403) :

   ```sh
   git fetch origin foire-2026 && git checkout foire-2026 && git pull
   git tag -a gel-final -m "Gel final — Foire 2026" && git push origin gel-final
   ```

   Après le tag, plus un seul commit.

Mutation : aucun chemin surveillé par les campagnes (`capacites.py`, `essai.py`, `test_capacites*.py`,
`test_banc_finalite.py`, `mutation.yml`…) n'a été touché cette nuit ; aucun déclencheur n'a été désactivé.

---

# Vagues 2 et 3 (03.10, 15:47 → nuit) — message consolidé, liste du Club, pas de VPS

Branche `foire-2026`. Aucun tag posé, rien poussé sur `main` (et `main` n'existe pas sur le dépôt distant : la base de
l'audit est `3a6ef4f`, point de départ commun avec `claude/modest-bohr-xvk53n`). **CI : ne démarre plus**, refus de
GitHub (facturation : « recent account payments have failed or your spending limit needs to be increased »). Aucun
commit de cette nuit n'est dit « CI verte ». Les preuves sont les portes **locales**, ci-dessous.

## Portes locales (commit `51d406a`, final de la nuit)

CI : **n'a pas tourné** (facturation, gérée par Hiba). Aucune ligne ci-dessous n'est « CI verte » : ce sont des
portes lancées sur cette machine.

| Porte | Résultat |
|---|---|
| Suite complète (`make test`, hors E2E) | **1 572 réussis**, 0 échec (sur `51d406a`) |
| E2E interrupteur allumé (`make e2e`) | **31 / 31** (sur `8d83954` ; depuis, seuls un test unitaire et des docs ont changé) |
| E2E interrupteur éteint (`HACKVS_FOIRE=0 make e2e`) | **31 / 31** (idem, `8d83954`) |
| E2E réseau coupé (`make e2e-salle`, espace réseau vide) | **31 / 31** (idem, `8d83954`) |
| Lint (`make lint`) · types (`make typecheck`) | propres · 0 erreur (102 fichiers) |
| Secrets (`make secrets`) | **aucun** (le faux secret du test de la porte est assemblé hors du motif, `51d406a`) |
| Validateur des affirmations (`--sans-benchmark --verifier` et passe complète) | « toutes les affirmations contrôlables sont vérifiées » |

## Fait

| Bloc | Quoi | Commits |
|---|---|---|
| P0 mode salle | QR multi-usage, deux gestes, écran géant, régie, bascule scriptée, purge ; **constellation en motion design** (spirale HMAC, anneau 3/4 → 4/4, halo rouge au seul instant du oui, retrait, tableau final, jour / nuit, 59–61 i/s mesurées, vidéo de 30 s en plan B) | `a0d1e46`, `730caac` |
| Liste du Club | CSV (colonne métier seule) ; **seuil « < 3 » en entreprises distinctes** ; 25 métiers ; « Ce que votre Club pourrait assembler » **8/9** ; 145 / 173 partout ; demande finale | `74cbc6b`, `493b977`, `de2d3e4` |
| Pas de VPS | démo sur le Mac via tunnel (Tailscale Funnel ; Cloudflare en secours) ; **console fermée aux requêtes relayées** ; QR servi en direct ; `--base-url` ; `demo-tunnel.sh` exige le jeton | `97763e7`, `ee5dea5`, `24876cb`, `5ef41c4` |
| P1 présentation v2 | deck v2 (24 slides, chiffres recalculés par test), structure 18 min, script + à dire, runbook, contenu des slides, Q&R ; v1 intacte en plan B | `24ba47c`, `57056b5` |
| P1 feuille de route | 30 / 45 jours, pilote au plus fort des Mondiaux, risque nommé, CSCS, pistes « à contacter » | `cb9ccb1`, suivants |
| P3 n°1–16 | voir `docs/NUIT.md` (statut 17:55) ; n°6 **bloqué** (feuille d'annotation non remplie : aucune exactitude ne peut être mesurée honnêtement) | |

## Mesures nouvelles (toutes dans PREUVES.md)

- Appel d'outils natif d'Apertus 1.5 (CSCS), mêmes 26 cas : **1/26, aucun gain**, 3 sorties fausses acceptées → interrupteur éteint.
- Pipeline d'affinage : essai réel de 10 générations, **9 gardées** par le filtre aller-retour ; **aucun entraînement lancé**.
- Carte → profil : règle des 5/5 — carte fictive k1 **0/5**, k6 **5/5** ; la vraie carte reste à essayer au rituel.

## Écarts assumés (à valider)

- **Monde de démonstration non re-proportionné** sur la liste du Club (addendum, point 6) : ses 150 profils portent les
  vérités plantées dont dépendent des dizaines de tests et les bancs mesurés. Le refaire la veille du gel mettait la démo
  en risque. Les proportions de la liste sont utilisées là où elles comptent sans risque : « assembler », « le Club
  cherche », pondération des données synthétiques.
- **Film à 3:21** (verrouillé) au lieu du créneau 2:00–4:30 du brief : les actes suivants glissent d'environ 55 s, fin
  toujours à 18:00 (estimation, pas encore chronométrée).
- **Routage vers les membres jamais liés** : hypothèse non branchée (une demande va à une catégorie, jamais à une
  personne choisie par le système).
- Termes DPV de l'export 27560 choisis sans accès à la spécification (site bloqué depuis la session) : à relire.

---

# Audit (sous-agent à contexte neuf, branche `audit-nuit`, commit `db91fde`)

Audité : `e2b1745` (diff depuis `3a6ef4f`). Rapport complet : [audit/AUDIT_NUIT.md](audit/AUDIT_NUIT.md). Verdict de
l'auditeur : « ne pas geler en l'état » — **1 BLOQUANT, 8 IMPORTANT, 12 MINEUR**. Les 5 tests rouges de l'auditeur sont
rapatriés sur `foire-2026` et désormais **verts**.

| # | Gravité | Constat | Réponse | Commit |
|---|---|---|---|---|
| 1 | BLOQUANT | l'écran géant partait sur `/etabli` avant l'acte 3 (minute de bascule comptée depuis l'ouverture à H-30) | corrigé : la minute part de l'invitation en séance (régie « 1 bis · Sortez vos téléphones ») ; test rouge d1 vert | `6135c98` |
| 2 | IMPORTANT | jeton de la salle public à travers le tunnel (`/qr/salle.*`) | corrigé : servi à cette machine ou avec le jeton de console seulement ; d5 vert | `37dfc23` |
| 3 | IMPORTANT | nom d'entreprise de l'invité dans le journal ; pas de retrait possible | corrigé : nom en mémoire seule, clé HMAC au journal ; route `/decouverte/retirer` ; d2 vert | `2c644f5` |
| 4 | IMPORTANT | seuil des invités compté en passes | corrigé : entreprises distinctes ; d3 vert | `2c644f5` |
| 5 | IMPORTANT | chiffre d'annonce réattribué après effacement | corrigé : compté sur tout le journal ; d4 vert | `49d08ce` |
| 6 | IMPORTANT | `make secrets` rouge (faux positifs) alors que le rapport le disait propre | corrigé avant l'arrivée du rapport ; la ligne du rapport reflète maintenant une porte réellement verte | `b25b00c` |
| 7 | IMPORTANT | le vérificateur d'affirmations ignorait deck v2 et script v2 | corrigé : formulations interdites + nombres dits sans source | `5536d88` |
| 8 | IMPORTANT | slide « Votre Club en chiffres » : faits non vérifiés sur des membres précis | retirés de la slide, du script et du contenu des slides | `dad7004` |
| 9 | IMPORTANT | acte 3 : « vraie demande » écrite en dur ; retrait simulé qui retirait un vrai consentement | « demande type, écrite pour cette démonstration » ; retrait dit simulé ; il ne retire plus aucun consentement (le fournisseur repasse en réserve) | `c44195d`, `dad7004` |
| 13, 14, 16, 17, 18 | MINEUR | libellés du runbook, `purge.sh` sans `.env`, « mois 1 à 3 », étiquette « Personnage fictif », décompte Tally de 1 | corrigés | `8d83954` |
| 10 | MINEUR | la suite historique tourne interrupteur éteint ; 2 tests historiques échouent allumés (masquage voulu du rôle) | **non corrigé** — fichiers surveillés par les campagnes de mutation (`test_capacites*`), interdits ; à adapter après le gel | — |
| 11 | MINEUR | en salle, k porte sur des passes (pas d'entreprise ; un téléphone peut scanner plusieurs fois) | **dit, non corrigé** : la salle est anonyme par construction (aucune entreprise demandée) ; plafond 80, purge après | — |
| 12 | MINEUR | acte 2 peut déborder de 5 à 15 s | **dit** : à chronométrer au rituel (mode `R`) ; marge 0:40 | — |
| 15 | MINEUR | §§ 1–8 de ce rapport (vague 1) parlent encore de « personnes » et de « cinquante » | **laissé** : section historique de la vague 1, datée ; les vagues 2 et 3 font foi | — |
| 19 | MINEUR | monde « visite » : console ouverte sans jeton | **dit** : bac à sable fictif, conteneur à part ; non déployé (pas de VPS) — à régler avant tout déploiement | — |
| 20 | MINEUR | en salle, la déclaration dit « révocable » mais on ne retire qu'après un oui | **à faire** après le gel (la purge efface tout après la présentation) | — |
| 21 | MINEUR | la carte appelle le fournisseur hors du chemin `ia.repondre` (pas de quota IA par membre) | **à faire** après le gel (limite de 10 propositions / min en place) | — |

---

# Pour Hiba

## À fournir pour la démo (pas de VPS)

| Quoi | Où |
|---|---|
| Le Mac du pitch, Python 3.11, le dépôt à jour (`foire-2026`, puis `main` après fusion) | `pip install -r prototype/requirements.txt` |
| Tailscale installé et connecté ; HTTPS et Funnel autorisés pour ce Mac dans la console du tailnet | `docs/DEMO_TUNNEL.md` |
| `cloudflared` en secours (`brew install cloudflared`) | idem |
| Un jeton de console | `python3 -c 'import secrets; print(secrets.token_urlsafe(24))'` |
| (Facultatif) `APERTUS_API_KEY` du CSCS dans l'environnement — jamais dans un fichier du dépôt | la démo tourne sans |
| `film.mp4` dans `docs/presentation/deck/assets/` sur la machine de la salle | sinon plan B texte |

## Commandes (session locale sur le Mac)

```sh
git fetch origin && git checkout foire-2026 && git pull
export HACKVS_CONSOLE_JETON="<jeton>" PUBLIC_BASE_URL="https://<mac>.<tailnet>.ts.net"
./demo-tunnel.sh                       # terminal 1 : serveur sur 127.0.0.1:8000, caffeinate
tailscale funnel 8000                  # terminal 2 : le tunnel
python3 docs/presentation/deck/lancer.py   # terminal 3 : deck → http://127.0.0.1:8765/v2.html (v1 : index.html)
curl -fsS "$PUBLIC_BASE_URL/sante" && curl -fsS http://127.0.0.1:8000/qr/salle.txt
cd prototype && python scripts/charge_salle.py --base-url "$PUBLIC_BASE_URL" --jeton "$HACKVS_CONSOLE_JETON" --n 80
```

## Liste de 08:00

1. **Fusion et tag** : fusionner `foire-2026` dans `main`, poser `gel-final` (je n'ai posé aucun tag, rien poussé sur `main`).
2. **CI** : régler la facturation GitHub (Billing & plans), relancer ; jusque-là, seules les portes locales ci-dessus font foi.
3. **Mode salle et constellation sur de vrais téléphones**, à travers le tunnel, en 4G : scan, deux gestes, oui, retrait, bilan, purge.
4. **Chronométrer la v2** (deck, touche `R`) : 821 mots dits + film 3:21 + scans ≈ 15–16 min estimées ; cible 18:00.
5. **`film.mp4`** copié sur la machine de la salle ; tester la lecture dans le deck (`v2.html`, slide « film »).
6. **Carte → profil : les 5 essais sur la VRAIE carte** :
   `cd prototype && python -m eval.banc_carte --photo <photo> --entreprise "<nom>" --metier <id>` (rapport hors dépôt).
   5/5 → deck avec `?carte=1` ; sinon, monde « visite » seulement, hors scène.
7. **Relire** : la traduction allemande (bandeau « à relire ») ; les termes DPV (`docs/conformite/RECU_27560.md`) ;
   l'écart 44 / 48 « autre » de la liste du Club (PREUVES, « Liste du Club »).
8. **Remplir la feuille d'annotation Tally** (`prototype/var/annotation/`) : sans elle, aucune exactitude de classification.

---

# Pack « deux double-clics » (03.10, soir — avant le gel)

Branche `foire-2026`. Aucun tag, rien sur `main`. CI : **n'a pas tourné** (facturation) — portes locales seulement.

| Quoi | Où |
|---|---|
| « 1 - Lancer Club Pulse », « 2 - Arrêter et effacer », « 3 - Passer en v1 » (double-clics, racine) | logique commune : `prototype/scripts/jour_j_commun.sh` ; film, jeton, check-list : `prototype/app/jour_j.py` |
| Check-list locale `/preflight` (404 à travers le tunnel) | `app/main.py` |
| Écran de la salle **dans** le deck v2 (iframe, intégrable seulement par le deck local) | `deck/v2.html`, `app/protections.py` |
| Cartes d'une page (régie V2, V1), guide en cinq lignes | `docs/presentation/livrables/CARTE_*.pdf`, `COMMENT_PRESENTER.md` |

**Audit par un sous-agent au contexte neuf** : 2 BLOQUANT, 8 IMPORTANT, des MINEUR — tous les BLOQUANT et IMPORTANT
corrigés, test rouge d'abord, un commit par lot de constats : B1 (fenêtre de saisie du jeton sur le projecteur),
B2 (certificats du Python de python.org), I1 (vert « tailnet » au lieu de « Internet »), I2 (vieux PID), I3 (iCloud
sur Sonoma), I4 (code en zip), I5 (tunnel qui attend), I6 (« PASSER EN v1 » non exécutable → 3e double-clic et
« RÉPARER D'ABORD »), I7 (fenêtre qui se ferme), I8 (salle déjà remplie). Restent (mineurs, dits) : jeton et secret
visibles dans `ps` (existant, `demo-tunnel.sh`) ; jeton jamais renouvelé ; `/salle/ecran` intégrable par le deck local
aussi hors démo ; rebinding DNS sur `/preflight.json` (même classe que `/qr/salle.svg`) ; tests sous bash 5, pas 3.2.

**Non vérifiable depuis la session cloud** (à faire sur le Mac) : la sonde de l'adresse publique par DNS public (proxy
de la session) ; le vrai Funnel ; la permission « Bureau » de macOS ; le comportement de Terminal à la fermeture.

| Porte (sur `341bd91`) | Résultat |
|---|---|
| Suite complète | **1 612** réussis, 0 échec |
| E2E allumé · éteint · réseau coupé | **34 / 34** · **34 / 34** · **34 / 34** |
| Lint · types · secrets · validateur | propres · 0 erreur · aucun · « toutes vérifiées » |

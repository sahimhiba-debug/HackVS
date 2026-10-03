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

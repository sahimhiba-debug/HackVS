# Vagues de correction — 01.10.2026 (après l'audit profond)

> Décision de Hiba : tout corriger, Vague 2 comprise, avec discipline. Règles appliquées à CHAQUE constat : test
> ROUGE d'abord sur le scénario exact du constat, changement minimal, contre-épreuve, un commit par correctif, CI verte
> après chaque vague, aucune nouvelle fonctionnalité. Gel du code : vendredi 02.10, 18:00.
> Constats et preuves : [SENIOR_ENGINEERING_AUDIT.md](SENIOR_ENGINEERING_AUDIT.md) · état de chacun :
> [SENIOR_ENGINEERING_FINDINGS.md](SENIOR_ENGINEERING_FINDINGS.md).

## 0. Remise au vert

| Constat | Avant | Test rouge | Changement | Commit |
|---|---|---|---|---|
| F25 | CI rouge (#125, #126) : le scanner de secrets refusait un littéral de test ; le garde « chaque E2E en CI » refusait `test_e2e_serveur.py` | les deux gardes existants, rejoués localement | littéral construit (`"x" * 10`) ; fichier ajouté à la CI et à `make e2e` | `36faa4e` — CI #128 verte |

## 1. Vague 1 — fiabilité et véracité (CI #131 verte)

| Constat | Avant (scénario exact) | Test rouge | Changement | Contre-épreuve | Commit |
|---|---|---|---|---|---|
| F29 / F24 | `make demo` et l'image : journal en mémoire, secret aléatoire ; un redémarrage perdait le monde, les sessions, le rejeu IA | `test_redemarrage_kill9.py` : VRAI uvicorn, faux modèle local (chat/completions), `SIGKILL`, relance avec le modèle MORT | journal fichier + secret stable hors dépôt (`make demo`) ; journalisés : `ACTIVATION`, `IA_INTERRUPTEUR`, `PASSE_EMIS`, nonce de `PASSE_JURE`, `DEMO_ETAPE` ; historique IA rebâti (compteurs et traces continus) | chacune des 5 restaurations retirée → rouge | `4c3975e` |
| F26 | Pauline déplace son horaire hors fenêtre : capacité ACTIVE → ONE_AWAY sans perte, reçu « valable » | `test_capacites_offre_ne_couvre_plus.py` (scénario E1) | la validité d'un consentement de finalité vérifie que l'offre couvre encore la portée CONSENTIE ; changement journalisé `CONSENTEMENT_ETAT` (anonyme) ; cause dite par le rôle ; reçu exact | horaire déplacé DANS la fenêtre → rien | `378277c` |
| F31 | valeur proposée par l'IA puis confirmée : `SELF_DECLARED`, aucun lien à l'appel | `test_provenance_ia.py` | `PROPOSITION_IA` (nombres, à qui, quelle demande) ; confirmation identique → `AI_PROPOSED_CONFIRMED` + trace ; « Mes données » le dit ; parité : la provenance DOIT différer | valeur corrigée / sans proposition / proposition d'un autre → `SELF_DECLARED` | `bc939e4` |
| F01 | `/moi/demandes` écrivait le BESOIN interprété par le modèle | `test_demande_confirmee.py` (16 → 18 événements) | interpréter n'écrit rien ; `…/confirmer` publie exactement ce qui a été montré, une fois, par son auteur | confirmation par un autre ou deux fois → 404 | `bcf2710` |
| F34 | `Coffre.supprimer` jamais appelé ; coffre rebâti à chaque démarrage | `test_effacement.py` | « Tout effacer » : une transaction (consentements, offres, participations, profil, préférences, `EFFACEMENT`), puis le coffre ; rejoué au redémarrage ; ce qui reste est dit | sans `confirme: true` → 422 ; session morte → 401 | `4ac6f81` |
| F33 | « champs non demandés : ['…'] » recopiait la sortie du modèle | `test_rejets_sans_contenu.py` (canari dans chaque sortie hostile) | `Rejet` à catégorie fixe ; tout ce qui est gardé passe par `raison_sans_contenu` | rouge sur le commit précédent (canari recopié) | `af7837c` |
| F30 | README : 7 pages 404, 8 fonctions livrées « non implémentées » | `test_readme.py` | README réécrit sur l'état réel ; ancien prototype → `docs/ANCIEN_PROTOTYPE.md` | — | `d3e53eb` |

## 2. Vague 2 — cohérence transactionnelle (CI #132 verte)

| Constat | Avant | Test rouge | Changement | Contre-épreuve | Commit |
|---|---|---|---|---|---|
| F27 | échec après l'écriture d'un profil : journal annulé, mémoire non ; projection en cache servie après annulation | `test_transaction_memoire.py` (E3 + cache par comptage) | `Memoire.sur_annulation` : la façade rebâtit profils, besoins, préférences, horloge par le seul chemin `_appliquer` et oublie ses caches | rejeu après l'échec = état d'avant | `02b6655` |
| F28 | réinitialisation pendant une requête : écriture de l'ancien monde dans le nouveau journal | `test_reinitialisation_atomique.py` (entrelacement déterministe, requête bloquée en pleine commande) | `Passage` lecteurs / rédacteur sur toute la durée d'une requête ; remplacer le monde attend la vidange ; journal de l'ancien monde FERMÉ (`MondeRemplace`) | écriture sur un journal fermé → lève | `9ca23cb` |
| F36 | 404 en lecture, 403 sur 12 commandes pour un étranger à l'essai | `test_essai_inexistant_pour_etranger.py` (balayage E6) | « concerné ? » avant « porteur ? » : 404 uniforme | un participant non porteur garde son 403 | `298adab` |

## 3. Après les vagues

| Constat | Changement | Commit |
|---|---|---|
| F09 | `/acces` : par CODE (5/min) + plafond global doux (300/min) ; l'IP n'est plus lue — test rouge : 14 téléphones derrière une adresse | `2712f5b` |
| F32 | un acquittement ne tombe plus sur une trace (appel IA, passe juré, interrupteur, activation, « non ») ; contre-épreuve : une offre publiée le fait tomber | `e33e1f6` |
| Mutation | campagne locale sur `capacites.py` après F26/F31 : 8 survivants non classés trouvés AVANT GitHub ; 5 tués par deux tests (dont un vrai trou : le chemin ACTIVE quand la première pièce consentie ne tient pas le créneau), 3 renumérotés (équivalents) ; 4 anciens survivants tués par F26 → **1 229 / 1 327, 98 survivants, tous classés** | `0fa7620` |

## 4. F37 — mutation de `essai.py` (mesure, pas correction)

Condition de Hiba : seulement si la Vague 2 était verte avant jeudi soir, en local, jamais sur la machine de démo.
Remplie (CI #132 verte jeudi 11:00). Campagne locale dans une copie du dépôt (`setup.cfg` : `only_mutate =
intelligence/essai.py`, sélection : tests du banc d'essai et du registre). Résultat : voir § 4.1 (écrit à la fin de la
campagne, tel quel).

### 4.1 Résultat (campagne terminée le 02.10 vers 02:55 UTC, tel quel)

| Population | Tués | Survivants | Sans test | Timeout | Suspects |
|---|---|---|---|---|---|
| 3 528 | 2 311 | 1 150 | 67 | 0 | 0 |

- **Taux** : 65,5 % de la population tuée ; 66,8 % des 3 461 mutants couverts par au moins un test.
- **Survivants : 1 150, NON classés.** Consigne : pas de classification de masse avant le gel. Certains sont sans
  doute équivalents, d'autres sont de vrais trous de test ; cette campagne ne permet pas de faire la part des deux.
- **Population d'avant H2.** La mesure porte sur une copie figée de `essai.py` prise avant les commits H2 (`107c6cb`,
  `edb0f5d`) : les index ajoutés depuis ne sont pas dans cette population.
- **Exécution.** Campagne locale dans une copie du dépôt, jamais sur la machine de démo. Elle a été interrompue
  plusieurs fois par des redémarrages du conteneur, puis reprise par mutmut là où elle en était, sans rien perdre.
- **Ce que ces chiffres ne font pas.** Ils ne vont ni dans `PREUVES.md` ni dans le deck : règle au gel, FINAL_AUDIT
  § 10. Ils mesurent le banc d'essai, pas le cœur du registre (`capacites.py`, dont les 98 survivants sont tous
  classés).

## 5. Ce qui reste (connu, dit)

F02 (architecture à réécrire — documentation), F05 (charges d'événements non typées), F06 (`Banc`), F08 (classement
des routes sans écran), F10 (4 tests d'absence), F11/F16 (frontière de l'héritage dans `docs/`), F17 (contrat de
configuration du rejeu), F38 (hygiène), F39–F40 (à documenter). Aucun ne touche une garantie démontrée en scène.

## 6. Durcissement final avant le gel (01.10, après-midi) — détail dans [FINAL_AUDIT.md](FINAL_AUDIT.md)

| Problème (preuve) | Impact | Test ajouté (rouge d'abord) | Commit |
|---|---|---|---|
| H2 — chaque recherche d'offre relisait tout le journal : 200 offres parasites → 27–31 s par projection, sous le verrou du monde | démo figée par un membre ou un juré | `test_charge_offres.py` (lectures du journal comptées ; offre annulée jamais servie par l'index) | `107c6cb` |
| H2 — idem pour les faits d'essai : 100 brouillons parasites → 8,5 s | idem | `test_charge_offres.py::…brouillons_parasites` | `edb0f5d` |
| H3 — la porte de mutation ignorait le code de sortie de mutmut et les mutants « not checked » / « no tests » : verte après 16 mutants sur 1 327 | preuve de mutation possiblement fausse | `test_porte_mutation.py` (7 cas) | `d374f75`, `4233cef` |
| H3 — `make coverage` masquait son code de sortie (`\| tail`) ; ma propre contre-épreuve du limiteur ne déclenchait jamais la purge | faux verts | `test_limiteur_memoire_bornee.py` renforcé | `d374f75`, `d549aa6` |
| H1 — aucune garde n'était vérifiée route par route | régression silencieuse possible | `test_autorisation_balayage.py` (routes énumérées depuis le routeur, matrice A → B, gestes doubles) | `7359277` |
| H5 — la concurrence n'était testée qu'en séquence | — | `test_concurrence_http.py` (vrais fils, barrière) | `7e6b24b` |
| Claim « recomposition jamais appliquée » seulement implicite | claim non gardé | `test_recomposition_jamais_appliquee.py` | `40fa659` |
| `DEMO_SCRIPT` et `TODO-DEMO` : « après un redémarrage, Nouvelle démonstration » | l'opérateur aurait EFFACÉ le monde restauré, en direct | — (documentation) | `00d221b` |
| Six champs du téléphone sans nom accessible (placeholder seul) | lecteurs d'écran | `test_lisible_et_touchable…` étendu | `22bddf8` |
| 19 documents d'avant le pivot non marqués ; ADR 0004 décrivant un module supprimé ; claims D | crédibilité | `test_docs_classees.py` | `ab664b5` |

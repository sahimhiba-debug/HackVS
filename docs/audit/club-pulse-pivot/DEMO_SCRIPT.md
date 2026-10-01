# Démonstration — une action collective qu'aucun membre ne pouvait faire seul

> **Monde FICTIF** : personnes, entreprises, offres et horaires sont inventés (aucun membre réel, aucun entretien
> inventé). **Joué** : les membres absents de la scène (Pauline, Markus, Nicolas) sont incarnés depuis la console, et
> l'écran commun l'affiche. **Simulé** : l'horloge quand on l'avance. **Non testé** : de vrais téléphones sur le réseau
> d'une salle, un jury réel, Apertus réel.

## 0. Calendrier des scènes (chaque écran affiche sa date)

Horloge de démonstration (simulée, affichée sur chaque écran) : **mardi 06.10.2026**, pendant la Foire du Valais
(02–11.10.2026). Chaque scène vit un jour distinct : les mondes de démonstration sont isolés, jamais regroupés.

| Scène | Jour de la scène | Où | Ce qui se passe |
|---|---|---|---|
| Action collective (Sophie, Léa, jury) | **jeudi 08.10** | `/projection`, téléphones « Agir à plusieurs » | le créneau commun, la perturbation, l'adaptation, la fiche |
| Registre — scénario A (une pièce manque) | **vendredi 09.10** | `/etabli`, téléphone « Demandes » | minibus demandé → réponse → « le Club peut le faire » |
| Registre — retrait (Phase 2) | **vendredi 09.10** | `/etabli`, téléphones | retrait en un geste → « ce composant n'est plus disponible » → la demande repart vers un autre membre |
| Après l'événement | **+30 jours (simulé)** | console | ce qui reste : reçu, résultat inconnu, capacités éteintes |

**Règle de scène : après un redémarrage du serveur, NE PAS faire « Nouvelle démonstration »** : `make demo` rend le même
monde, y compris l'étape de la régie (F29, `tests/test_redemarrage_kill9.py`) ; « Nouvelle démonstration » l'effacerait.
Elle sert seulement à recommencer volontairement (§ 2, § 9). L'ancienne règle, d'avant F29, est corrigée ici et dans
`TODO-DEMO.md`.

## 1. Scénario du pitch
Sophie (fictive) produit des tisanes. Pendant la Foire, jeudi après-midi, elle veut les présenter à des acheteurs
germanophones. Elle n'a ni stand ni personne qui parle allemand, et veut leur laisser une fiche en allemand.
Des membres ont déjà proposé, chacun avec ses horaires : une voix allemande (16:00–18:00), un présentoir
(14:00–17:30), un autre lieu (16:30–19:00), des acheteurs (15:00–18:30) — et des pièges réels : une traductrice le
matin seulement, une offre sans horaire, une personne qui refuse d'être sollicitée.
**Aucune offre ne suffit seule** ; le serveur trouve où les disponibilités **déclarées** se recouvrent, chacun
accepte **sa** part sur **son** téléphone, le jury change une condition, le système dit ce qui tombe, ce qui tient et
ce qui est encore possible — ou qu'il est bloqué.

## 2. État initial reproductible
- `make demo` — journal dans un FICHIER (`prototype/var/club_pulse.db`) et secret STABLE (`prototype/var/secret_demo`,
  tiré une fois, hors dépôt : ne jamais le supprimer pendant le hackathon, sessions et QR juré en dépendent) ; puis
  console → « Nouvelle démonstration »
  (ou `POST /api/pulse/demo/reinitialiser`). Date simulée : mardi 06.10.2026, pendant la Foire du Valais (2–11 octobre 2026) ; la scène : jeudi 08.10.
  La vidéo `captures/action/demo_action.webm` et les captures ont été **réenregistrées au commit `a03bfa6`** (Phase 3),
  aux dates actuelles (06.10 / 08.10) : `scripts/enregistrer_demo.py`.
- Aucune action n'existe ; l'écran commun (`/projection`) montre « Jeudi 08.10 : 6 contributions proposées, dispersées ».
- **Vrais téléphones** (point d'accès du portable) : `make demo HOTE=0.0.0.0 URL_PUBLIQUE=http://<ip-du-portable>:8000`
  (l'adresse du portable SUR son point d'accès). Sans ces deux valeurs, le serveur n'écoute que le portable et le QR juré
  encode `127.0.0.1`, qu'un téléphone prend pour lui-même (revue R-01). La console et l'Établi s'ouvrent sur le portable
  (`http://127.0.0.1:8000/…`) : la console refuse tout autre appareil (403, testé). Les téléphones restent en HTTP
  local : le mode hors ligne du service worker n'y est pas actif, rien d'autre n'en dépend (vérifié dans Chromium).
- Téléphone 1 = Sophie (code affiché dans la console), téléphone 2 = Léa (voix allemande). Régie de tournage :
  `/demo/regie` (écran commun + deux téléphones côte à côte ; aucun code affiché).

## 3. L'intervention du jury
| Dimension | Qui la modifie | Comment | Réponse attendue (test `test_la_valeur_choisie_par_le_jury_n_est_pas_fixee_d_avance`, 6 valeurs) |
|---|---|---|---|
| **Heure de disponibilité de la voix** (dimension principale, valeur choisie par le jury) | Léa, sur **son** téléphone : « Ma disponibilité a changé » | le jury dit une heure ; Léa la saisit | 15:00–18:00 : rien ne change (le créneau reste couvert) · 16:15 à 17:30 : « ne couvre plus : voix », « reste valable pour ce créneau : lieu, public », 1 à 3 adaptations (même équipe, plus court jamais sous 30 min, ou autre lieu) · **18:00 ou plus tard, ou le matin : BLOQUÉ**, dit tel quel, lancement impossible |
| Horaire du lieu | la console (**joué**, marqué « joué par l'équipe ») | « Le lieu ferme à… » | test `test_perturbation_jouee_par_l_equipe…` : le lieu tombe, l'autre lieu (16:30) est proposé |
| Refus ou retrait | Léa sur son téléphone, ou la console pour un rôle absent (**joué**) | « Décliner » / « Me retirer » | le geste retombe ; jamais redemandé à la même personne ; adaptation ou blocage |
| Interdit par construction | la console **ne peut pas** jouer Léa : elle a son téléphone (403) | — | test `test_personne_ne_decide_a_la_place_d_un_autre` |
| Registre (vendredi 09.10) : un juré **joue Markus** | un juré, sur **son** téléphone | Établi → « QR juré » : passe de 15 min, **une seule fois** ; le téléphone affiche « Jury : vous jouez Markus, personnage FICTIF » | tests `test_qr_jure.py` et E2E `test_qr_jure_etabli_telephone_usage_unique` ; activation journalisée (attribuée au jury) |
| L'IA, allumée ou éteinte | l'équipe (Établi, en-tête) | « Éteindre l'IA » / « Allumer l'IA » ; chaque proposition et chaque récit disent qui les a produits | parité ON/OFF `test_parite_ia.py` : même état métier |

**Sans solution** : l'état « bloqué : aucune adaptation admissible aujourd'hui » n'est pas une fin : si Léa redevient
disponible (ex. 16:30), l'action **rouvre une adaptation** que Sophie choisit ; rien n'est relancé tout seul
(`test_sans_solution_bloque_et_le_dit_puis_rouvre…`). « Et si… » : **non construit** — toute modification montrée est réelle.

## 4. Résultat, preuve de réception, transition finale
- Résultat concret : la **fiche en allemand** écrite par Léa, transmise depuis son téléphone, **reçue** sur celui de
  Sophie, qui confirme la réception. Palier affiché : « livrable reçu » — **pas** « présentation tenue » : la
  présentation, elle, est engagée pour le créneau et ne peut être constatée qu'à partir de son jour.
- Transition finale : console « +30 jours (simulé) ». L'écran dit : la fiche reçue le reste ; **aucun résultat n'a été
  déclaré — il reste inconnu** ; les disponibilités étaient datées : **rien n'est reconduit** (même besoin un mois plus
  tard → aucune proposition).

## 5. États affichés, jamais plus forts que leur preuve
proposition réalisable (serveur) → accords réunis (« coopération prête ») → réalisation engagée (« action engagée : pas
encore réalisée ») → livrable transmis → livrable reçu (confirmé par la destinataire) → contribution constatée (au
créneau) → résultat **déclaré** (par la porteuse, contestable) ; sans déclaration : « résultat inconnu ».

## 6. Storyboard vidéo (enregistrement réel `captures/action/demo_action.webm`, 87 s, commit `a03bfa6` ; horodatage dans `demo_action.json`)
| t | Écran | Action | Parole (à dire) | Preuve visible |
|---|---|---|---|---|
| 0:02 | régie : écran commun | — | « Jeudi, pendant la Foire : six offres de membres, chacune avec ses horaires. Dans quarante secondes, c'est vous qui changerez une condition. » | barres d'horaires anonymes, « FICTIF » |
| 0:09 | téléphone de Sophie | elle écrit son besoin | « Sophie écrit avec ses mots ce qu'elle ne peut pas faire seule. » | texte tapé en direct |
| 0:15 | téléphone de Sophie | 3 exigences, « Règles simples — aucun modèle utilisé » | « Trois exigences reprises de ses mots. Pas d'IA ici : c'est affiché. » | mention du mode |
| 0:22 | écran commun | Sophie choisit de montrer son action | « Aucune offre ne suffit seule. Les disponibilités se recouvrent de 16 h à 17 h 30 : premier créneau, 16 h–16 h 45. » | zone de recouvrement + cadre |
| 0:30 | téléphone de Léa | elle accepte **sa** part | « Léa reçoit sa seule part, sur son téléphone. Elle accepte. » | « 1 accord sur 3 » (678 ms mesurés au dernier enregistrement ; à l'oral : « moins d'une seconde ») |
| 0:36 | écran commun | accords de Pauline et Markus **joués** | « Pauline et Markus ne sont pas là : leurs accords sont joués, et c'est affiché. » | « Joué par l'équipe (console) » |
| 0:43 | téléphone de Léa | le jury donne une heure (17:00) | « À vous : à partir de quelle heure Léa est-elle disponible ? » | valeur saisie sur son téléphone |
| 0:44 | écran commun | recalcul | « Ce qui tombe, ce qui tient, ce qui est encore possible. Aucun lancement possible. » | encadré rouge, adaptations en rôles |
| 0:53 | téléphone de Sophie | elle choisit 17:00–17:45, autre lieu | « Sophie choisit. Le moment change : tout le monde reconfirme, personne à sa place. » | nouvelle version ; accords redemandés |
| 1:00 | les deux téléphones | action engagée ; Léa transmet la fiche | « Engagée, pas encore réalisée. Léa envoie la fiche. » | « transmis » |
| 1:06 | téléphone de Sophie | la fiche apparaît ; « J'ai bien reçu » | « Transmise, puis reçue : deux faits. La présentation, elle, n'a pas encore eu lieu. » | palier « livrable reçu » |
| 1:18 | écran commun | +30 jours (simulé) | « Un mois plus tard : la fiche reste reçue ; personne n'a déclaré de résultat — il reste inconnu. Rien n'est reconduit. » | « résultat inconnu », horloge simulée |

## 7. Scripts chronométrés
Temps **estimés** à 150 mots/min (français parlé, lent) — non chronométrés par un humain ; la durée machine de
l'exécution enregistrée est mesurée (`demo_action.json`). Répétition : lire le script sur la vidéo sans le son.

**60 secondes** (132 mots ≈ 53 s de parole — sur la vidéo ou la régie) :
« Au Club, chacun peut aider un peu : une langue, un stand, des contacts. Seul, personne ne suffit. Sophie veut
présenter ses tisanes à des acheteurs germanophones jeudi ; elle n'a ni stand ni allemand. Club Pulse ne cherche pas
“quelqu'un” : il cherche le moment où des offres réelles se recouvrent, et le propose. Chacun accepte sa part sur son
téléphone. Maintenant, vous : Léa n'est disponible qu'à partir de quelle heure ? … Le système recalcule : ce qui
tombe, ce qui tient, ce qui est encore possible — ou il dit qu'il est bloqué. Sophie choisit, tout le monde
reconfirme, la fiche en allemand arrive sur son téléphone. Et il n'affiche jamais plus que ce qui est prouvé : fiche
reçue, présentation pas encore tenue. Tout est fictif, rien n'est inventé. »

**2 minutes** : le storyboard ci-dessus, parole par parole (172 mots ≈ 70 s de parole), plus ≈ 40 s pour la réponse du jury et les gestes sur les téléphones ; exécution machine enregistrée : voir `demo_action.json` (`duree_s`).

**5 minutes** : 2 minutes de démonstration, puis 3 minutes : (1) le cas « bloqué » en direct (le jury donne 18:00 →
« bloqué », puis 16:30 → une adaptation rouvre) ; (2) ce qui n'est pas prouvé : aucun utilisateur, Apertus non
exécuté, l'IA non nécessaire à cette démo ; (3) le test terrain proposé (`REVUE_JURY.md` § 4).

## 8. Secours
| Panne | Secours | Ce qu'on dit |
|---|---|---|
| Internet de la salle | tout tourne sur l'ordinateur de démonstration ; téléphones sur son point d'accès (`make demo HOTE=0.0.0.0 URL_PUBLIQUE=…`, § 2) | — |
| Téléphones qui ne se connectent pas | régie `/demo/regie` sur un seul écran : deux sessions distinctes dans deux cadres | « deux sessions sur une machine » |
| Fournisseur IA | aucun impact : Établi → « Éteindre l'IA » (ou aucun modèle configuré) ; chaque résultat dit « forme déterministe, sans IA » ; même état métier (parité testée) | « l'IA propose, le code décide : sans elle, le formulaire » |
| Réseau de la salle | tout est local : E2E vérifiés en « mode salle » (espace réseau vide, IA OFF) en CI | — |
| Le serveur plante, l'ordinateur redémarre | `make demo` : le monde revient tel quel — étape de la régie, Établi, sessions des téléphones, QR juré non scanné, interrupteur IA, sorties IA rejouées sans modèle (`tests/test_redemarrage_kill9.py`, répété samedi matin : § 9) | « le journal est la source de vérité : on rejoue, on n'improvise pas » |
| Tout tombe | la vidéo `demo_action.webm` : **exécution réelle enregistrée, sans montage**, commit indiqué à l'image | « enregistrement, pas du direct » |

## 9. Répétition
0. Sur la machine de démonstration : **aucune campagne de mutation** pendant le hackathon (`TODO-DEMO.md`).
1. `make quality-check` vert ; `python -m pytest -q prototype/tests/test_e2e_action.py` (le parcours complet dans un vrai navigateur).
2. Nouvelle démonstration ; parcours complet deux fois, dont une fois avec une heure « bloquante » (18:00).
3. Vérifier sur l'écran commun : aucun nom, aucun texte d'offre, « joué par l'équipe » présent, date simulée affichée.
4. Chronométrer le script à voix haute ; couper s'il dépasse (priorité : la question au jury avant 0:45).
5. **Rituel d'avant-scène — samedi matin, SUR LA MACHINE DE DÉMONSTRATION** (F29 : on prouve la reprise, on ne la
   suppose pas) :
   1. `make demo` ; console → « Nouvelle démonstration » ; régie → avancer de deux étapes ; activer Sophie sur son
      téléphone ; émettre un QR juré **sans le scanner** ; éteindre puis rallumer l'IA (Établi).
   2. Noter : l'étape de la régie, le statut de « Accueillir une délégation d'acheteurs germanophones » sur l'Établi, le
      nombre d'actions de la console.
   3. Tuer le serveur sans arrêt propre : `kill -9 $(pgrep -f "uvicorn app.main:app")`.
   4. `make demo`.
   5. Vérifier : même étape à la régie, même Établi, même nombre d'actions ; le téléphone de Sophie, rafraîchi, est
      toujours connecté ; le QR juré non scanné s'active ; l'interrupteur IA est dans l'état laissé.
   6. Avec un VRAI téléphone sur le point d'accès : ouvrir `/app` par l'adresse du portable, puis scanner un QR juré
      depuis l'Établi — il doit ouvrir « Jury : vous jouez … ». Un QR qui pointe vers `127.0.0.1` = `URL_PUBLIQUE` oublié.
   7. Un écart, un seul : ne pas improviser — le noter, « Nouvelle démonstration », et prévoir la vidéo de secours.

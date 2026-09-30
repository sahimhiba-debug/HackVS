# Démonstration — une action collective qu'aucun membre ne pouvait faire seul

> **Monde FICTIF** : personnes, entreprises, offres et horaires sont inventés (aucun membre réel, aucun entretien
> inventé). **Joué** : les membres absents de la scène (Pauline, Markus, Nicolas) sont incarnés depuis la console, et
> l'écran commun l'affiche. **Simulé** : l'horloge quand on l'avance. **Non testé** : de vrais téléphones sur le réseau
> d'une salle, un jury réel, Apertus réel.

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
- `make demo` (ou `cd prototype && HACKVS_MODE=demo … uvicorn app.main:app`), puis console → « Nouvelle démonstration »
  (ou `POST /api/pulse/demo/reinitialiser`). Date simulée : mardi 03.11.2026 ; la Foire : jeudi 05.11.
- Aucune action n'existe ; l'écran commun (`/projection`) montre « Jeudi 05.11 : 6 contributions proposées, dispersées ».
- Téléphone 1 = Sophie (code affiché dans la console), téléphone 2 = Léa (voix allemande). Régie de tournage :
  `/demo/regie` (écran commun + deux téléphones côte à côte ; aucun code affiché).

## 3. L'intervention du jury
| Dimension | Qui la modifie | Comment | Réponse attendue (test `test_la_valeur_choisie_par_le_jury_n_est_pas_fixee_d_avance`, 6 valeurs) |
|---|---|---|---|
| **Heure de disponibilité de la voix** (dimension principale, valeur choisie par le jury) | Léa, sur **son** téléphone : « Ma disponibilité a changé » | le jury dit une heure ; Léa la saisit | 15:00–18:00 : rien ne change (le créneau reste couvert) · 16:15 à 17:30 : « ne couvre plus : voix », « reste valable pour ce créneau : lieu, public », 1 à 3 adaptations (même équipe, plus court jamais sous 30 min, ou autre lieu) · **18:00 ou plus tard, ou le matin : BLOQUÉ**, dit tel quel, lancement impossible |
| Horaire du lieu | la console (**joué**, marqué « joué par l'équipe ») | « Le lieu ferme à… » | test `test_perturbation_jouee_par_l_equipe…` : le lieu tombe, l'autre lieu (16:30) est proposé |
| Refus ou retrait | Léa sur son téléphone, ou la console pour un rôle absent (**joué**) | « Décliner » / « Me retirer » | le geste retombe ; jamais redemandé à la même personne ; adaptation ou blocage |
| Interdit par construction | la console **ne peut pas** jouer Léa : elle a son téléphone (403) | — | test `test_personne_ne_decide_a_la_place_d_un_autre` |

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

## 6. Storyboard vidéo (enregistrement réel `captures/action/demo_action.webm`, 89 s, commit `dd75a7c` ; horodatage dans `demo_action.json`)
| t | Écran | Action | Parole (à dire) | Preuve visible |
|---|---|---|---|---|
| 0:01 | régie : écran commun | — | « Jeudi, pendant la Foire : six offres de membres, chacune avec ses horaires. Dans quarante secondes, c'est vous qui changerez une condition. » | barres d'horaires anonymes, « FICTIF » |
| 0:08 | téléphone de Sophie | elle écrit son besoin | « Sophie écrit avec ses mots ce qu'elle ne peut pas faire seule. » | texte tapé en direct |
| 0:15 | téléphone de Sophie | 3 exigences, « Règles simples — aucun modèle utilisé » | « Trois exigences reprises de ses mots. Pas d'IA ici : c'est affiché. » | mention du mode |
| 0:22 | écran commun | Sophie choisit de montrer son action | « Aucune offre ne suffit seule. Les disponibilités se recouvrent de 16 h à 17 h 30 : premier créneau, 16 h–16 h 45. » | zone de recouvrement + cadre |
| 0:31 | téléphone de Léa | elle accepte **sa** part | « Léa reçoit sa seule part, sur son téléphone. Elle accepte. » | « 1 accord sur 3 » en < 0,4 s |
| 0:35 | écran commun | accords de Pauline et Markus **joués** | « Pauline et Markus ne sont pas là : leurs accords sont joués, et c'est affiché. » | « Joué par l'équipe (console) » |
| 0:42 | téléphone de Léa | le jury donne une heure (17:00) | « À vous : à partir de quelle heure Léa est-elle disponible ? » | valeur saisie sur son téléphone |
| 0:44 | écran commun | recalcul | « Ce qui tombe, ce qui tient, ce qui est encore possible. Aucun lancement possible. » | encadré rouge, adaptations en rôles |
| 0:54 | téléphone de Sophie | elle choisit 17:00–17:45, autre lieu | « Sophie choisit. Le moment change : tout le monde reconfirme, personne à sa place. » | nouvelle version ; accords redemandés |
| 1:02 | les deux téléphones | action engagée ; Léa transmet la fiche | « Engagée, pas encore réalisée. Léa envoie la fiche. » | « transmis » |
| 1:09 | téléphone de Sophie | la fiche apparaît ; « J'ai bien reçu » | « Transmise, puis reçue : deux faits. La présentation, elle, n'a pas encore eu lieu. » | palier « livrable reçu » |
| 1:20 | écran commun | +30 jours (simulé) | « Un mois plus tard : la fiche reste reçue ; personne n'a déclaré de résultat — il reste inconnu. Rien n'est reconduit. » | « résultat inconnu », horloge simulée |

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
| Internet de la salle | tout tourne sur l'ordinateur de démonstration ; téléphones sur son point d'accès | — |
| Téléphones qui ne se connectent pas | régie `/demo/regie` sur un seul écran : deux sessions distinctes dans deux cadres | « deux sessions sur une machine » |
| Fournisseur IA | aucun impact : la démo tourne en « règles simples », affiché | « pas d'IA dans cette étape » |
| Tout tombe | la vidéo `demo_action.webm` : **exécution réelle enregistrée, sans montage**, commit indiqué à l'image | « enregistrement, pas du direct » |

## 9. Répétition
1. `make quality-check` vert ; `python -m pytest -q prototype/tests/test_e2e_action.py` (le parcours complet dans un vrai navigateur).
2. Nouvelle démonstration ; parcours complet deux fois, dont une fois avec une heure « bloquante » (18:00).
3. Vérifier sur l'écran commun : aucun nom, aucun texte d'offre, « joué par l'équipe » présent, date simulée affichée.
4. Chronométrer le script à voix haute ; couper s'il dépasse (priorité : la question au jury avant 0:45).

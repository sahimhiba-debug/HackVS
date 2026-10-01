# 04 — Runbook de la démo live (actes 4–6, 4:40–7:10)

Ce runbook **s'adosse** à `docs/audit/club-pulse-pivot/DEMO_SCRIPT.md` (état initial § 2, secours § 8, rituel de
samedi § 9.5) et l'étend pour la scène du registre. Il ne le remplace pas : en cas de divergence, DEMO_SCRIPT gagne
pour tout ce qui touche au lancement, à la reprise après plantage et au rituel.

## 0. Ce que la démo rejoue, et pourquoi cette scène

Le film montre une demande qui arrive chez Jean-Marc, et Jean-Marc qui dit oui. La démo refait exactement ce moment
dans le vrai produit, scène **« Registre — scénario A »** de DEMO_SCRIPT (vendredi 09.10, horloge simulée au mardi 06.10) :

```
l'Établi montre une capacité à une pièce près
→ la demande est sur le téléphone d'un membre (trois boutons)
→ le membre écrit sa pièce avec ses mots → l'IA propose une structure → le code vérifie
→ Oui → l'Établi passe à « le Club peut le faire » → le reçu est sur le téléphone
→ retrait en un geste → « transport : ce composant n'est plus disponible », sans nom
→ la demande repart vers un autre membre (un juré, s'il a scanné le passe)
```

C'est le parcours vérifié par `prototype/tests/test_e2e_capacites.py::test_etabli_telephones_reponse_recu_retrait_anonyme`
(vrai navigateur), et la seule scène du produit qui enchaîne trois boutons, reçu et retrait anonyme en 90 secondes.

Note de mise en scène : le brief parle d'un « anneau qui se ferme ». Dans le **produit réel**, l'Établi ne dessine pas
d'anneau : la carte passe du statut « il manque une pièce » (pièce manquante en pointillés) à « le Club peut le faire »
(bordure verte). L'anneau 3/4 → 4/4 est le langage des planches du design system (Cover, Passeport). Sur scène, on
montre l'écran réel ; l'anneau peut vivre sur les slides, pas dans la démo.

## 1. Matériel et réseau

| Élément | Réglage | Vérifié par |
|---|---|---|
| Ordinateur de démonstration | `make demo HOTE=0.0.0.0 URL_PUBLIQUE=http://<ip-du-portable>:8000` (DEMO_SCRIPT § 2) | rituel § 9.5 |
| Point d'accès du portable | WPA2, mot de passe ; les téléphones s'y connectent avant la séance | rituel § 9.5, étape 6 |
| Écran 1 (projecteur) | navigateur plein écran, onglet A : `http://127.0.0.1:8000/etabli` ; onglet B : la régie `/demo/regie` (secours) | — |
| Téléphone de V2 | `http://<ip-du-portable>:8000/app`, compte de Pauline (code `s01` dans la console), session ouverte AVANT la séance | — |
| Téléphone de secours | même réglage, compte de Markus (`s14`) | — |
| Projection du téléphone | miroir du téléphone sur l'écran 1 (câble ou AirPlay/Cast local, **sans Internet**), sinon régie `/demo/regie` en onglet B | répétition |
| IA | voir § 3 (décision) | — |
| Internet de la salle | **non requis** ; tout est local, y compris les polices et le QR | CI « mode salle » |

**Jamais pendant le hackathon sur cette machine** : `make mutation`, mutmut (TODO-DEMO.md).

## 2. État initial (reproductible)

1. `make demo …` (§ 1). Console → **« Nouvelle démonstration »** — une seule fois, avant la séance, jamais après un
   redémarrage (DEMO_SCRIPT § 0 : après un `kill -9`, `make demo` rend le même monde ; « Nouvelle démonstration »
   l'effacerait).
2. Vérifier sur l'Établi (`/etabli`) :
   - en-tête : « date du Club (simulée) : mardi 06.10 » ;
   - carte « Accueillir une délégation d'acheteurs germanophones » : statut **« il manque une pièce »**, pièce
     manquante en pointillés : **« Un minibus de 12 places ou plus — Débloquerait 1 capacité »**, jour « vendredi 09.10 » ;
   - bandeau IA : « IA : allumée — modèle « … » » ou « IA : aucun modèle configuré — forme déterministe » (§ 3).
3. Sur le téléphone de Pauline : onglet **Demandes** → la carte de la demande est là, avec **Oui / Non / Pas cette fois**
   et le champ « Décrivez votre pièce avec vos mots (facultatif) ».
4. Émettre un **QR juré** depuis l'Établi (bouton « QR juré », personnage Markus) **sans le scanner** : il servira à
   l'acte 6 s'il reste du temps. Le passe vaut 15 minutes : l'émettre au plus tôt à 4:40, idéalement pendant le film.

Données : monde fictif, personnages fictifs, marqués « FICTIF » sur chaque écran. Aucun nom réel.

## 3. L'IA pendant la démo — décision à prendre par Hiba avant samedi

Le brief impose « l'IA propose une structure ». Dans cette scène, l'IA intervient quand Pauline appuie sur
**« Proposer à partir de mon texte »** : le modèle relève la quantité (« 14 places ») dans sa phrase, le code vérifie
(entier, ≥ 12), et le téléphone dit soit « proposé par le modèle « … », vérifié par le code — Vérifiez, puis répondez. »,
soit « forme déterministe, sans IA — … Remplissez le formulaire vous-même. ».

Ce qui est **prouvé** (CLAIMS n° 38–40) concerne l'autre tâche IA du produit (« Agir à plusieurs → Comprendre ma
demande ») : Apertus répond, est validé ou refusé, et sa qualité mesurée est faible (1/26). La tâche de cette scène
(relever une quantité) n'a **pas** été mesurée (évaluation EXTRACT prête, non exécutée). Donc :

| Option | Ce que le jury voit | Risque | Ce que V1 dit |
|---|---|---|---|
| **A — IA allumée** (variables `APERTUS_*` sur la machine, modèle `swiss-ai/Apertus-v1.5-70B`) | une attente de 1 à 7 s après « Proposer », puis l'un des deux messages | Internet de la salle requis pour cet appel seul ; sortie refusée possible | les deux répliques de l'acte 5 sont écrites ; aucune des deux n'est un échec |
| **B — IA éteinte** (interrupteur « Éteindre l'IA » sur l'Établi, ou pas de variables) | « forme déterministe, sans IA » immédiatement | aucun | la réplique « formulaire » ; l'acte 8 porte seul le discours IA |

Recommandation de mise en scène : **A si le rituel de samedi a montré au moins une proposition acceptée sur cette
phrase exacte, sinon B.** Dans les deux cas, la décision antérieure (« la démonstration de scène tourne sans modèle »)
est modifiée par ce brief : à confirmer par Hiba. Le scénario guidé de la régie, lui, reste sans modèle quoi qu'il arrive.

## 4. Pendant le film (2:00–4:25) — V2, en silence

- Réveiller l'écran du téléphone, vérifier l'onglet Demandes, régler la luminosité au maximum.
- Mettre l'Établi au premier plan sur l'ordinateur ; vérifier « lu en … ms » en haut (pas « hors ligne : écran figé »).
- Émettre le QR juré (§ 2.4) si l'acte 6 long est prévu.
- Ne rien cliquer d'autre.

## 5. Les actions, une par une, avec plan B

| # | Temps | Qui | Action exacte | Ce qui doit s'afficher | Plan B si ce n'est pas le cas |
|---|---|---|---|---|---|
| 1 | 4:40 | V1 | basculer le projecteur sur l'Établi | la carte « il manque une pièce », le minibus en pointillés | **Établi vide / « hors ligne »** : F5 ; sinon `make demo` dans un terminal (le monde revient, ne pas réinitialiser) ; sinon capture `etabli-1-manque.png` et dire « capture de la répétition de ce matin » |
| 2 | 5:10 | V2 | téléphone : onglet **Demandes** | la demande « Un minibus de 12 places ou plus », trois boutons | **téléphone ne charge pas** : régie `/demo/regie` sur l'écran, cadre « Téléphone 1 » ; **toujours pas** : capture `tel-1-demande.png` |
| 3 | 5:25 | V2 | taper dans « Décrivez votre pièce avec vos mots » : `Mon minibus a 14 places, libre vendredi après-midi.` | le texte | — |
| 4 | 5:35 | V2 | appuyer **« Proposer à partir de mon texte »** | sous le champ, l'une des deux phrases (§ 3) ; si proposition acceptée, « places » pré-rempli à 14 | **« Proposition indisponible »** (réseau) : V1 dit la réplique « formulaire » ; V2 saisit 14 |
| 5 | 5:45 | V1 | la réplique qui correspond à l'écran (`03_SCRIPT_ORAL.md`, acte 5) | — | ne jamais commenter un message qui n'est pas à l'écran |
| 6 | 6:00 | V2 | vérifier « places (au moins 12) » = 14, appuyer **Oui** | téléphone : le reçu apparaît dans « Mes consentements (reçus) » ; **Établi : « le Club peut le faire »**, bordure verte, plus de pointillés (≤ 1 s, l'Établi relit chaque seconde) | **l'Établi ne change pas en 3 s** : F5 ; **rien** : capture `etabli-2-peut.png` ; **le téléphone refuse (429 / erreur)** : capture `tel-2-recu.png`, et dire « plafond ou réseau : voici la répétition de ce matin » |
| 7 | 6:20 | V2 | montrer le reçu : « valable · donné le 06.10 · jusqu'au 09.10 · référence … » | la carte du reçu | — |
| 8 | 6:40 | V2 | appuyer **« Retirer mon consentement »** | toast « Consentement retiré. Personne ne saura que c'est vous. » ; Établi : statut **« un consentement ne vaut plus »**, ligne **« transport : ce composant n'est plus disponible »** | **Établi inchangé** : F5 ; **rien** : capture `etabli-3-retrait.png` |
| 9 | 6:55 | V2 | *(option)* montrer le QR juré sur l'Établi ; un juré scanne | sur son téléphone : bandeau « Jury : vous jouez Markus, personnage FICTIF, jusqu'à … », onglet Demandes avec la demande | **le QR n'ouvre rien / pointe vers 127.0.0.1** : ne pas insister ; V2 ouvre l'onglet Demandes sur le téléphone de secours (Markus) : la demande y est |
| 10 | 7:10 | V1 | « Voilà pour l'essai. » | — | — |

Règle absolue (DEMO_SCRIPT § 9.7) : **un écart, un seul : ne pas improviser.** On dit ce que l'écran fait, ou on
montre la capture de la répétition en le disant. On ne clique jamais « Nouvelle démonstration » pendant la séance.

## 6. Captures de secours (à produire SAMEDI MATIN, pendant le rituel, sur la machine de démonstration)

Aucune capture de cette scène n'est versionnée (TODO-DEMO.md). Les produire pendant la répétition, dans l'ordre du
§ 5, et les ranger dans `docs/presentation/captures/` (hors gel : documentation) :

| Fichier | Écran | Moment |
|---|---|---|
| `etabli-1-manque.png` | Établi, carte « il manque une pièce » | état initial |
| `tel-1-demande.png` | téléphone, Demandes, trois boutons | étape 2 |
| `tel-1b-proposition.png` | téléphone, après « Proposer à partir de mon texte » (le message réel, quel qu'il soit) | étape 4 |
| `etabli-2-peut.png` | Établi, « le Club peut le faire » | étape 6 |
| `tel-2-recu.png` | téléphone, « Mes consentements (reçus) » | étape 7 — **c'est aussi le reçu de la slide finale** |
| `etabli-3-retrait.png` | Établi, « transport : ce composant n'est plus disponible » | étape 8 |
| `tel-3-jure.png` | téléphone du juré, bandeau « Jury : vous jouez Markus » | étape 9 |

Chaque capture porte la date simulée et la mention « FICTIF » à l'écran : c'est voulu, on ne les recadre pas.
Si une capture n'a pas pu être prise, l'étape correspondante n'a pas de plan B visuel : on le dit à l'oral.

## 7. Secours lourd (DEMO_SCRIPT § 8, rappel)

| Panne | Réponse |
|---|---|
| Le serveur plante | `make demo` : le monde revient tel quel, étape comprise. **Ne pas réinitialiser.** |
| Les téléphones ne joignent pas le portable | régie `/demo/regie` : deux sessions dans deux cadres sur l'écran |
| Tout tombe | les captures du § 6 ; en dernier recours la vidéo `captures/action/demo_action.webm` (87 s, exécution réelle, scène de l'action collective — ce n'est **pas** cette scène : le dire) |
| Le fournisseur IA ne répond pas | aucun impact sur le parcours : la réplique « formulaire » |

## 8. Répétition (samedi matin, en plus du rituel § 9.5)

1. Rituel § 9.5 complet (kill -9, reprise, vrai téléphone, vrai scan de QR).
2. Cette scène trois fois, chronométrée de 4:40 à 7:10, avec les captures du § 6 à la première.
3. Une fois avec l'IA allumée (si option A) : noter ce que « Proposer à partir de mon texte » a affiché sur la phrase
   exacte de l'étape 3, et le temps d'attente. Décider A ou B sur ce constat, pas sur l'espoir.
4. Une fois en coupant le Wi-Fi de la salle (pas le point d'accès) : rien ne doit changer, sauf l'IA en option A.
5. Chronométrer les trois mesures de « Oui → le Club peut le faire » sur l'Établi et garder la pire pour l'oral
   (« moins d'une seconde » seulement si la pire est sous une seconde — sinon dire le chiffre).

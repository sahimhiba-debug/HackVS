# Suivi — définition des métriques

L'écran **Suivi** (`/suivi`, console du Club, interrupteur `HACKVS_FOIRE`) calcule tout **depuis le journal**, à la
lecture (rien n'est écrit en lisant), pour une période : toute la démonstration, les 7 derniers jours, le trimestre
(90 jours) — en jours de l'horloge du monde (simulée en démonstration). Code : `prototype/intelligence/suivi.py` ;
tests : `prototype/tests/test_foire_suivi.py`.

## Les quatre étapes d'un partenariat

`demande → accord → essai → résultat` (machine à états explicite, `prototype/intelligence/partenariats.py`) :

| Étape | Entrée | Fait du journal |
|---|---|---|
| demande | une pièce manque à une capacité ; la demande est adressée à un membre | (projetée, jamais écrite en lisant) |
| accord | le membre répond oui → reçu de consentement | `ASK_REPONSE` (oui), `ACCORD` |
| essai | la capacité est réellement possible (ACTIVE) ou son jour est passé, accord valable | (calculé) |
| résultat | le demandeur (le Club) clôture : signé / test sans suite / contact établi / abandonné, note ≤ 140 car. | `CLOTURE` |
| *retiré* | le membre retire son consentement — hors chemin, jamais qui | `RETRAIT` |

Toute autre transition est refusée (`partenariats.suivante`).

## Métriques

| Métrique | Définition | Personnes ? |
|---|---|---|
| Demandes envoyées | demandes adressées dans la période (répondues + encore ouvertes) | non — dite telle quelle |
| Réponses oui / non / pas cette fois | réponses de la période ; « non » et « pas cette fois » ont le même effet, seul ce décompte les distingue | oui → k |
| Sans réponse | demandes ouvertes sans réponse ; % sur (réponses + sans réponse) | non |
| Délai médian avant le premier oui | jours entre la naissance de la demande (début du monde ou dernier retrait sur la capacité) et le oui ; non affiché sous k oui | — |
| Partenariats par étape | reçus par étape (demande : demandes ouvertes) | oui → k (sauf « demande ») |
| Résultats déclarés | clôtures par catégorie, membres distincts | oui → k |
| Métiers manquants | demandes sans réponse, par métier (taxonomie `prototype/data/taxonomie_metiers.yaml`) | non |
| Membres actifs | membres ayant répondu ou consenti dans la période | oui → k |
| Hors Valais | membres dont la zone n'est ni Valais romand ni Haut-Valais ; sans la zone : « zone non renseignée » | oui → k |
| Invités ayant contribué | passes découverte activés ayant proposé leur aide ; aussi : invités actifs, intentions d'adhésion (jamais « conversions ») | oui → k |

## Règles de confidentialité

- **Agrégats seulement.** La charge utile ne contient ni nom, ni identifiant de membre, ni texte d'offre, ni note
  (test-canari `test_canari_aucune_donnee_personnelle_dans_la_charge_utile`).
- **k = 3** (`HACKVS_K_ANONYMAT`) : tout décompte de personnes entre 1 et 2 s'affiche « < 3 ». Conséquence assumée :
  dans le monde de démonstration, « 1 invité a contribué » s'affiche « < 3 ».
- **Nominatif sous double accord** : une ligne (qui, quelle pièce, quel résultat) n'apparaît que si le membre ET le
  Club ont activé « visible par le Club » sur ce reçu ; l'un retire, elle disparaît.
- Le nom d'entreprise déclaré par un invité n'apparaît sur **aucun** écran du Club.

## Ce qu'on ne suit jamais

Les **vues** (qui a lu quoi), les **inscrits inactifs** (qui ne répond pas), les **« matchs »** proposés par une IA.
Le Suivi mesure des gestes faits par des personnes, pas une activité supposée.

## Nouveaux liens tissés (03.10)

Deux entreprises distinctes qui portent chacune un accord sur la même capacité, pour la première fois dans la
période. Un décompte, jamais une liste ; « < 3 » sous trois entreprises. Hypothèse (non branchée) : favoriser les
membres jamais liés quand une demande est routée — à décider avec le Club, car aujourd'hui une demande va à une catégorie,
jamais à une personne choisie par le système.

## Critères du pilote de 45 jours (à valider avec le Club)

Fixés d'avance dans [ROADMAP.md](ROADMAP.md) et lus sur cet écran, période « trimestre » : au moins 25 demandes, au
moins 30 % de oui, premier oui en moins de 72 h en médiane, au moins 15 membres actifs sur les 50 volontaires du pilote, zéro incident de
confidentialité. Avec ce volume, le taux de réponse est **un signal, pas une mesure fine**.

## Mode salle (pitch)

L'écran géant et son bilan (« en N minutes, cette salle a rendu possible… ») suivent les mêmes règles : agrégats,
seuil « < 3 », aucun identifiant ; tout est effacé après la présentation (purge vérifiée).

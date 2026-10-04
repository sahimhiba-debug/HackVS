# Modèle économique et prix — hypothèses

> **Hypothèses, pas des offres.** Aucun prix n'a été discuté avec le Club des Affaires. Le Club n'a pas dit qu'il
> paierait. Ce document sert à préparer cette discussion, pas à la remplacer.

## Qui paie, pour quoi (trois hypothèses)

| Hypothèse | Qui paie | Pour quoi | Pour | Contre |
|---|---|---|---|---|
| **H1 — abonnement du Club** | le Club, sur sa cotisation | le service pour tous ses membres | simple ; aucun membre ne paie à l'acte ; cohérent avec « l'entraide du Club » | dépend d'une décision du comité ; le Club porte le risque |
| **H2 — service aux membres** | chaque membre, en option | un service en plus de la cotisation | le Club ne paie rien | crée deux classes de membres ; contraire à « tous les membres peuvent être sollicités » |
| **H3 — financé (pilote puis transfrontalier)** | Innosuisse, Interreg, fondations | la preuve, puis l'ouverture transfrontalière | pas de prix tant que rien n'est prouvé | temporaire ; ne finance pas l'exploitation durable |

**Recommandation de travail :** H3 pendant le pilote (aucun prix demandé au Club), puis H1 si les critères du pilote
sont atteints. H2 est écartée : elle contredit le principe d'un réseau où chacun peut aider.

## Coûts d'exploitation (ordres de grandeur, à chiffrer)

| Poste | Hypothèse | Source |
|---|---|---|
| Hébergement en Suisse (serveur, sauvegardes, base PostgreSQL) | quelques dizaines de CHF par mois | ROADMAP.md, budget ; **devis à demander** |
| E-mails transactionnels (fournisseur suisse) | quelques CHF à quelques dizaines de CHF par mois au volume d'un Club | **devis à demander** |
| Modèle de langage (Apertus 1.5, servi par le CSCS) | à l'appel ; le service tourne aussi sans modèle | conditions d'utilisation **à vérifier** pour un pilote |
| Support et exploitation | temps humain : le vrai coût | à mesurer pendant le pilote |
| Audit de sécurité annuel | forfait | **devis à demander** |

Le coût technique est faible : un seul processus, un journal, une base. **Le coût réel est humain** (secrétariat,
support, animation). C'est pour cela que le pilote mesure aussi le temps passé par le secrétariat
([GUIDE_PILOTE_SECRETARIAT.md](GUIDE_PILOTE_SECRETARIAT.md)).

## Grille de prix — hypothèse H1 (à discuter, aucun chiffre validé)

Une grille ne se fixe pas avant le pilote. Ce que l'on peut préparer, c'est **la règle** :

- un forfait annuel par Club, par tranche de représentants (le Club compte 173 représentants dans la liste reçue le
  03.10.2026) ;
- le forfait couvre l'hébergement, les e-mails, l'audit annuel et une part du support ;
- les clubs partenaires (adhésion croisée, lot 8) paient leur propre forfait, réduit tant qu'ils comptent moins de 3 entreprises actives (en dessous, le service ne peut rien leur montrer : le
  seuil de confidentialité « < 3 » est compté par entreprise).

**Ce qu'il faut savoir avant de chiffrer** : le temps de secrétariat mesuré pendant le pilote ; les devis
d'hébergement et d'audit ; ce que le Club dépense aujourd'hui pour l'animation de son réseau (à demander au Club).

## Ce qui ferait échouer le modèle

- le pilote n'atteint pas ses critères : on arrête, ou on change le produit, **avant** de demander un prix ;
- le temps de secrétariat dépasse ce que le Club peut donner : le modèle H1 ne tient pas sans un poste financé ;
- un seul club : les coûts fixes (audit, juriste) pèsent sur 173 représentants. L'ouverture transfrontalière (Interreg)
  sert aussi à les répartir.

# Vitrine · lot 1 — Fondations de production

> **Construit — branche annee-1, pas dans la démo.** Sorties réelles du 04.10 (nuit), REFAITES après les correctifs de
> l'audit du lot 1 : serveur complet lancé avec `HACKVS_ESSAIS_DB=postgresql://…` contre un PostgreSQL 16 local (base
> jetable), `HACKVS_METRIQUES=1`. `/sante/pret` ne dit plus le nombre de faits (route publique) ; la sauvegarde est au
> format v2 (numéros des faits conservés, empreinte sur chaque ligne entière) ; une adresse fautive est refusée.

```text
$ curl /sante/pret
{"pret":true,"schema":2}
$ curl /metriques  (HACKVS_METRIQUES=1, depuis cette machine)
# HELP clubpulse_requetes_total Requêtes servies, par classe de statut HTTP.
# TYPE clubpulse_requetes_total counter
clubpulse_requetes_total{classe="2xx"} 2
clubpulse_requetes_total{classe="3xx"} 0
clubpulse_requetes_total{classe="4xx"} 0
clubpulse_requetes_total{classe="5xx"} 0
# HELP clubpulse_duree_requetes_secondes Durée de traitement des requêtes.
# TYPE clubpulse_duree_requetes_secondes summary
clubpulse_duree_requetes_secondes_somme 0.260735
clubpulse_duree_requetes_secondes_nombre 2
# HELP clubpulse_journal_faits Faits dans le journal du Club.
# TYPE clubpulse_journal_faits gauge
clubpulse_journal_faits 16
# HELP clubpulse_demarre_depuis_secondes Temps depuis le démarrage du processus.
# TYPE clubpulse_demarre_depuis_secondes gauge
clubpulse_demarre_depuis_secondes 1

$ python scripts/sauvegarde.py sauvegarder postgresql://… sauvegarde.jsonl
sauvegardé : 16 faits · empreinte e8cce728734bed59… → sauvegarde.jsonl
$ python scripts/sauvegarde.py verifier sauvegarde.jsonl
valide : 16 faits · empreinte e8cce728734bed59…
$ python scripts/sauvegarde.py restaurer restaure.db sauvegarde.jsonl   # PostgreSQL → SQLite
restauré : 16 faits · empreinte vérifiée
$ python scripts/sauvegarde.py sauvegarder club_puls.db s.jsonl   # faute de frappe dans l'adresse
REFUSÉ : aucun journal à cette adresse : club_puls.db
```

Ce que ça montre : le journal du Club vit dans PostgreSQL ; la disponibilité se lit en une requête ; les métriques ne
disent rien de qui fait quoi (aucune étiquette par route ni par membre) ; une sauvegarde faite sur PostgreSQL se
restaure dans SQLite, empreinte vérifiée.

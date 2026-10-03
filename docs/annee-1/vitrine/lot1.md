# Vitrine · lot 1 — Fondations de production

> **Construit — branche annee-1, pas dans la démo.** Sorties réelles du 04.10 (nuit), serveur complet lancé avec
> `HACKVS_ESSAIS_DB=postgresql://…` contre un PostgreSQL 16 local (base jetable), `HACKVS_METRIQUES=1`.
> (Le compteur « démarré depuis » valait 0 : il partait de la première requête ; corrigé juste après, il part du
> chargement du serveur.)

```text
$ curl /sante/pret
{"pret":true,"schema":2,"faits":16}
$ curl /metriques  (HACKVS_METRIQUES=1, depuis cette machine)
# HELP clubpulse_requetes_total Requêtes servies, par classe de statut HTTP.
# TYPE clubpulse_requetes_total counter
clubpulse_requetes_total{classe="2xx"} 3
clubpulse_requetes_total{classe="3xx"} 0
clubpulse_requetes_total{classe="4xx"} 0
clubpulse_requetes_total{classe="5xx"} 0
# HELP clubpulse_duree_requetes_secondes Durée de traitement des requêtes.
# TYPE clubpulse_duree_requetes_secondes summary
clubpulse_duree_requetes_secondes_somme 0.248037
clubpulse_duree_requetes_secondes_nombre 3
# HELP clubpulse_journal_faits Faits dans le journal du Club.
# TYPE clubpulse_journal_faits gauge
clubpulse_journal_faits 16
# HELP clubpulse_demarre_depuis_secondes Temps depuis le démarrage du processus.
# TYPE clubpulse_demarre_depuis_secondes gauge
clubpulse_demarre_depuis_secondes 0

$ python scripts/sauvegarde.py sauvegarder postgresql://… sauvegarde.jsonl
sauvegardé : 16 faits · empreinte be1d00aa11f3a90e… → pg.jsonl

$ python scripts/sauvegarde.py restaurer restaure.db sauvegarde.jsonl   # PostgreSQL → SQLite
restauré : 16 faits · empreinte vérifiée
```

Ce que ça montre : le journal du Club vit dans PostgreSQL ; la disponibilité se lit en une requête ; les métriques ne
disent rien de qui fait quoi (aucune étiquette par route ni par membre) ; une sauvegarde faite sur PostgreSQL se
restaure dans SQLite, empreinte vérifiée.

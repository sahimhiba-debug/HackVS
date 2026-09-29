# 18 — Liste de contrôle de la démo en direct

Avant de monter sur scène :
- [ ] `cd prototype && python -m pytest -q` vert ; `python scripts/validate_competition_claims.py` → code 0.
- [ ] Serveur local lancé (`uvicorn app.main:app`), SANS dépendre du réseau de la salle.
- [ ] Ouvrir `/demo/stage`, appuyer sur **R** (réinitialiser) ; vérifier « étape 0/9 ».
- [ ] Faire défiler une fois toute la scène (→ ×9, et un clic sur une relation à l'étape 6), puis **R**.
- [ ] **Si un modèle d'IA est configuré** : l'étape 1 change ; relire à l'écran les chiffres des étapes 2, 5, 7 avant de
      les dire (les chiffres du pitch sont ceux de la scène sans modèle).
- [ ] `python scripts/mesurer_scene.py --largeur <projecteur>` : aucune erreur, attente < 1 s par étape.
- [ ] Zoom navigateur réglé pour le projecteur ; mode sombre / clair vérifié.
- [ ] Vidéo `competition/video/demo.webm` ouverte dans un second onglet (plan B).
- [ ] Notifications désactivées, onglets personnels fermés, aucune clé d'API en variable d'environnement affichée.

Pendant : un clic = une idée. Ne pas lire l'écran : dire la phrase de la colonne « Ce que l'on dit » (09_DEMO_SCRIPT).
Si un clic ne répond pas : attendre 2 s (une seule action à la fois est acceptée), puis continuer ; en cas de blocage,
**R** puis « Rejouer tout » jusqu'à l'étape voulue, ou basculer sur la vidéo.

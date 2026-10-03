# Outils de la session cloud (archivés tels quels, 02.10)

| Script | Rôle |
|---|---|
| `md2pdf.py` | les `0*_*.md` de `docs/presentation/` → un PDF (Chromium) |
| `fiches.py` | fiches du présentateur (03b + captures réelles + aperçus de slides) → PDF A4 paysage |
| `verif_deck.py` | vérifications du deck : navigation clavier complète, réseau coupé, 60 i/s, contraste AA, mouvement réduit, plan B du film |
| `verif_jour.py` | vérifications du mode jour/nuit : contraste AA dans les deux modes, touche J, `?mode=`, écran neutre N |
| `cartes.py` | les deux cartes d'une page du jour J (régie de V2, V1) → `livrables/CARTE_*.html` (+ PDF) ; chemins relatifs |
| `script_imprimable.py` | `03_SCRIPT_ORAL_v2.md` → `livrables/SCRIPT_v2_IMPRIMABLE.html` (+ PDF si Playwright) : une colonne par intervenant, chronos ; chemins relatifs, se relance tel quel sur le Mac |

Chemins absolus de la session cloud (`/home/user/HackVS`, scratchpad, `/opt/pw-browsers/chromium`) : à adapter avant
de les relancer sur un Mac. Nécessitent Playwright (outillage E2E du dépôt).

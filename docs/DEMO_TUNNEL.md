# Démo publique sur le Mac du pitch, derrière un tunnel

Il n'y a pas de budget d'hébergement. **La démo est servie depuis notre machine, à Martigny, via un tunnel chiffré.**

- Le serveur écoute **seulement 127.0.0.1:8000** sur le Mac de présentation.
- Un tunnel gratuit lui donne une adresse HTTPS publique.
- Le guide VPS ([DEPLOIEMENT.md](DEPLOIEMENT.md)) reste rangé en « production future », pour le pilote.

| | Solution principale | Secours |
|---|---|---|
| Tunnel | **Tailscale Funnel** | Tunnel rapide Cloudflare (`trycloudflare.com`) |
| Adresse | **stable** : `https://<mac>.<tailnet>.ts.net` | **aléatoire à chaque lancement** |
| Limites connues | voir la doc Tailscale | **200 requêtes simultanées** au plus (au-delà : 429) ; **pas de SSE** |
| Le relais peut-il lire les données ? | **non** : le TLS se termine sur le Mac, le relais transporte du chiffré | **oui, techniquement** : le TLS se termine chez Cloudflare. Ne jamais dire « le relais ne peut pas lire » pour ce tunnel. |

Sources : documentation Cloudflare « Quick Tunnels » (limite de 200 requêtes en vol, SSE non pris en charge) ;
documentation Tailscale Funnel. À relire le jour J : ces services changent.

## Ce qui a été vérifié dans le code (tests)

1. **Pas de SSE sur les écrans en direct de Club Pulse.**
   - Le téléphone, l'écran géant, la régie, l'Établi, la projection, la console et Suivi se mettent à jour par
     interrogation périodique (`fetch` toutes les 1 à 2 s). Aucun `EventSource`, aucun WebSocket dans `web/pulse/`.
   - Seul l'**ancien prototype** utilise des SSE (`/api/flux`). Il n'est pas servi par défaut (`HACKVS_ANCIEN_PROTOTYPE` ≠ 1), ni
     montré au pitch.
   - Le tunnel Cloudflare de secours fonctionne donc tel quel : aucun repli à ajouter.
2. **Aucune limite par adresse IP.**
   - Derrière un tunnel, toutes les requêtes arrivent de 127.0.0.1 (le démon du tunnel tourne sur le Mac).
   - Les limites de débit sont par passe de salle, par session, par code, ou globales ; le plafond de la salle est de 80.
   - Test : `tests/test_tunnel.py::test_quatre_vingts_telephones_derriere_une_seule_ip_ne_sont_pas_bloques`. 80 téléphones
     derrière une seule IP scannent, déclarent, relisent 5 fois et répondent : aucun 429.
3. **« Local » ne veut plus dire « cette machine ».**
   - Une requête qui porte un en-tête de relais n'est jamais traitée comme locale. Les en-têtes reconnus :
     `X-Forwarded-For`, `Forwarded`, `CF-Connecting-IP`, `CF-Ray`, `Tailscale-Funnel-Request`, `X-Real-IP`.
   - Sinon, la salle entière aurait eu la console (test rouge d'abord, `tests/test_tunnel.py`).
   - Nous n'avons pas pu vérifier depuis la session cloud quels en-têtes Funnel ajoute (documentation inaccessible). Le
     lanceur **exige donc `HACKVS_CONSOLE_JETON`** : la console ne dépend jamais de l'adresse d'origine.
4. **Le QR de la salle est servi en direct**, à `<PUBLIC_BASE_URL>/qr/salle.svg`, sans cache.
   - Il suit l'adresse du tunnel ; il n'est jamais figé dans le deck. Salle fermée : une image « salle fermée ».
   - `/qr/salle.txt` donne l'adresse encodée, pour la vérifier — **sur le Mac seulement** (ou avec le jeton de console) : à travers le tunnel, le QR et son jeton ne sortent jamais (audit D5).

## Avant le pitch (la veille, puis à H-1)

1. **Alimentation branchée**, Wi-Fi de la salle testé. **Partage de connexion 4G** prêt sur un téléphone, en secours
   (Réglages → Partage de connexion). Le tunnel suit le changement de réseau : relancez-le si l'adresse ne répond plus.
2. Désactiver la veille : le lanceur enveloppe le serveur dans `caffeinate -dimsu`. Vérifiez aussi Réglages →
   Économiseur d'énergie (« Empêcher la suspension automatique » sur secteur).
3. Préparer un jeton de console :

   ```sh
   export HACKVS_CONSOLE_JETON="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
   ```

   La régie le demande une fois par onglet (jamais dans l'URL).

## Lancer — solution principale : Tailscale Funnel

```sh
# 1. une fois : installer Tailscale (App Store ou tailscale.com), se connecter ; dans la console d'administration du
#    tailnet, activer HTTPS et autoriser Funnel pour ce Mac.
# 2. le serveur (terminal 1)
export PUBLIC_BASE_URL="https://<mac>.<tailnet>.ts.net"
./demo-tunnel.sh
# 3. le tunnel (terminal 2) — expose 127.0.0.1:8000 sur le port 443 public
tailscale funnel 8000          # ou, selon la version : tailscale funnel --bg 8000 ; arrêt : tailscale funnel reset
```

## Lancer — secours : tunnel rapide Cloudflare

```sh
brew install cloudflared
cloudflared tunnel --url http://127.0.0.1:8000     # affiche https://<mots-aléatoires>.trycloudflare.com
# l'adresse change à CHAQUE lancement : relancer le serveur avec la nouvelle
export PUBLIC_BASE_URL="https://<mots-aléatoires>.trycloudflare.com"
./demo-tunnel.sh
```

Le QR étant servi en direct, l'écran géant et `/qr/salle.svg` suivent la nouvelle adresse dès le redémarrage. Le deck
n'a rien à régénérer.

## Vérifier à travers le tunnel

```sh
curl -fsS "$PUBLIC_BASE_URL/sante"
curl -fsS -H "X-Pulse-Console: $HACKVS_CONSOLE_JETON" "$PUBLIC_BASE_URL/api/pulse/console/salle/etat"
curl -fsS "http://127.0.0.1:8000/qr/salle.txt"               # sur le Mac seulement : à travers le tunnel, le jeton ne sort jamais
cd prototype && python scripts/charge_salle.py --base-url "$PUBLIC_BASE_URL" --jeton "$HACKVS_CONSOLE_JETON" --n 80
```

- Le test de charge part d'**une seule machine**, donc d'une seule IP : c'est exactement la situation du tunnel.
- Il purge la salle au début et à la fin.
- Avec Cloudflare, gardez `--n 80` : 80 téléphones restent sous les 200 requêtes simultanées.

## Ce qu'on dit (et ne dit pas)

- **Dire** : « la démo est servie depuis notre machine, à Martigny, via un tunnel chiffré ».
- **Avec Tailscale Funnel seulement** : « le relais ne peut pas lire les données ».
- **Jamais** cette dernière phrase si le secours Cloudflare est en service.

// Jeton de la console du Club (HACKVS_CONSOLE_JETON) pour les écrans de l'animation : console, Établi, projection, régie.
// Sans jeton configuré côté serveur, rien ne change : « 1 » suffit depuis cette machine, et rien n'est jamais demandé.
// Avec un jeton (déploiement joignable du réseau), chaque onglet le garde dans son sessionStorage — jamais dans l'URL,
// jamais en stockage durable. Un onglet qui ne l'a pas (ouvert par un lien rel=noopener, ou tapé à la main) le demande
// d'abord aux onglets de l'animation déjà déverrouillés, par un canal de diffusion de la MÊME origine et du même
// navigateur ; à défaut, à l'animatrice. La garde du serveur reste seule juge : un jeton faux reste refusé (403).
const CLE = "console-jeton";
const lire = () => { try { return sessionStorage.getItem(CLE); } catch { return null; } };
const garder = (j) => { try { sessionStorage.setItem(CLE, j); } catch { /* stockage indisponible : jeton de cette page seulement */ } };

let memoire = null;          // si sessionStorage est indisponible
let canal = null;
try { canal = new BroadcastChannel("club-pulse-console-jeton"); } catch { /* navigateur sans canal : on demandera */ }
if (canal) {
  canal.addEventListener("message", (e) => {
    const m = e.data || {};
    const j = lire() || memoire;
    if (m.type === "demande" && typeof m.id === "string" && j) canal.postMessage({ type: "reponse", id: m.id, jeton: j });
  });
}

export const jeton = () => lire() || memoire || "1";

function demanderAuxOnglets(delai = 400) {
  if (!canal) return Promise.resolve(null);
  return new Promise((ok) => {
    const id = Math.random().toString(36).slice(2) + Date.now().toString(36);
    const ecoute = (e) => {
      const m = e.data || {};
      if (m.type === "reponse" && m.id === id && typeof m.jeton === "string") { fin(); ok(m.jeton); }
    };
    const minuterie = setTimeout(() => { fin(); ok(null); }, delai);
    const fin = () => { clearTimeout(minuterie); canal.removeEventListener("message", ecoute); };
    canal.addEventListener("message", ecoute);
    canal.postMessage({ type: "demande", id });
  });
}

let enCours = null, demandes = 0;
// Un seul jeton demandé à la fois, même si plusieurs appels sont refusés en même temps. Au plus deux demandes par
// chargement de page : « Annuler », ou deux jetons refusés, ne sont pas redemandés à chaque rafraîchissement (recharger
// la page pour réessayer).
function obtenir(refuse) {
  const actuel = jeton();
  if (actuel !== refuse) return Promise.resolve(actuel);
  if (enCours) return enCours;
  enCours = (async () => {
    let j = await demanderAuxOnglets();
    if (!j || j === refuse) {
      if (window.top !== window.self) {
        // JOUR J (audit B1) : intégrée au deck, la page ne demande JAMAIS rien devant le public ; elle prévient le deck,
        // qui dit « jeton manquant » et garde la touche B. Le message ne porte aucun secret.
        try { window.parent.postMessage({ type: "club-pulse-jeton-manquant" }, "*"); } catch (e) { /* pas de parent */ }
        return null;
      }
      if (demandes >= 2) return null;
      demandes += 1;
      j = window.prompt("Jeton de la console du Club :");
    }
    if (!j) { demandes = 2; return null; }
    garder(j);
    memoire = j;
    return j;
  })().finally(() => { enCours = null; });
  return enCours;
}

// fetch avec l'en-tête de console ; sur un refus qui porte sur le jeton, obtient le jeton puis réessaie une fois.
export async function consoleFetch(chemin, options = {}) {
  const appel = (j) => fetch(chemin, { ...options, headers: { ...(options.headers || {}), "X-Pulse-Console": j } });
  const essaye = jeton();
  const r = await appel(essaye);
  if (r.status !== 403) return r;
  const d = await r.clone().json().catch(() => ({}));
  if (!/jeton/i.test(d.detail || "")) return r;
  const j = await obtenir(essaye);
  return j && j !== essaye ? appel(j) : r;
}

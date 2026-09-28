// Utilitaires partagés. Tout contenu issu des données passe par textContent (jamais innerHTML).

export const $ = (sel, racine = document) => racine.querySelector(sel);

export const etat = {
  config: null,       // /api/etat
  moi: null,          // /api/moi
  membreId: null,     // identité incarnée (démo)
  scene: false,       // affiché dans la vue « scène »
  vue: "nouveau",
};

export function h(tag, attrs = {}, ...enfants) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") el.setAttribute("style", v);
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "value") el.value = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const e of enfants.flat(Infinity)) {
    if (e === null || e === undefined || e === false) continue;
    el.append(e instanceof Node ? e : document.createTextNode(String(e)));
  }
  return el;
}

export async function api(chemin, { methode, corps } = {}) {
  const options = { method: methode || (corps === undefined ? "GET" : "POST"), headers: {} };
  if (etat.membreId) options.headers["X-Membre"] = etat.membreId;
  if (corps !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(corps);
  }
  let rep;
  try { rep = await fetch(chemin, options); }
  catch { throw new Error("Serveur injoignable. Vérifiez qu'il est lancé (voir README)."); }
  const data = await rep.json().catch(() => ({}));
  if (!rep.ok) {
    const d = data.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? "Données invalides." : `Erreur ${rep.status}`);
  }
  return data;
}

export function toast(msg, genre = "") {
  const t = h("div", { class: "toast " + genre }, msg);
  $("#toasts").append(t);
  setTimeout(() => t.remove(), genre === "erreur" ? 6000 : 4500);
}

export function occupe(bouton, texte) {
  bouton.disabled = true;
  bouton.dataset.libelle = bouton.textContent;
  bouton.replaceChildren(h("span", { class: "chargement" }, texte));
}
export function libre(bouton) {
  bouton.disabled = false;
  if (bouton.dataset.libelle) bouton.textContent = bouton.dataset.libelle;
}

export function transition(fn) {
  if (document.startViewTransition && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return document.startViewTransition(fn);
  }
  fn();
}

export function entre(el) {
  el.classList.remove("entre"); void el.offsetWidth; el.classList.add("entre");
}

export const LANGUES = { fr: "français", de: "allemand", en: "anglais", it: "italien" };

export function dateCourte(iso) {
  try { return new Date(iso).toLocaleDateString("fr-CH", { day: "numeric", month: "long" }); } catch { return iso; }
}

export function prenom(nom) { return (nom || "").split(" ")[0]; }

export function titreBesoin(b) {
  const p = (b.criteres || []).find((c) => c.type === "expertise" || c.type === "texte_libre");
  if (!p) return "Besoin sans compétence";
  return p.type === "texte_libre" ? `« ${p.valeur} »` : p.libelle;
}

export function erreurBloc(msg, reessayer) {
  return h("div", { class: "erreur-bloc", role: "alert" }, h("strong", {}, "Impossible de charger. "), msg,
    reessayer ? h("div", { class: "actions" }, h("button", { class: "btn petit", type: "button", onclick: reessayer }, "Réessayer")) : null);
}

// Petit bus d'événements entre modules (rafraîchissements, changement de vue).
const abonnes = {};
export function sur(evt, fn) { (abonnes[evt] ||= []).push(fn); }
export function emettre(evt, data) { (abonnes[evt] || []).forEach((fn) => fn(data)); }

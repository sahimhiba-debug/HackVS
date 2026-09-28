// Point d'entrée : identité (démo), onglets, compteurs, mises à jour en direct.
import { $, api, emettre, etat, h, sur, toast, transition, prenom } from "./outils.js";
import { vueNouveau, majEntete } from "./vue-nouveau.js";
import { ouvrirBesoin, vueBesoins } from "./vue-besoins.js";
import { vueBourse } from "./vue-bourse.js";
import { aMonTour, vueSuivi } from "./vue-suivi.js";
import { vueProfil } from "./vue-profil.js";

const VUES = { nouveau: null, besoins: vueBesoins, bourse: vueBourse, suivi: vueSuivi, profil: vueProfil };
const connu = { bourse: null, relations: null };  // pour détecter les nouveautés et notifier

function lireStockage(cle) { try { return localStorage.getItem(cle); } catch { return null; } }
function ecrireStockage(cle, v) { try { localStorage.setItem(cle, v); } catch { /* navigation privée */ } }

async function init() {
  const params = new URLSearchParams(location.search);
  etat.scene = params.has("scene");
  try { etat.config = await api("/api/etat"); }
  catch (e) {
    $("#principal").replaceChildren(h("div", { class: "erreur-bloc", role: "alert" }, e.message)); return;
  }
  const c = etat.config;
  etat.membreId = params.get("membre") || (!etat.scene && lireStockage("fil-membre")) || c.utilisateur_defaut;

  // Badges : toujours dire ce qui est réel et ce qui ne l'est pas.
  const badges = $("#badges");
  badges.append(c.donnees_fictives ? h("span", { class: "badge demo" }, "Démo · données fictives") : h("span", { class: "badge live" }, "Mode réel"));
  const nomLLM = { claude: "Claude", apertus: "Apertus (IA suisse)" }[c.fournisseur_llm] || c.fournisseur_llm;
  badges.append(c.analyseur_claude_disponible
    ? h("span", { class: "badge live", title: "Analyse du besoin par un modèle de langage, vérifiée par le code." }, `Analyse : ${nomLLM}`)
    : c.semantique_locale
      ? h("span", { class: "badge local", title: "Règles + modèle sémantique multilingue exécuté sur cette machine (aucune donnée ne sort)." }, "Analyse : règles + IA locale")
      : h("span", { class: "badge local", title: "Analyse par règles locales, sans IA générative ni réseau." }, "Analyse : règles locales"));
  $("#bandeau-demo").hidden = !c.donnees_fictives || etat.scene;
  $("#pied").textContent = "Prototype exploratoire préparé avant Hack VS 2026 · "
    + (c.donnees_fictives ? "données fictives, aucun message réel envoyé" : "mode réel");
  if (c.donnees_fictives) {
    $("#pied").append(" · ", h("a", { href: "/club" }, "Vue du Club"), " · ", h("a", { href: "/scene" }, "Scène"),
      " · ", h("button", { class: "lien", type: "button", onclick: reinitialiser }, "Réinitialiser la démo"));
    await installerPersona();
  }
  try { etat.moi = await api("/api/moi"); }
  catch (e) { toast(e.message, "erreur"); return; }

  document.querySelectorAll(".onglet").forEach((b) => b.addEventListener("click", () => afficher(b.dataset.vue)));
  document.querySelector(".onglets").addEventListener("keydown", navigationClavier);
  sur("vue", afficher);
  sur("ouvrir-besoin", (id) => { ouvrirBesoin(id); afficher("besoins"); });
  sur("rafraichir", rafraichir);

  vueNouveau();
  const depart = params.get("vue") || (lireStockage("fil-vue-" + etat.membreId) || "nouveau");
  afficher(VUES.hasOwnProperty(depart) ? depart : "nouveau");
  await compteurs(true);
  ecouter();
}

async function installerPersona() {
  const bloc = $("#persona");
  if (etat.scene) return;  // en scène, l'identité est fixée par l'URL
  try {
    const membres = await api("/api/membres");
    const sel = $("#choix-membre");
    const groupes = { membre_club: "Membres du Club", exposant: "Exposants (non membres)" };
    for (const [type, lib] of Object.entries(groupes)) {
      sel.append(h("optgroup", { label: lib }, membres.filter((m) => m.type === type).map((m) =>
        h("option", { value: m.id, selected: m.id === etat.membreId }, `${m.nom} · ${m.entreprise}`))));
    }
    sel.addEventListener("change", () => {
      ecrireStockage("fil-membre", sel.value);
      location.search = "";  // recharge proprement avec la nouvelle identité
    });
    bloc.hidden = false;
  } catch { /* mode réel : pas de changement d'identité */ }
}

function afficher(vue) {
  etat.vue = vue;
  ecrireStockage("fil-vue-" + etat.membreId, vue);
  document.querySelectorAll(".onglet").forEach((b) => {
    const actif = b.dataset.vue === vue;
    b.setAttribute("aria-selected", String(actif));
    b.tabIndex = actif ? 0 : -1;
  });
  transition(() => {
    document.querySelectorAll(".vue").forEach((v) => (v.hidden = v.id !== "vue-" + vue));
  });
  if (vue === "nouveau") majEntete();
  VUES[vue]?.();
  window.scrollTo({ top: 0 });
}

function navigationClavier(e) {
  const onglets = [...document.querySelectorAll(".onglet")];
  const i = onglets.indexOf(document.activeElement);
  if (i < 0) return;
  const j = e.key === "ArrowRight" ? (i + 1) % onglets.length : e.key === "ArrowLeft" ? (i - 1 + onglets.length) % onglets.length : null;
  if (j !== null) { e.preventDefault(); onglets[j].focus(); afficher(onglets[j].dataset.vue); }
}

async function compteurs(silencieux = false) {
  let bourse, relations, besoins;
  try { [bourse, relations, besoins] = await Promise.all([api("/api/bourse"), api("/api/relations"), api("/api/besoins")]); }
  catch { return; }
  const ouverts = bourse.filter((x) => x.correspondance && !x.relation);
  const aFaire = relations.filter(aMonTour);
  const offresRecues = relations.filter((r) => r.mon_role === "auteur" && r.initiateur === "aidant" && r.etat === "proposee");
  majCompteur("bourse", ouverts.length);
  majCompteur("suivi", aFaire.length);
  majCompteur("besoins", offresRecues.length);

  // Notifications : uniquement ce qui est nouveau pour CE membre.
  if (!silencieux && connu.bourse) {
    for (const x of ouverts) if (!connu.bourse.has(x.besoin.id)) {
      const qui = x.besoin.auteur?.anonyme ? "Un membre" : prenom(x.besoin.auteur?.nom);
      toast(`${qui} a besoin de ce que vous faites. Voir la Bourse.`, "info");
    }
    for (const r of relations) {
      const avant = connu.relations.get(r.id);
      if (avant === r.etat) continue;
      const qui = r.autre?.anonyme ? "Un membre" : prenom(r.autre?.nom);
      if (!avant && r.je_suis_destinataire) toast(r.initiateur === "aidant" ? `${qui} vous propose son aide.` : `${qui} vous sollicite.`, "info");
      else if (avant && r.etat === "acceptee" && !r.je_suis_destinataire) toast(`${qui} a accepté : coordonnées partagées.`, "info");
      else if (avant && r.etat === "declinee" && !r.je_suis_destinataire) toast(`${qui} a décliné.`, "info");
      else if (avant && r.etat === "annulee" && r.motif_fin) toast(r.motif_fin, "info");
    }
  }
  connu.bourse = new Set(ouverts.map((x) => x.besoin.id));
  connu.relations = new Map(relations.map((r) => [r.id, r.etat]));
  void besoins;
}

function majCompteur(nom, n) {
  const el = document.querySelector(`[data-compteur="${nom}"]`);
  const avant = Number(el.textContent || 0);
  el.textContent = n;
  el.hidden = n === 0;
  if (n > avant) { el.classList.remove("pulse"); void el.offsetWidth; el.classList.add("pulse"); }
  el.setAttribute("aria-label", `${n} élément${n > 1 ? "s" : ""} à voir`);
}

let minuteur;
function rafraichir() {
  clearTimeout(minuteur);
  minuteur = setTimeout(async () => {
    await compteurs();
    if (etat.vue !== "nouveau") VUES[etat.vue]?.();
  }, 150);
}

function ecouter() {
  // Flux d'événements du serveur : la scène à deux membres se met à jour en direct.
  let seq = etat.config.seq;
  const connecter = () => {
    const es = new EventSource(`/api/flux?depuis=${seq}`);
    es.onmessage = (m) => {
      const ev = JSON.parse(m.data);
      seq = ev.seq;
      if (ev.type === "reinitialisation") { location.reload(); return; }
      const concerne = ev.concerne?.includes(etat.membreId) || ["besoin_publie", "besoin_modifie", "besoin_publier", "consentement", "profil_modifie"].includes(ev.type);
      if (concerne && ev.acteur !== etat.membreId) rafraichir();
    };
    es.onerror = () => { es.close(); setTimeout(connecter, 2000); };
  };
  connecter();
}

async function reinitialiser() {
  if (!confirm("Effacer tous les besoins et mises en relation de la démo ?")) return;
  try { await api("/api/demo/reinitialiser", { corps: {} }); location.reload(); }
  catch (e) { toast(e.message, "erreur"); }
}

init();

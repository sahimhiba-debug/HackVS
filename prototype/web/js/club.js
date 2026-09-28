// Vue du Club : indicateurs calculés par le serveur, compétences à recruter, offres à faire connaître.
import { $, api, dateCourte, h, occupe, libre, toast } from "./outils.js";

function kpi(chiffre, sur, texte) {
  return h("div", { class: "kpi" },
    h("div", { class: "chiffre" }, String(chiffre), sur !== null ? h("small", {}, ` / ${sur}`) : null),
    h("p", {}, texte));
}

let precedents = null;  // compétences à recruter lors du dernier chargement (pour annoncer un manque comblé)

async function charger() {
  const zone = $("#contenu");
  let t;
  try { t = await api("/api/club/tableau"); }
  catch (e) { zone.replaceChildren(h("div", { class: "erreur-bloc", role: "alert" }, e.message)); return; }
  if (!t.besoins.total) {
    zone.replaceChildren(h("div", { class: "vide" }, h("strong", {}, "Aucune activité pour l'instant."),
      "Publiez un besoin depuis l'espace membre, ou chargez l'historique fictif pour voir la vue du Club en situation."));
    return;
  }
  const r = t.relations.resultats;
  const actuels = new Set(t.a_recruter.map((m) => m.competence));
  const combles = precedents ? [...precedents].filter((c) => !actuels.has(c)) : [];
  precedents = actuels;
  const kpis = h("div", { class: "kpis" },
      kpi(t.besoins.total, null, `besoins exprimés${t.periode.debut ? ` depuis le ${dateCourte(t.periode.debut)}` : ""}`),
      kpi(t.besoins.avec_mise_en_relation, t.besoins.total, "ont reçu au moins une mise en relation"),
      kpi(t.taux_resolution.resolus, t.taux_resolution.clos, "besoins clos ont été résolus grâce à un membre"),
      kpi(r.utile + r.affaire_en_cours, r.utile + r.affaire_en_cours + r.pas_pertinent,
        `rencontres jugées utiles ou suivies d'une affaire (${r.affaire_en_cours} affaire${r.affaire_en_cours > 1 ? "s" : ""} en cours)`),
      t.delai_premiere_relation_h.mediane !== null
        ? kpi(t.delai_premiere_relation_h.mediane < 48 ? `${Math.round(t.delai_premiere_relation_h.mediane)} h` : `${Math.round(t.delai_premiere_relation_h.mediane / 24)} j`, null,
          `délai médian avant la première mise en relation (sur ${t.delai_premiere_relation_h.n})`) : null);
  zone.replaceChildren(...[
    combles.length ? h("div", { class: "comble", role: "status" }, combles.map((c) =>
      h("p", {}, h("strong", {}, "Comblé : "), `« ${c} » : un membre propose désormais cette compétence.`))) : null,
    h("section", { class: "deux" },
      h("div", {},
        h("h2", {}, "Compétences à recruter"),
        h("p", { class: "sous" }, "Des membres les ont cherchées ; aucun membre actuel ne les propose. Autant d'entreprises à inviter au Club."),
        t.a_recruter.length ? h("div", { class: "recruter" }, t.a_recruter.map((m, i) =>
          h("article", { class: "manque", style: `animation-delay:${i * 70}ms` },
            h("span", { class: "n", "aria-label": `${m.demandes} demandes` }, String(m.demandes)),
            h("span", { class: "quoi" }, m.competence),
            h("span", { class: "detail" }, `${m.demandes > 1 ? "demandes" : "demande"} sans réponse · dernière le ${dateCourte(m.derniere)}`
              + (m.pistes.length ? ` · piste voisine : ${m.pistes.join(", ")}` : "")),
            h("button", { class: "btn petit action", type: "button", onclick: () => copier(m) }, "Copier une invitation"))))
          : h("p", { class: "aide" }, "Aucun besoin sans réponse : chaque demande a trouvé au moins un membre.")),
      h("div", {},
        h("h2", {}, "À faire connaître"),
        h("p", { class: "sous" }, "Compétences proposées par des membres, jamais demandées : une ressource du Club à mettre en avant lors de la prochaine soirée."),
        t.offres_dormantes.length ? h("div", { class: "dormantes" }, t.offres_dormantes.map((o) => h("span", {}, `${o.competence} · ${o.membres} membre${o.membres > 1 ? "s" : ""}`)))
          : h("p", { class: "aide" }, "Toutes les compétences proposées ont déjà été demandées."),
        h("h2", { style: "margin-top:32px" }, "Communauté"),
        h("p", {}, `${t.membres.acceptent_introductions} membres sur ${t.membres.total} acceptent d'être proposés et sollicités.`),
        h("p", {}, `${t.relations.acceptees} mises en relation acceptées sur ${t.relations.total} proposées.`))),
    h("section", { class: "bloc" }, h("h2", {}, "Activité"), kpis),
    h("p", { class: "aide" }, "Définitions : « résolu » = besoin clos par son auteur avec « résolu grâce à… » ; « à recruter » = aucun membre actuel ne correspond (recalculé maintenant) et aucune mise en relation n'a abouti. Agrégats seulement, aucun nom.")].filter(Boolean));
}

async function copier(m) {
  const texte = `Bonjour,\n\nLe Club des Affaires de la Foire du Valais réunit des dirigeants valaisans. Plusieurs membres recherchent actuellement une compétence en : ${m.competence.replace(/ \(hors catalogue\)$/, "")}. Nous serions heureux de vous présenter le Club.\n\n[Signature du Club]`;
  try { await navigator.clipboard.writeText(texte); toast("Invitation copiée (modèle à adapter).", "info"); }
  catch { toast("Copie impossible dans ce navigateur.", "erreur"); }
}

$("#historique").addEventListener("click", async (ev) => {
  if (!confirm("Remplacer les données de la démo par un historique FICTIF de 6 semaines ?")) return;
  occupe(ev.target.closest("button"), "Chargement…");
  try { const r = await api("/api/demo/historique", { corps: {} }); toast(`${r.besoins_charges} besoins fictifs chargés.`, "info"); await charger(); }
  catch (e) { toast(e.message, "erreur"); }
  finally { libre(ev.target.closest("button")); }
});

charger();
try {
  const es = new EventSource("/api/flux");
  let minuteur;
  es.onmessage = () => { clearTimeout(minuteur); minuteur = setTimeout(charger, 300); };
} catch { /* pas de mise à jour en direct */ }

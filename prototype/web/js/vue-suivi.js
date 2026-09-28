// Vue « Suivi » : toutes mes mises en relation (demandes envoyées, reçues, offres d'aide), avec les actions de mon rôle.
import { $, api, dateCourte, emettre, erreurBloc, etat, h, occupe, libre, prenom, titreBesoin, toast } from "./outils.js";
import { frise, RESULTATS } from "./composants.js";

export async function vueSuivi() {
  const racine = $("#vue-suivi");
  let rels;
  try { rels = await api("/api/relations"); }
  catch (e) { racine.replaceChildren(erreurBloc(e.message, vueSuivi)); return; }
  const aFaire = rels.filter(aMonTour);
  racine.replaceChildren(
    h("h1", {}, "Suivi"),
    h("p", { class: "sous" }, rels.length ? `${rels.length} mise${rels.length > 1 ? "s" : ""} en relation · ${aFaire.length} attend${aFaire.length > 1 ? "ent" : ""} votre action` : ""),
    rels.length ? h("div", {}, [...aFaire, ...rels.filter((r) => !aFaire.includes(r))].map(carte))
      : h("div", { class: "vide" }, h("strong", {}, "Aucune mise en relation."),
        "Sollicitez un membre depuis « Mes besoins », ou proposez votre aide depuis la Bourse."));
}

export function aMonTour(r) {
  return (r.etat === "proposee" && r.je_suis_destinataire) || ["acceptee", "rencontre_planifiee", "rencontre_faite"].includes(r.etat);
}

function carte(r) {
  const autre = r.autre || { nom: "Membre" };
  const sens = r.mon_role === "auteur"
    ? (r.initiateur === "auteur" ? "Vous l'avez sollicité·e pour votre besoin" : "Vous propose son aide")
    : (r.initiateur === "aidant" ? "Vous proposez votre aide" : "Vous sollicite pour son besoin");
  const act = (action, corps = {}) => async (ev) => {
    occupe(ev.target.closest("button"), "…");
    try { await api(`/api/relations/${r.id}/${action}`, { corps }); emettre("rafraichir"); }
    catch (e) { toast(e.message, "erreur"); libre(ev.target.closest("button")); }
  };
  const boutons = [];
  if (r.etat === "proposee" && r.je_suis_destinataire) {
    boutons.push(h("button", { class: "btn primaire petit", type: "button", onclick: act("accepter") }, "Accepter et partager nos coordonnées"),
      h("button", { class: "btn petit", type: "button", onclick: act("decliner") }, "Décliner"));
  }
  if (r.etat === "proposee" && !r.je_suis_destinataire) {
    boutons.push(h("span", { class: "aide" }, `En attente de la réponse de ${autre.anonyme ? "ce membre" : prenom(autre.nom)}.`),
      h("button", { class: "lien", type: "button", onclick: act("retirer") }, "Retirer ma demande"));
  }
  if (r.etat === "acceptee") {
    const d = h("input", { type: "date", "aria-label": "Date de la rencontre" });
    const communs = h("div", { class: "creneaux", "aria-live": "polite" });
    api(`/api/relations/${r.id}/creneaux`).then((c) => communs.replaceChildren(
      c.creneaux.length ? h("span", { class: "aide" }, "Vos disponibilités communes :") : h("span", { class: "aide" }, c.message),
      ...c.creneaux.map((x) => h("button", { class: "pilule", type: "button", onclick: act("planifier", { date_rencontre: x.date }) }, x.libelle))))
      .catch(() => communs.replaceChildren());
    boutons.push(communs, d, h("button", { class: "btn primaire petit", type: "button",
      onclick: (ev) => d.value ? act("planifier", { date_rencontre: d.value })(ev) : toast("Choisissez une date.") }, "Planifier une autre date"));
  }
  if (r.etat === "rencontre_planifiee") boutons.push(h("button", { class: "btn primaire petit", type: "button", onclick: act("confirmer_rencontre") }, "La rencontre a eu lieu"));
  if (r.etat === "rencontre_faite") {
    boutons.push(h("span", { class: "aide" }, "Cette mise en relation a-t-elle été utile ?"));
    for (const [k, v] of Object.entries(RESULTATS)) boutons.push(h("button", { class: "btn petit", type: "button", onclick: act("cloturer", { resultat: k }) }, v));
  }
  if (["acceptee", "rencontre_planifiee"].includes(r.etat)) boutons.push(h("button", { class: "lien", type: "button", onclick: act("annuler") }, "Annuler"));

  return h("article", { class: "relation" + (aMonTour(r) ? " a-faire" : "") },
    h("div", { class: "tete" },
      h("div", {}, h("span", { class: "sens" }, sens), h("div", { class: "qui" }, `${autre.nom}${autre.entreprise ? " · " + autre.entreprise : ""}`)),
      h("span", { class: "etat" }, r.libelle_etat + (r.resultat ? ` : ${RESULTATS[r.resultat]}` : ""))),
    h("p", { class: "info" }, `Besoin : ${titreBesoin(r.besoin.besoin)} · ${r.besoin.libelle_statut.toLowerCase()}`),
    frise(r),
    r.motif_fin ? h("p", { class: "info alerte" }, r.motif_fin) : null,
    r.besoin_modifie_depuis && ["proposee", "acceptee"].includes(r.etat) ? h("p", { class: "info alerte" }, "Le besoin a été modifié depuis cette mise en relation.") : null,
    h("p", { class: "info" }, r.coordonnees_partagees
      ? "Coordonnées partagées" + (etat.config.donnees_fictives ? " (démo : aucune coordonnée réelle)" : "")
      : "Coordonnées non partagées tant que la demande n'est pas acceptée."),
    r.date_rencontre ? h("p", { class: "info" }, `Rencontre prévue le ${dateCourte(r.date_rencontre)}`) : null,
    h("details", {}, h("summary", { class: "aide" }, "Voir le message"), h("p", { class: "message" }, r.message)),
    boutons.length ? h("div", { class: "boutons" }, boutons) : null);
}

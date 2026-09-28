// Vue « Profil » : ce que les autres membres voient, et le consentement aux introductions.
import { $, api, emettre, erreurBloc, etat, h, LANGUES, occupe, libre, toast } from "./outils.js";

export async function vueProfil() {
  const racine = $("#vue-profil");
  let m;
  try { m = await api("/api/moi"); etat.moi = m; }
  catch (e) { racine.replaceChildren(erreurBloc(e.message, vueProfil)); return; }
  const bascule = h("input", { type: "checkbox", checked: m.accepte_introductions, id: "consentement" });
  bascule.addEventListener("change", async () => {
    const accepte = bascule.checked;
    if (!accepte && !confirm("Retirer votre consentement ? Vous n'apparaîtrez plus dans les recherches ni dans la Bourse, et les demandes en attente qui vous sont adressées seront annulées.")) {
      bascule.checked = true; return;
    }
    bascule.disabled = true;
    try {
      const r = await api("/api/moi/consentement", { corps: { accepte } });
      toast(accepte ? "Vous pouvez de nouveau être proposé·e et sollicité·e."
        : `Consentement retiré.${r.relations_annulees.length ? ` ${r.relations_annulees.length} demande(s) en attente annulée(s).` : ""}`, "info");
      emettre("rafraichir");
    } catch (e) { toast(e.message, "erreur"); bascule.checked = !accepte; }
    finally { bascule.disabled = false; }
  });
  racine.replaceChildren(
    h("p", { class: "surtitre" }, etat.config.donnees_fictives ? "Profil fictif de démonstration" : "Votre profil"),
    h("h1", {}, m.nom),
    h("div", { class: "fiche" },
      h("dl", {},
        h("dt", {}, "Fonction"), h("dd", {}, `${m.fonction} · ${m.entreprise}`),
        h("dt", {}, "Implantation"), h("dd", {}, `${m.commune}${m.zone_implantation ? ` (${m.zone_implantation})` : ""}`),
        h("dt", {}, "Intervient en"), h("dd", {}, m.zones_service.length ? m.zones_service.join(", ") : "non renseigné"),
        h("dt", {}, "Langues"), h("dd", {}, m.langues.length ? m.langues.map((l) => LANGUES[l] || l).join(", ") : "non renseigné"),
        h("dt", {}, "Propose"), h("dd", {}, m.offre.length ? h("ul", { style: "margin:0;padding-left:18px" }, m.offre.map((o) => h("li", {}, o.texte))) : "—"),
        h("dt", {}, "Recherche"), h("dd", {}, m.recherche.length ? h("ul", { style: "margin:0;padding-left:18px" }, m.recherche.map((o) => h("li", {}, o.texte))) : "—"),
        h("dt", {}, "Présentation"), h("dd", {}, m.presentation || "—")),
      h("label", { class: "bascule", for: "consentement" }, bascule,
        h("span", {}, h("strong", {}, "J'accepte d'être proposé·e et sollicité·e par les membres du Club"),
          h("small", {}, "Désactivé : vous disparaissez des recherches et de la Bourse ; les demandes en attente qui vous sont adressées sont annulées ; les mises en relation déjà acceptées restent (vous pouvez les annuler)."))),
      h("p", { class: "aide" }, "Profil en lecture seule dans ce prototype : l'édition du profil n'est pas implémentée.")));
}

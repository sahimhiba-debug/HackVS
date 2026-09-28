// Vue « Profil » : ce que les autres membres voient, le profil en 30 secondes, le consentement.
import { $, api, emettre, erreurBloc, etat, h, LANGUES, occupe, libre, toast, transition } from "./outils.js";

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

  const zoneProposition = h("div", { id: "proposition-profil", "aria-live": "polite" });
  const saisie = h("textarea", { id: "texte-profil", rows: "4", maxlength: "3000",
    placeholder: "Ex. : Nous livrons des produits frais en camion frigorifique en Valais et à Genève. Nous parlons français et allemand. Nous cherchons des chauffeurs pour l'hiver." });

  racine.replaceChildren(
    h("p", { class: "surtitre" }, etat.config.donnees_fictives ? "Profil fictif de démonstration" : "Votre profil"),
    h("h1", {}, m.nom),
    h("div", { class: "fiche" },
      h("dl", {},
        h("dt", {}, "Fonction"), h("dd", {}, `${m.fonction} · ${m.entreprise}`),
        h("dt", {}, "Implantation"), h("dd", {}, `${m.commune}${m.zone_implantation ? ` (${m.zone_implantation})` : ""}`),
        h("dt", {}, "Intervient en"), h("dd", {}, m.zones_service.length ? m.zones_service.join(", ") : "non renseigné"),
        h("dt", {}, "Langues"), h("dd", {}, m.langues.length ? m.langues.map((l) => LANGUES[l] || l).join(", ") : "non renseigné"),
        h("dt", {}, "Propose"), h("dd", {}, m.offre.length ? h("ul", { class: "liste-simple" }, m.offre.map((o) => h("li", {}, o.texte))) : "—"),
        h("dt", {}, "Recherche"), h("dd", {}, m.recherche.length ? h("ul", { class: "liste-simple" }, m.recherche.map((o) => h("li", {}, o.texte))) : "—"),
        h("dt", {}, "Présentation"), h("dd", {}, m.presentation || "—")),
      h("label", { class: "bascule", for: "consentement" }, bascule,
        h("span", {}, h("strong", {}, "J'accepte d'être proposé·e et sollicité·e par les membres du Club"),
          h("small", {}, "Désactivé : vous disparaissez des recherches et de la Bourse ; les demandes en attente qui vous sont adressées sont annulées ; les mises en relation déjà acceptées restent (vous pouvez les annuler).")))),
    h("section", { class: "bloc", "aria-labelledby": "t-profil-30" },
      h("h2", { id: "t-profil-30" }, "Mettre à jour mon profil en 30 secondes"),
      h("p", { class: "sous" }, "Décrivez votre entreprise comme à un apéro : ce que vous proposez, où vous intervenez, vos langues, ce que vous cherchez. Rien n'est enregistré sans votre validation."),
      h("label", { class: "sr", for: "texte-profil" }, "Description de votre entreprise"),
      saisie,
      h("div", { class: "actions" },
        h("button", { class: "btn primaire", type: "button", id: "btn-proposer-profil", onclick: async (ev) => {
          if (!saisie.value.trim()) { toast("Écrivez quelques phrases sur votre entreprise."); saisie.focus(); return; }
          occupe(ev.target.closest("button"), "Lecture…");
          try {
            const p = await api("/api/profil/analyser", { corps: { texte: saisie.value } });
            transition(() => zoneProposition.replaceChildren(formulaireProposition(m, p)));
            zoneProposition.scrollIntoView({ behavior: "smooth", block: "start" });
          } catch (e) { toast(e.message, "erreur"); }
          finally { libre(ev.target.closest("button")); }
        } }, "Proposer mon profil"),
        h("span", { class: "aide" }, "Lecture par règles locales ; chaque phrase retenue deviendra une preuve citée mot pour mot.")),
      zoneProposition));
}

function formulaireProposition(m, p) {
  const cle = (o) => `${o.concept}|${o.texte}`;
  const offres = [...m.offre.map((o) => ({ ...o, existant: true })), ...p.offre.filter((o) => !m.offre.some((x) => cle(x) === cle(o)))];
  const recherches = [...m.recherche.map((o) => ({ ...o, existant: true })), ...p.recherche.filter((o) => !m.recherche.some((x) => cle(x) === cle(o)))];
  const zones = [...new Set([...m.zones_service, ...p.zones_service])];
  const langues = [...new Set([...m.langues, ...p.langues])];
  const libelle = (o) => (o.libelle || etat.config.concepts.find((c) => c.valeur === o.concept)?.libelle || (o.concept ? o.concept : "Hors catalogue (recherche par mots)"));
  const ligne = (o, groupe) => h("label", { class: "bascule ligne-profil" + (o.existant ? "" : " nouveau") },
    h("input", { type: "checkbox", checked: true, "data-groupe": groupe, "data-concept": o.concept ?? "", "data-texte": o.texte }),
    h("span", {}, h("strong", {}, libelle(o)), h("small", {}, `« ${o.texte} »` + (o.existant ? " · déjà dans votre profil" : " · nouveau"))));
  const form = h("div", { class: "visibilite proposition" },
    h("h3", {}, "Ce que les autres membres verront"),
    offres.length ? h("fieldset", {}, h("legend", {}, "Vous proposez"), offres.map((o) => ligne(o, "offre"))) : null,
    recherches.length ? h("fieldset", {}, h("legend", {}, "Vous cherchez (sert la réciprocité)"), recherches.map((o) => ligne(o, "recherche"))) : null,
    h("fieldset", {}, h("legend", {}, "Vous intervenez en"), etat.config.zones.map((z) =>
      h("label", { class: "bascule" }, h("input", { type: "checkbox", "data-groupe": "zone", value: z, checked: zones.includes(z) }), h("span", {}, z)))),
    h("fieldset", {}, h("legend", {}, "Langues"), etat.config.langues.map((l) =>
      h("label", { class: "bascule" }, h("input", { type: "checkbox", "data-groupe": "langue", value: l.valeur, checked: langues.includes(l.valeur) }), h("span", {}, l.libelle)))),
    p.phrases_ignorees.length ? h("p", { class: "aide" }, "Non retenu (ni offre ni recherche reconnue, ou tournure négative) : " + p.phrases_ignorees.map((x) => `« ${x} »`).join(" · ")) : null,
    h("div", { class: "actions" }, h("button", { class: "btn rouge", type: "button", onclick: async (ev) => {
      const coches = (g) => [...form.querySelectorAll(`input[data-groupe="${g}"]:checked`)];
      const items = (g) => coches(g).map((i) => ({ concept: i.dataset.concept || null, texte: i.dataset.texte }));
      occupe(ev.target.closest("button"), "Enregistrement…");
      try {
        await api("/api/moi/profil", { methode: "PUT", corps: { offre: items("offre"), recherche: items("recherche"),
          zones_service: coches("zone").map((i) => i.value), langues: coches("langue").map((i) => i.value) } });
        toast("Profil enregistré : recherches et Bourse recalculées pour tout le Club.", "info");
        emettre("rafraichir"); vueProfil();
      } catch (e) { toast(e.message, "erreur"); libre(ev.target.closest("button")); }
    } }, "Valider et enregistrer mon profil")));
  return form;
}

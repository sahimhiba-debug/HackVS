// Fenêtre de message (demande d'introduction ou proposition d'aide).
import { $, api, etat, occupe, libre, toast } from "./outils.js";

export async function ouvrirMessage({ titre, consentement, brouillonUrl, libelleEnvoi, envoyer }) {
  const dlg = $("#dialogue");
  $("#dialogue-titre").textContent = titre;
  $("#dialogue-consentement").textContent = consentement + (etat.config.donnees_fictives ? " Démonstration : rien n'est envoyé." : "");
  const zone = $("#message");
  zone.value = "Préparation du message…";
  zone.disabled = true;
  const btn = $("#dialogue-envoyer");
  btn.textContent = libelleEnvoi;
  dlg.showModal();
  try {
    zone.value = (await api(brouillonUrl)).message;
  } catch (e) { zone.value = ""; toast(e.message, "erreur"); }
  zone.disabled = false;
  zone.focus();
  zone.setSelectionRange(0, 0);

  return new Promise((resolve) => {
    const surEnvoi = async (ev) => {
      ev.preventDefault();
      if (!zone.value.trim()) { toast("Le message ne peut pas être vide."); return; }
      occupe(btn, "Envoi…");
      try { await envoyer(zone.value); dlg.close(); resolve(true); }
      catch (e) { toast(e.message, "erreur"); }
      finally { libre(btn); btn.textContent = libelleEnvoi; }
    };
    btn.onclick = surEnvoi;
    dlg.onclose = () => { btn.onclick = null; resolve(false); };
  });
}

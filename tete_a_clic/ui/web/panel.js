/* Tête-à-Clic : logique du panneau. État lu 10 fois par seconde via pywebview.api.state(). */
"use strict";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const api = () => window.pywebview.api;

const P = (d) => `<path d="${d}"/>`;
const C = (x, y, r) => `<circle cx="${x}" cy="${y}" r="${r}"/>`;
const ICONS = {
  logo: C(12, 8, 5) + P("M9.5 7.5h.01M14.5 7.5h.01M10 10.5c1.2.8 2.8.8 4 0M5 21c1-3.5 3.8-6 7-6M15 15l6 6M15 15v4.5M15 15h4.5"),
  face: C(12, 12, 9) + P("M9 10h.01M15 10h.01M9 15c1.7 1.3 4.3 1.3 6 0"),
  pause: '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
  play: P("M7 4l13 8-13 8z"),
  target: C(12, 12, 9) + C(12, 12, 5) + C(12, 12, 1),
  keyboard: '<rect x="2" y="6" width="20" height="12" rx="2"/>' + P("M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"),
  sparkles: P("M12 3l1.9 5.8L20 10.5l-6.1 1.7L12 18l-1.9-5.8L4 10.5l6.1-1.7z"),
  cursor: P("M4 3l7 17 2.5-7.5L21 10z"),
  list: P("M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"),
  camoff: P("M2 2l20 20M7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h12M9.5 4h5L17 7h3a2 2 0 0 1 2 2v7.5"),
};
const icon = (n) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[n] || ""}</svg>`;
function hydrate(root = document) {
  $$("[data-icon]", root).forEach((el) => { if (!el.dataset.ok) { el.insertAdjacentHTML("afterbegin", icon(el.dataset.icon)); el.dataset.ok = 1; } });
}

/* --- Voix ---------------------------------------------------------------- */
const spoken = new Set();
let firstState = true;
function say(text) {
  if (!("speechSynthesis" in window)) return;
  const u = new SpeechSynthesisUtterance(text);
  const fr = speechSynthesis.getVoices().filter((v) => v.lang.startsWith("fr"));
  u.voice = fr.find((v) => /julie|denise|natural/i.test(v.name)) || fr[0] || null;
  u.lang = "fr-FR";
  speechSynthesis.speak(u);
}

/* --- Rendu ----------------------------------------------------------------- */
const STATUS_TONES = { "Actif": "green", "Défilement": "blue", "En pause": "grey", "Recentrage": "orange",
  "Souris physique": "orange", "Visage non détecté": "red", "Caméra indisponible": "red", "Démarrage": "accent" };
let videoSet = false, settingsFilled = false;
const logSeen = new Set();

function render(s) {
  if (!s || !s.status) return;
  const tone = STATUS_TONES[s.status] || "accent";
  $("#status").className = `status tone-${tone}`;
  $("#hero").className = `hero card tone-${tone}`;
  $("#status-text").textContent = s.status;

  // Vidéo, recentrage, erreurs
  if (s.error) {
    $("#video").hidden = true; $("#ph").hidden = false;
    $("#ph-title").textContent = "Caméra indisponible";
    $("#ph-text").textContent = "Une autre application l'utilise peut-être. Ferme-la puis relance Tête-à-Clic.";
    $(".ph-icon").innerHTML = icon("camoff");
  } else if (s.videoUrl && !videoSet) {
    $("#video").src = s.videoUrl; $("#video").hidden = false; $("#ph").hidden = true; videoSet = true;
  }
  const calib = s.calibrating;
  $("#calib").hidden = calib == null;
  if (calib != null) {
    $("#calib-num").textContent = Math.ceil(calib);
    $("#calib-bar").style.strokeDashoffset = 169.6 * (calib / 2);
  }
  $("#fps").textContent = s.fps ? `${s.fps} img/s` : "";

  // Bouton pause
  const btn = $("#btn-pause");
  btn.classList.toggle("paused", s.paused);
  $(".lbl", btn).textContent = s.paused ? "Reprendre" : "Pause";
  const want = s.paused ? "play" : "pause";
  if (btn.dataset.ic !== want) { btn.dataset.ic = want; btn.querySelector("[data-icon]").innerHTML = icon(want); }

  // Jauges des gestes (avec le seuil de déclenchement)
  const meter = (id, value, threshold, enabled) => {
    const el = $(id);
    $(".fill", el).style.width = `${Math.round(Math.min(1, value) * 100)}%`;
    el.classList.toggle("hot", value >= threshold);
    el.classList.toggle("off", !enabled);
  };
  const st = s.settings || {};
  meter("#g-blink", s.signals.blink, 0.5, st.blink_click);
  meter("#g-brow", s.signals.brow, 0.55, st.brow_right_click);
  meter("#g-jaw", s.signals.jaw, 0.45, st.mouth_scroll);

  if (!settingsFilled && s.settings) { fillSettings(s.settings); settingsFilled = true; }

  // Journal
  const log = s.log || [];
  if (log.length) {
    const ul = $("#log");
    if (ul.querySelector(".empty")) ul.innerHTML = "";
    for (const item of [...log].reverse()) {
      if (logSeen.has(item.id)) continue;
      logSeen.add(item.id);
      const li = document.createElement("li");
      li.className = `tone-${item.tone}`;
      li.innerHTML = `<i></i><time>${item.time}</time><span></span>`;
      $("span", li).textContent = item.text;
      ul.prepend(li);
    }
    while (ul.children.length > 6) ul.lastChild.remove();
  }

  // Voix
  for (const sp of s.speech || []) {
    if (spoken.has(sp.id)) continue;
    spoken.add(sp.id);
    if (!firstState) say(sp.text);
  }
  firstState = false;
}

/* --- Réglages ---------------------------------------------------------------- */
function showValue(r) {
  const v = Number(r.value);
  r.nextElementSibling.textContent = r.hasAttribute("data-pct") ? `${Math.round(v * 100)} %` : v.toFixed(1).replace(".", ",") + (r.dataset.unit || "");
  const pct = ((v - r.min) / (r.max - r.min)) * 100;
  r.style.background = `linear-gradient(90deg, var(--accent) ${pct}%, var(--track) ${pct}%)`;
}

function fillSettings(values) {
  $$("[data-setting]").forEach((el) => {
    const v = values[el.dataset.setting];
    if (el.type === "checkbox") el.checked = !!v;
    else if (el.type === "range") { el.value = v; showValue(el); }
  });
}

function wire() {
  $$("[data-action]").forEach((b) => b.addEventListener("click", () => api().action(b.dataset.action)));
  $$("[data-setting]").forEach((el) => {
    const send = () => api().set_setting(el.dataset.setting, el.type === "checkbox" ? el.checked : Number(el.value));
    if (el.type === "range") { el.addEventListener("input", () => showValue(el)); el.addEventListener("change", send); }
    else el.addEventListener("change", send);
  });
}

async function poll() {
  try { render(await api().state()); } catch (e) { /* fermeture */ }
  setTimeout(poll, 100);
}

window.addEventListener("pywebviewready", async () => {
  hydrate();
  wire();
  const a = await api().about();
  $("#about").textContent = `${a.name} ${a.version} · © 2026 ${a.author} · ${a.contact}`;
  poll();
  setTimeout(() => document.body.classList.remove("booting"), 400);
});

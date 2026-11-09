/* Domogotchi card — carte Lovelace de la créature-maison (FR / EN). */
const DOMOGOTCHI_VERSION = "2026.11.6";

const W = 32;
const H = 24;
const SCALE = 5;
const LCD_BG = "#C0DD97";
const LCD_OFF = "#B4D08C";
const LCD_ON = "#173404";

const STAGE_SIZE = {
  cabane: [10, 7],
  maisonnette: [14, 8],
  maison: [18, 9],
  villa: [24, 10],
};

const ACTIONS = [
  { key: "nourrir", letter: "A" },
  { key: "jouer", letter: "B" },
  { key: "nettoyer", letter: "C" },
  { key: "soigner", letter: "D" },
];

const I18N = {
  fr: {
    messages: {
      nourri: "Miam !", trop_mange: "Trop mangé…", joue: "Youpi !", nettoye: "Tout propre",
      soigne: "Ça va mieux", refus_dort: "Chut, il dort", refus_oeuf: "Patience…", refus_mort: "…",
      refus_fatigue: "Trop fatigué", refus_pas_malade: "Pas malade", eclosion: "Éclosion !",
      nouvel_oeuf: "Un nouvel œuf", endormi: "Bonne nuit", reveil: "Bonjour !", malade: "Il est malade", mort: "R.I.P.",
    },
    moods: {
      mort: "Mort", oeuf: "Dans l'œuf", malade: "Malade", endormi: "Endormi", affame: "Affamé", fatigue: "Fatigué",
      froid: "A froid", chaud: "A chaud", sale: "Sale", seul: "Seul", stresse: "Stressé", triste: "Triste",
      content: "Content", heureux: "Heureux",
    },
    stages: { oeuf: "œuf", cabane: "cabane", maisonnette: "maisonnette", maison: "maison", villa: "villa", mort: "ruine" },
    actions: { nourrir: "Nourrir", jouer: "Jouer", nettoyer: "Nettoyer", soigner: "Soigner" },
    gauges: { satiete: "Satiété", bonheur: "Bonheur", energie: "Énergie", sante: "Santé", proprete: "Propreté" },
    ctx: {
      mood: "Humeur :", stage: "stade :", generation: "génération", cold: "il a froid", hot: "il a chaud",
      alone: "personne à la maison", stressed: "consommation élevée", good: "beau temps", bad: "mauvais temps",
    },
    egg: "œuf", hatchIn: (m) => `Éclosion dans ${m} min`, hatchSoon: "Éclosion imminente", hours: "h", days: "j", rip: "R.I.P.",
    reset: "Nouvel œuf", resetConfirm: "Remplacer la créature par un nouvel œuf ?",
    notFound: "Entité introuvable :",
  },
  en: {
    messages: {
      nourri: "Yum!", trop_mange: "Too full…", joue: "Yay!", nettoye: "All clean",
      soigne: "Feeling better", refus_dort: "Shh, sleeping", refus_oeuf: "Patience…", refus_mort: "…",
      refus_fatigue: "Too tired", refus_pas_malade: "Not sick", eclosion: "Hatched!",
      nouvel_oeuf: "A new egg", endormi: "Good night", reveil: "Good morning!", malade: "It is sick", mort: "R.I.P.",
    },
    moods: {
      mort: "Dead", oeuf: "In the egg", malade: "Sick", endormi: "Asleep", affame: "Starving", fatigue: "Tired",
      froid: "Cold", chaud: "Hot", sale: "Dirty", seul: "Lonely", stresse: "Stressed", triste: "Sad",
      content: "Content", heureux: "Happy",
    },
    stages: { oeuf: "egg", cabane: "hut", maisonnette: "cottage", maison: "house", villa: "villa", mort: "ruin" },
    actions: { nourrir: "Feed", jouer: "Play", nettoyer: "Clean", soigner: "Heal" },
    gauges: { satiete: "Satiety", bonheur: "Happiness", energie: "Energy", sante: "Health", proprete: "Cleanliness" },
    ctx: {
      mood: "Mood:", stage: "stage:", generation: "generation", cold: "feeling cold", hot: "feeling hot",
      alone: "nobody home", stressed: "high consumption", good: "nice weather", bad: "bad weather",
    },
    egg: "egg", hatchIn: (m) => `Hatching in ${m} min`, hatchSoon: "Hatching soon", hours: "h", days: "d", rip: "R.I.P.",
    reset: "New egg", resetConfirm: "Replace the creature with a new egg?",
    notFound: "Entity not found:",
  },
};

function pickLang(hass) {
  const lang = (hass && ((hass.locale && hass.locale.language) || hass.language)) || navigator.language || "en";
  return String(lang).toLowerCase().startsWith("fr") ? "fr" : "en";
}

/* ---------- dessin pixel ---------- */
class Grid {
  constructor() {
    this.cells = new Uint8Array(W * H);
  }
  set(x, y) {
    x = Math.round(x);
    y = Math.round(y);
    if (x >= 0 && x < W && y >= 0 && y < H) this.cells[y * W + x] = 1;
  }
  get(x, y) {
    if (x < 0 || x >= W || y < 0 || y >= H) return 0;
    return this.cells[y * W + x];
  }
  line(x0, y0, x1, y1) {
    const dx = Math.abs(x1 - x0);
    const dy = -Math.abs(y1 - y0);
    const sx = x0 < x1 ? 1 : -1;
    const sy = y0 < y1 ? 1 : -1;
    let err = dx + dy;
    for (;;) {
      this.set(x0, y0);
      if (x0 === x1 && y0 === y1) break;
      const e2 = 2 * err;
      if (e2 >= dy) { err += dy; x0 += sx; }
      if (e2 <= dx) { err += dx; y0 += sy; }
    }
  }
  rect(x0, y0, x1, y1) {
    this.line(x0, y0, x1, y0);
    this.line(x0, y1, x1, y1);
    this.line(x0, y0, x0, y1);
    this.line(x1, y0, x1, y1);
  }
  fill(x0, y0, x1, y1) {
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) this.set(x, y);
  }
  pattern(x, y, rows) {
    rows.forEach((r, dy) => [...r].forEach((c, dx) => c === "1" && this.set(x + dx, y + dy)));
  }
}

function drawEgg(g, frame) {
  const wob = frame % 4 === 0 ? -1 : frame % 4 === 2 ? 1 : 0;
  const cx = 16 + wob;
  const cy = 13;
  for (let a = 0; a < 360; a += 4) {
    const r = (a * Math.PI) / 180;
    const ry = Math.sin(r) < 0 ? 7.5 : 6.5;
    g.set(cx + Math.cos(r) * 5.5, cy + Math.sin(r) * ry);
  }
  g.pattern(cx - 3, cy - 1, ["1000101", "0101010"]);
  g.line(10, 21, 22, 21);
}

function drawGrave(g) {
  g.pattern(10, 6, [
    "000111111000",
    "001000000100",
    "010000000010",
    "010001100010",
    "010111111010",
    "010001100010",
    "010001100010",
    "010000000010",
    "010000000010",
    "010000000010",
    "010000000010",
    "010000000010",
    "111111111111",
  ]);
  g.line(4, 19, 27, 19);
  g.pattern(5, 17, ["0101", "1010"]);
  g.pattern(23, 17, ["1010", "0101"]);
}

function drawHouse(g, a, frame) {
  const [bw, bh] = STAGE_SIZE[a.stade] || STAGE_SIZE.cabane;
  const bounce = !a.endormi && !a.malade && frame % 2 === 1 ? -1 : 0;
  const x0 = Math.floor((W - bw) / 2);
  const x1 = x0 + bw - 1;
  const yBottom = 20 + bounce;
  const yTop = yBottom - bh + 1;
  const cx = Math.floor((x0 + x1) / 2);

  // corps
  g.rect(x0, yTop, x1, yBottom);
  // pieds
  g.set(x0 + 2, yBottom + 1);
  g.set(x1 - 2, yBottom + 1);
  if (bounce === 0) { g.set(x0 + 1, yBottom + 1); g.set(x1 - 1, yBottom + 1); }

  // toit
  const eave = yTop - 1;
  const rh = Math.min(Math.floor((bw + 2) / 2), eave - 2);
  const apex = eave - rh;
  g.line(x0 - 1, eave, x1 + 1, eave);
  g.line(x0 - 1, eave, cx, apex);
  g.line(x1 + 1, eave, cx + 1, apex);

  // neige sur le toit quand il a froid
  if (a.froid) {
    for (let x = x0 - 1; x <= x1 + 1; x++) {
      for (let y = 0; y < eave; y++) {
        if (g.get(x, y + 1) && !g.get(x, y)) { if ((x + frame) % 3 !== 0) g.set(x, y); break; }
      }
    }
  }

  // cheminée + fumée
  const chx = x1 - 2;
  let roofY = eave;
  for (let y = 0; y < eave; y++) if (g.get(chx, y)) { roofY = y; break; }
  g.fill(chx, roofY - 3, chx + 1, roofY - 1);
  if (!a.endormi && !a.malade) {
    const s = frame % 3;
    g.set(chx + (s === 1 ? 1 : 0), roofY - 5 - s);
    if (roofY - 7 - s >= 0) g.set(chx + 1 - (s === 1 ? 1 : 0), roofY - 7 - s);
  }

  // fenêtres-yeux (3x3)
  const ey = yTop + 1;
  const exs = [x0 + Math.max(1, Math.floor(bw / 4) - 1), x1 - Math.max(1, Math.floor(bw / 4) - 1) - 2];
  const blink = frame % 9 === 0;
  for (const ex of exs) {
    if (a.malade) {
      g.pattern(ex, ey, ["101", "010", "101"]); // volets croisés
    } else if (a.endormi) {
      g.fill(ex, ey, ex + 2, ey + 2); // fenêtre éteinte
    } else {
      g.rect(ex, ey, ex + 2, ey + 2);
      if (!blink) g.set(ex + 1, ey + 1 + (["affame", "triste", "seul"].includes(a.humeur) ? 1 : 0));
    }
  }

  // bouche
  const my = yTop + 4;
  const mx = cx - 1;
  const happy = a.humeur === "heureux" || frame % 6 === 0 && a.humeur === "content";
  const sad = ["malade", "affame", "triste", "seul", "stresse", "sale", "fatigue", "froid", "chaud"].includes(a.humeur);
  if (a.endormi) g.line(mx + 1, my + 1, mx + 2, my + 1);
  else if (happy) g.pattern(mx, my, ["1001", "0110"]);
  else if (sad) g.pattern(mx, my, ["0110", "1001"]);
  else g.line(mx, my + 1, mx + 3, my + 1);

  // porte
  if (bh >= 9) g.rect(x0 + 1, yBottom - 3, x0 + 3, yBottom);
  // villa : clôture
  if (a.stade === "villa") for (let x = 1; x < x0 - 1; x += 2) g.line(x, yBottom - 1, x, yBottom);

  // il a chaud : gouttes
  if (a.chaud && frame % 2 === 0) { g.set(x0 - 2, yTop + 1); g.set(x0 - 2, yTop + 2); g.set(x1 + 2, yTop + 3); }
  // dodo : Zz
  if (a.endormi) {
    const z = frame % 4 < 2 ? 0 : 1;
    g.pattern(x0 - 4, apex + 1 - z, ["111", "010", "111"]);
    if (z) g.pattern(x0 - 7, apex - 3, ["11", "11"]);
  }
  // saleté : petits tas qui fument
  const dirt = a.proprete < 20 ? 2 : a.proprete < 40 ? 1 : 0;
  const piles = [[x1 + 2, 21], [x0 - 5, 21]];
  for (let i = 0; i < dirt; i++) {
    const [px, py] = piles[i];
    g.pattern(px, py - 2, ["010", "111"]);
    if (frame % 2 === i % 2) g.set(px + 1, py - 4);
  }
  // sol
  g.line(0, 22, W - 1, 22);
}

/* ---------- DOM ---------- */
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

/* ---------- carte ---------- */
class DomogotchiCard extends HTMLElement {
  static getStubConfig(hass) {
    const found = Object.values(hass.states).find(
      (s) => s.entity_id.startsWith("sensor.") && s.attributes && s.attributes.boutons && s.attributes.config_entry_id
    );
    return { entity: found ? found.entity_id : "sensor.domo_humeur" };
  }

  setConfig(config) {
    if (!config || !config.entity) throw new Error("entity: sensor Humeur / Mood");
    this._config = { show_stats: true, ...config };
    this._frame = 0;
    this._lastEventSeen = null;
    this._msgUntil = 0;
    if (this.shadowRoot) this._build();
  }

  set hass(hass) {
    this._hass = hass;
    const lang = pickLang(hass);
    if (lang !== this._lang) { this._lang = lang; this._btnMode = null; }
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this._build();
    }
    this._update();
  }

  getCardSize() {
    return this._config && this._config.show_stats ? 9 : 6;
  }

  connectedCallback() {
    if (!this._timer) this._timer = setInterval(() => { this._frame++; this._draw(); this._renderMessage(); }, 500);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    this._timer = null;
  }

  _build() {
    const root = this.shadowRoot;
    root.innerHTML = `
      <style>
        :host { display:block; }
        ha-card { padding:16px; display:flex; flex-direction:column; align-items:center; gap:14px; }
        .house { width:250px; display:flex; flex-direction:column; align-items:center; }
        .roof { position:relative; width:250px; height:72px; }
        .roof svg { position:absolute; inset:0; }
        .chim { position:absolute; right:46px; top:8px; width:22px; height:40px;
          background:var(--secondary-background-color); border:1px solid var(--divider-color); }
        .brand { position:absolute; left:0; right:0; top:46px; text-align:center; font-size:12px;
          letter-spacing:2px; color:var(--secondary-text-color); text-transform:lowercase; }
        .body { width:226px; box-sizing:border-box; background:var(--secondary-background-color);
          border:1px solid var(--divider-color); border-top:none; border-radius:0 0 16px 16px;
          padding:12px 16px 16px; display:flex; flex-direction:column; align-items:center; gap:10px; }
        .lcd { background:${LCD_BG}; border:3px solid #444441; border-radius:8px; padding:8px; color:${LCD_ON}; }
        .icons { display:flex; justify-content:space-between; }
        .icons ha-icon { --mdc-icon-size:16px; opacity:.18; transition:opacity .2s; }
        .icons ha-icon.on { opacity:1; }
        canvas { display:block; image-rendering:pixelated; margin:4px 0; }
        .msg { text-align:center; font-family:monospace; font-size:13px; height:18px; overflow:hidden; white-space:nowrap; }
        .btns { display:flex; gap:10px; }
        .btn { display:flex; flex-direction:column; align-items:center; gap:4px; }
        button { width:42px; height:42px; border-radius:50%; border:1px solid var(--divider-color);
          background:var(--card-background-color); color:var(--primary-text-color); font-weight:500; cursor:pointer; }
        button:active { transform:scale(.94); }
        .btn span { font-size:11px; color:var(--secondary-text-color); }
        .reset { width:auto; height:auto; border-radius:18px; padding:8px 16px; }
        .stats { width:100%; max-width:300px; }
        .row { display:flex; justify-content:space-between; font-size:13px; color:var(--secondary-text-color); margin:6px 0 3px; }
        .bar { height:8px; border-radius:4px; background:var(--divider-color); overflow:hidden; }
        .bar div { height:100%; background:var(--primary-color); transition:width .4s; }
        .bar div.low { background:var(--error-color, #db4437); }
        .ctx { font-size:12px; color:var(--secondary-text-color); margin-top:10px; line-height:1.5; }
        .err { color:var(--error-color); font-size:14px; }
      </style>
      <ha-card>
        <div class="house">
          <div class="roof">
            <div class="chim"></div>
            <svg viewBox="0 0 250 72" width="250" height="72">
              <polygon points="125,4 248,72 2,72" fill="var(--secondary-background-color)" stroke="var(--divider-color)" stroke-width="1"/>
            </svg>
            <div class="brand">domogotchi</div>
          </div>
          <div class="body">
            <div class="lcd">
              <div class="icons">
                <ha-icon id="i_food" icon="mdi:food-drumstick"></ha-icon>
                <ha-icon id="i_sleep" icon="mdi:lightbulb-off-outline"></ha-icon>
                <ha-icon id="i_temp" icon="mdi:thermometer"></ha-icon>
                <ha-icon id="i_alone" icon="mdi:account-off-outline"></ha-icon>
                <ha-icon id="i_power" icon="mdi:flash"></ha-icon>
                <ha-icon id="i_sick" icon="mdi:medical-bag"></ha-icon>
              </div>
              <canvas id="screen" width="${W * SCALE}" height="${H * SCALE}"></canvas>
              <div class="msg" id="msg"></div>
            </div>
            <div class="btns" id="btns"></div>
          </div>
        </div>
        <div class="stats" id="stats"></div>
      </ha-card>`;
    this._els = {
      canvas: root.getElementById("screen"),
      msg: root.getElementById("msg"),
      btns: root.getElementById("btns"),
      stats: root.getElementById("stats"),
    };
    this._ctx = this._els.canvas.getContext("2d");
    this._btnMode = null;
  }

  get _t() {
    return I18N[this._lang || pickLang(this._hass)];
  }

  get _attrs() {
    const st = this._hass && this._config && this._hass.states[this._config.entity];
    return st ? { ...st.attributes, humeur: st.state } : null;
  }

  _update() {
    if (!this._els) return;
    const a = this._attrs;
    if (!a || !a.boutons) {
      this._els.stats.replaceChildren(el("div", "err", `${this._t.notFound} ${this._config.entity}`));
      return;
    }
    // icônes de statut
    const set = (id, on) => this.shadowRoot.getElementById(id).classList.toggle("on", !!on);
    set("i_food", a.vivant && a.stade !== "oeuf" && a.satiete < 30);
    set("i_sleep", a.endormi);
    set("i_temp", a.froid || a.chaud);
    set("i_alone", a.seul);
    set("i_power", a.stresse);
    set("i_sick", a.malade);

    // nouvel événement → message temporaire
    if (this._lastEventSeen !== null && a.dernier_evenement_le !== this._lastEventSeen) {
      this._msgUntil = Date.now() + 4000;
    }
    this._lastEventSeen = a.dernier_evenement_le;

    this._renderButtons(a);
    this._renderStats(a);
    this._draw();
    this._renderMessage();
  }

  _renderButtons(a) {
    const mode = a.vivant ? "alive" : "dead";
    if (mode === this._btnMode) return;
    this._btnMode = mode;
    const box = this._els.btns;
    box.replaceChildren();
    if (!a.vivant) {
      const b = document.createElement("button");
      b.className = "reset";
      b.textContent = this._t.reset;
      b.addEventListener("click", () => {
        if (confirm(this._t.resetConfirm)) {
          this._hass.callService("domogotchi", "reset", { config_entry_id: this._attrs.config_entry_id });
        }
      });
      box.appendChild(b);
      return;
    }
    for (const act of ACTIONS) {
      const wrap = document.createElement("div");
      wrap.className = "btn";
      const b = document.createElement("button");
      b.textContent = act.letter;
      const label = this._t.actions[act.key];
      b.title = label;
      b.setAttribute("aria-label", label);
      b.addEventListener("click", () => {
        const id = this._attrs && this._attrs.boutons && this._attrs.boutons[act.key];
        if (id) this._hass.callService("button", "press", { entity_id: id });
      });
      const l = document.createElement("span");
      l.textContent = label;
      wrap.append(b, l);
      box.appendChild(wrap);
    }
  }

  _renderStats(a) {
    if (!this._config.show_stats) { this._els.stats.replaceChildren(); return; }
    const t = this._t;
    const ctx = [];
    ctx.push(`${t.ctx.mood} ${t.moods[a.humeur] || a.humeur}`);
    ctx.push(`${t.ctx.stage} ${t.stages[a.stade] || a.stade}`);
    ctx.push(`${t.ctx.generation} ${a.generation}`);
    if (a.froid) ctx.push(t.ctx.cold);
    if (a.chaud) ctx.push(t.ctx.hot);
    if (a.seul) ctx.push(t.ctx.alone);
    if (a.stresse) ctx.push(t.ctx.stressed);
    if (a.beau_temps) ctx.push(t.ctx.good);
    if (a.mauvais_temps) ctx.push(t.ctx.bad);
    // Construit avec le DOM : aucune valeur d'état, d'attribut ou de config ne passe par innerHTML.
    const nodes = [];
    for (const key of ["satiete", "bonheur", "energie", "sante", "proprete"]) {
      const raw = Number(a[key]);
      const v = Number.isFinite(raw) ? Math.max(0, Math.min(100, raw)) : 0;
      const row = el("div", "row");
      row.append(el("span", null, t.gauges[key]), el("span", null, `${Math.round(v)} %`));
      const bar = el("div", "bar");
      const fill = el("div", v < 25 ? "low" : null);
      fill.style.width = `${v}%`;
      bar.appendChild(fill);
      nodes.push(row, bar);
    }
    nodes.push(el("div", "ctx", ctx.join(" · ")));
    this._els.stats.replaceChildren(...nodes);
  }

  _renderMessage() {
    const a = this._attrs;
    if (!a || !this._els) return;
    const t = this._t;
    let text;
    const eggRefusal = a.dernier_evenement === "refus_oeuf" && a.stade === "oeuf";
    if (Date.now() < this._msgUntil && !eggRefusal) text = t.messages[a.dernier_evenement] || "";
    else if (!a.vivant) text = `${t.rip} ${a.nom}`;
    else if (a.stade === "oeuf") {
      const at = Date.parse(a.eclosion_le || "");
      const left = Number.isFinite(at) ? Math.ceil((at - Date.now()) / 60000) : NaN;
      text = Number.isFinite(left) ? (left >= 1 ? t.hatchIn(left) : t.hatchSoon) : `${a.nom} · ${t.egg}`;
    }
    else {
      const h = a.age_heures || 0;
      text = `${a.nom} · ${h < 24 ? Math.floor(h) + " " + t.hours : Math.floor(h / 24) + " " + t.days}`;
    }
    if (this._els.msg.textContent !== text) this._els.msg.textContent = text;
  }

  _draw() {
    const a = this._attrs;
    if (!a || !this._ctx) return;
    const g = new Grid();
    if (!a.vivant) drawGrave(g);
    else if (a.stade === "oeuf") drawEgg(g, this._frame);
    else drawHouse(g, a, this._frame);
    const c = this._ctx;
    c.fillStyle = LCD_BG;
    c.fillRect(0, 0, W * SCALE, H * SCALE);
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        c.fillStyle = g.get(x, y) ? LCD_ON : LCD_OFF;
        c.fillRect(x * SCALE, y * SCALE, SCALE - 1, SCALE - 1);
      }
    }
  }
}

if (!customElements.get("domogotchi-card")) {
  customElements.define("domogotchi-card", DomogotchiCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "domogotchi-card",
    name: "Domogotchi",
    description: pickLang(null) === "fr" ? "Ta créature-maison sur écran LCD rétro." : "Your house creature on a retro LCD screen.",
    preview: true,
  });
  console.info(`%c DOMOGOTCHI %c ${DOMOGOTCHI_VERSION} `, "background:#173404;color:#C0DD97", "background:#C0DD97;color:#173404");
}

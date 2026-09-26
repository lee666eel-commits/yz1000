"""Emit a self-contained handwriting-capture page for a stylus/touch device.

Pairing is structural here: the page names the character, and the strokes are
stored under that codepoint. No slicing, no registration marks, no thresholds --
none of the photo-recovery machinery applies.

Usage:
    python make_spen_page.py --out D:\\handwriting-font\\spen
    python make_spen_page.py --out ... --chars-file chars.txt --count 1000
"""

import argparse
import hashlib
import json
import os

from make_template import PILOT_CHARS, build_charset

# Nib presets. `ratio` is the short axis as a fraction of the long one: 1.0 is a
# round tip (every direction the same width), lower is more directional. `press`
# is the pressure curve, width = base * (press[0] + press[1] * p) -- a fountain
# nib barely flexes, a pencil varies a lot. build_font_strokes.py reads the
# values back out of the capture, so a page and its .ttf can never disagree.
PENS = {
    "fountain":  {"angle": -40.0, "ratio": 0.55, "press": (0.80, 0.50)},
    "ballpoint": {"angle": 0.0,   "ratio": 1.00, "press": (0.90, 0.20)},
    "pencil":    {"angle": 0.0,   "ratio": 1.00, "press": (0.50, 1.00)},
    "round":     {"angle": 0.0,   "ratio": 1.00, "press": (0.55, 0.90)},
}

PAGE = r"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>__TITLE__</title>
<style>
  :root {
    --bg:#f4f2ee; --fg:#1b1b1b; --dim:#8a8578; --line:#d8d4ca;
    --accent:#2f6f4f; --warn:#a4442c; --card:#fffdf8;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#17181a; --fg:#eceae4; --dim:#8b8880; --line:#33353a;
            --accent:#6fd3a0; --warn:#e08b6f; --card:#1f2124; }
  }
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  html,body { margin:0; height:100%; background:var(--bg); color:var(--fg);
    font-family:-apple-system,"Segoe UI","Noto Sans CJK SC","Microsoft YaHei",sans-serif;
    overscroll-behavior:none; }
  body { display:flex; flex-direction:column; gap:.5rem; padding:.6rem; }
  header { display:flex; align-items:center; gap:.7rem; flex:0 0 auto; }
  #prog { font-variant-numeric:tabular-nums; font-size:.95rem; color:var(--dim); }
  #prog b { color:var(--fg); font-size:1.15rem; }
  #target { font-size:.85rem; color:var(--dim); margin-left:auto;
    max-width:60%; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
  #wrap { flex:1 1 auto; display:flex; align-items:center; justify-content:center;
    min-height:0; overflow:auto; }
  /* 横书: labels ABOVE the cells they name. 直书: labels down the left. Getting
     this wrong puts the whole label row beside the grid, and the writer cannot
     tell which cell is which character -- which is exactly what happened. */
  #strip { display:flex; gap:.1rem; align-items:flex-start;
    flex-direction:column; }
  #strip.v { flex-direction:row; }
  #labels { display:flex; gap:0; color:var(--dim); font-size:1rem;
    font-family:-apple-system,"Segoe UI",sans-serif; }
  #labels.v { flex-direction:column; }
  #labels span { display:flex; align-items:flex-end; justify-content:center;
    width:var(--cell,150px); height:1.35rem; flex:0 0 auto; }
  #labels.v span { width:1.5rem; height:var(--cell,150px);
    align-items:center; justify-content:flex-end; }
  #labels span.done { color:var(--accent); }
  #labels span.cur { color:var(--fg); font-weight:700; }
  /* No border on the canvas. `* { box-sizing:border-box }` makes a 1px border
     eat 1px of the drawing surface, so pointer coordinates (measured on the
     outer box) and ink (drawn on the content box) drift apart by a pixel-ish
     across every cell. The cell frames are drawn inside the bitmap instead. */
  canvas { background:var(--card); border-radius:.4rem;
    touch-action:none; display:block; }
  /* The box used to fill the screen. At that size you write with your arm, not
     your hand, and you fill every cell edge to edge -- so every glyph comes out
     the same monumental size and the size variation real handwriting has is
     gone before the pipeline ever sees it. Keep the box hand-sized. */
  #sizebar { display:flex; align-items:center; gap:.5rem; flex:0 0 auto;
    font-size:.75rem; color:var(--dim); }
  #sizebar input { flex:1; }
  /* Buttons live at the very bottom, away from where the hand rests. Palm
     rejection only covers the canvas -- a palm landing on an HTML button is
     just a click, and the tablet only locks out touch AFTER it has seen the
     pen, so the dangerous window is before the first pen contact. */
  nav { display:grid; grid-template-columns:repeat(6,1fr); gap:.4rem;
    flex:0 0 auto; margin-top:auto; padding-top:.6rem; }
  button { font:inherit; font-size:.9rem; padding:.75rem .2rem; border-radius:.4rem;
    border:1px solid var(--line); background:var(--card); color:var(--fg); }
  button:active { background:var(--line); }
  button.p { border-color:var(--accent); color:var(--accent); font-weight:600; }
  #foot { display:flex; gap:.5rem; align-items:center; flex:0 0 auto;
    font-size:.8rem; color:var(--dim); }
  #foot button { padding:.5rem .7rem; font-size:.8rem; }
  #msg { flex:1; }
  #msg.err { color:var(--warn); }
  #grid { display:none; grid-template-columns:repeat(auto-fill,minmax(2.1rem,1fr));
    gap:.25rem; max-height:34vh; overflow:auto; flex:0 0 auto;
    border-top:1px solid var(--line); padding-top:.5rem; }
  #grid.on { display:grid; }
  #grid span { text-align:center; padding:.35rem 0; border-radius:.25rem;
    border:1px solid var(--line); font-family:"KaiTi","Kaiti SC",serif;
    color:var(--dim); }
  #grid span.done { color:var(--fg); border-color:var(--accent);
    background:color-mix(in srgb, var(--accent) 12%, transparent); }
  #grid span.cur { outline:2px solid var(--accent); }
  #out { display:none; width:100%; height:22vh; font-size:.65rem; }
</style>

<header>
  <div id="prog"><b>0</b> / 0 已写</div>
  <div id="target">-</div>
</header>

<div id="wrap">
  <div id="strip">
    <div id="labels"></div>
    <canvas id="cv"></canvas>
  </div>
</div>

<div id="sizebar">
  <span>格子</span>
  <input id="size" type="range" min="70" max="560" step="5">
  <span id="sizev">-</span>
</div>

<div id="foot">
  <button id="tog">字表</button>
  <span id="msg">用触控笔写，格子上方那行小字就是要写的字。每写完一笔就自动存，关掉重开不会丢。</span>
</div>
<div id="grid"></div>
<textarea id="out" readonly></textarea>

<nav>
  <button id="prev">◀ 上行</button>
  <button id="undo">撤一笔</button>
  <button id="clr">清这字</button>
  <button id="dir">直书</button>
  <button id="next" class="p">下行 ▶</button>
  <button id="save" class="p">交出</button>
</nav>

<script>
const CHARS = __CHARS__;
const SET_ID = "__SET_ID__";
const BASE_W = __BASE_W__;          // stroke width, in the 0..1000 logical box
const KEY = "spen:" + SET_ID;
const CELL_KEY = "spen:cell";       // per-device, deliberately not per-charset
const U = 1000;                     // logical canvas box

// --- writing-box size -------------------------------------------------------
// Screen-filling boxes are what made the first real capture unusable: at arm
// scale you fill every cell, so all 100 glyphs come out the same size and the
// ink under the tip is millimetres thick. Tablets differ, so this is a knob the
// writer sets by eye once per device, not a constant.
const pxPerMm = (() => {
  const d = document.createElement("div");
  d.style.cssText = "width:100mm;position:absolute;visibility:hidden";
  document.body.appendChild(d);
  const v = d.getBoundingClientRect().width / 100;
  d.remove();
  return v > 0 ? v : 3.78;
})();

function cellPx() {
  return parseFloat(getComputedStyle(document.documentElement)
                    .getPropertyValue("--cell")) || 150;
}
function setCell(px, save) {
  px = Math.max(70, Math.min(560, Math.round(px)));
  document.documentElement.style.setProperty("--cell", px + "px");
  const sv = document.getElementById("sizev");
  if (sv) sv.textContent = px + "px ≈ " + Math.round(px / pxPerMm) + "mm";
  if (save) { try { localStorage.setItem(CELL_KEY, String(px)); } catch (e) {} }
  fit();
}

function initCell() {
  let px = parseInt(localStorage.getItem(CELL_KEY) || "", 10);
  // 18mm matches the paper route's cell, so BASE_W lands near a 0.8mm nib
  if (!px) px = Math.round(18 * pxPerMm);
  const s = document.getElementById("size");
  s.value = String(Math.max(70, Math.min(560, px)));
  s.addEventListener("input", () => setCell(+s.value, true));
  setCell(+s.value, false);
}

const cv = document.getElementById("cv"), ctx = cv.getContext("2d");
let store = load(), idx = firstUndone(), sawPen = false, drawing = null;
let vertical = localStorage.getItem("spen:vertical") === "1";
let drawCell = 0, lastCh = null;

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  return {};
}
function persist() {
  try { localStorage.setItem(KEY, JSON.stringify(store)); }
  catch (e) { say("存不进 localStorage：" + e.message, true); }
}
function firstUndone() {
  for (let i = 0; i < CHARS.length; i++) if (!store[CHARS[i]]) return i;
  return 0;
}

// --- the line being written --------------------------------------------------
// One character per page made every glyph an isolated exercise. Writing a whole
// line at once is what produces 行气 -- the rhythm, the size drift, the way one
// character leans into the next. Pairing stays structural anyway: a stroke
// belongs to the cell it STARTS in, so nothing is inferred from the ink.
const PER = __PER__;
function lineStart() { return Math.floor(idx / PER) * PER; }
function lineChars() { return CHARS.slice(lineStart(), lineStart() + PER); }
function cellOf(x, y) {                  // strip coords -> cell index in line
  const t = vertical ? y : x;
  return Math.max(0, Math.min(lineChars().length - 1, Math.floor(t / U)));
}
function cellOrigin(i) { return vertical ? [0, i * U] : [i * U, 0]; }
function say(t, err) {
  const m = document.getElementById("msg");
  m.textContent = t; m.className = err ? "err" : "";
}

// --- canvas sizing: back the element with a device-pixel bitmap, then work in
// --- 0..1000 units PER CELL, so nothing depends on screen density.
function stripSize() {                   // [across, along] in logical units
  return [U, U * lineChars().length];
}
function fit() {
  const cell = parseFloat(getComputedStyle(document.documentElement)
                          .getPropertyValue("--cell")) || 150;
  const n = lineChars().length;
  const dpr = window.devicePixelRatio || 1;
  const wpx = vertical ? cell : cell * n;
  const hpx = vertical ? cell * n : cell;
  cv.style.width = wpx + "px"; cv.style.height = hpx + "px";
  cv.width = Math.round(wpx * dpr); cv.height = Math.round(hpx * dpr);
  redraw();
}
function toLogical(e) {
  const r = cv.getBoundingClientRect();
  const cell = r.width / (vertical ? 1 : lineChars().length);
  return [(e.clientX - r.left) / cell * U, (e.clientY - r.top) / cell * U];
}

function redraw() {
  // bitmap pixels per logical unit: one cell spans U units, and the bitmap
  // holds (cells across) of them
  const across = vertical ? 1 : lineChars().length;
  const k = (cv.width / across) / U;
  ctx.setTransform(k, 0, 0, k, 0, 0);
  ctx.clearRect(0, 0, U * 40, U * 40);

  // NO guide glyph. Tracing a printed KaiTi outline produces KaiTi, not his
  // hand -- the character to write is named in the label row instead.
  const line = lineChars();
  for (let i = 0; i < line.length; i++) {
    const [ox, oy] = cellOrigin(i);
    ctx.strokeStyle = getComputedStyle(document.body).getPropertyValue("--line");
    ctx.lineWidth = 2;
    ctx.strokeRect(ox + 1, oy + 1, U - 2, U - 2);
    ctx.globalAlpha = .5;
    ctx.beginPath();
    ctx.moveTo(ox + U / 2, oy); ctx.lineTo(ox + U / 2, oy + U);
    ctx.moveTo(ox, oy + U / 2); ctx.lineTo(ox + U, oy + U / 2);
    ctx.stroke();
    ctx.globalAlpha = 1;
    const g = store[line[i]];
    if (g && (g.slot === undefined || g.slot === lineStart() + i))
      for (const s of g.strokes) inkStroke(s, ox, oy);
  }
  if (drawing) {
    const [ox, oy] = cellOrigin(drawCell);
    inkStroke(drawing, ox, oy);
  }
}

// --- nib ---------------------------------------------------------------------
// A round cap cannot make a 钢笔 stroke: the whole character of a nib is that
// width depends on the DIRECTION of travel. The nib is an ellipse, long axis
// NIB_ANGLE, short axis NIB_RATIO of it; sweeping it gives thin 撇 and full
// 捺 out of the same pressure. build_font_strokes.py implements this same
// formula -- change one and you must change the other, or the .ttf stops
// matching what he saw on the glass.
const NIB_ANGLE = __NIB_ANGLE__ * Math.PI / 180;
const NIB_RATIO = __NIB_RATIO__;
const E1 = [Math.cos(NIB_ANGLE), Math.sin(NIB_ANGLE)];
const E2 = [-E1[1], E1[0]];
const PRESS = [__PRESS_A__, __PRESS_B__];   // named so the parity test can read it
function nibLen(p) { return BASE_W * (PRESS[0] + PRESS[1] * p); }
function halfWidth(p, nx, ny) {          // support radius along unit normal n
  const a = nibLen(p) / 2, b = a * NIB_RATIO;
  const u = a * (nx * E1[0] + ny * E1[1]), v = b * (nx * E2[0] + ny * E2[1]);
  return Math.sqrt(u * u + v * v);
}
function nibBlob(pt, ox, oy) {
  const a = nibLen(pt[2]) / 2;
  ctx.beginPath();
  ctx.ellipse(pt[0] + ox, pt[1] + oy, a, a * NIB_RATIO, NIB_ANGLE, 0, 6.2832);
  ctx.fill();
}
function inkStroke(pts, ox, oy) {
  ctx.fillStyle = getComputedStyle(document.body).getPropertyValue("--fg");
  if (pts.length === 1) { nibBlob(pts[0], ox, oy); return; }
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i];
    let dx = b[0] - a[0], dy = b[1] - a[1];
    const len = Math.hypot(dx, dy) || 1;
    const nx = -dy / len, ny = dx / len;          // unit normal to travel
    const ha = halfWidth(a[2], nx, ny), hb = halfWidth(b[2], nx, ny);
    ctx.beginPath();
    ctx.moveTo(a[0] + nx * ha + ox, a[1] + ny * ha + oy);
    ctx.lineTo(b[0] + nx * hb + ox, b[1] + ny * hb + oy);
    ctx.lineTo(b[0] - nx * hb + ox, b[1] - ny * hb + oy);
    ctx.lineTo(a[0] - nx * ha + ox, a[1] - ny * ha + oy);
    ctx.closePath(); ctx.fill();
  }
  for (const p of pts) nibBlob(p, ox, oy);      // joins, and the angled ends
}

function pressure(e) {
  // Chrome reports 0.5 for devices with no real pressure, and 0 for some
  // synthetic events; treat both as "no signal" rather than "no ink".
  if (e.pointerType === "pen" && e.pressure > 0 && e.pressure !== 0.5) return e.pressure;
  return 0.5;
}

cv.addEventListener("pointerdown", e => {
  if (e.pointerType === "pen") sawPen = true;
  if (sawPen && e.pointerType !== "pen") return;   // palm rejection
  // capture keeps a stroke alive if the pen strays off the canvas mid-stroke;
  // it throws for pointers the browser does not consider active, and losing
  // capture is far better than losing the stroke
  try { cv.setPointerCapture(e.pointerId); } catch (err) {}
  const [x, y] = toLogical(e);
  // the stroke belongs to the cell it STARTS in; a 连笔 tail that runs into the
  // next cell stays with the character it came from, and nothing is guessed
  drawCell = cellOf(x, y);
  // A sentence repeats characters. Strokes are keyed by character, so writing
  // 一 in a second slot would APPEND to the 一 already written elsewhere and
  // produce two overlapping glyphs in one cell. Starting a fresh slot replaces.
  const tgt = lineChars()[drawCell], slot = lineStart() + drawCell;
  if (store[tgt] && store[tgt].slot !== undefined && store[tgt].slot !== slot) {
    delete store[tgt];
    say("「" + tgt + "」这行出现两次，改用这一格重写的。");
  }
  const [ox, oy] = cellOrigin(drawCell);
  drawing = [[r1(x - ox), r1(y - oy), r2(pressure(e))]];
  redraw();
});
cv.addEventListener("pointermove", e => {
  if (!drawing) return;
  if (sawPen && e.pointerType !== "pen") return;
  const evs = e.getCoalescedEvents ? e.getCoalescedEvents() : [e];
  const [ox, oy] = cellOrigin(drawCell);
  for (const ev of (evs.length ? evs : [e])) {
    const [gx, gy] = toLogical(ev);
    const x = gx - ox, y = gy - oy;
    const last = drawing[drawing.length - 1];
    if (Math.abs(x - last[0]) + Math.abs(y - last[1]) < 1.5) continue;
    drawing.push([r1(x), r1(y), r2(pressure(ev))]);
  }
  redraw();
});
function endStroke() {
  if (!drawing) return;
  const ch = lineChars()[drawCell];
  if (!store[ch]) store[ch] = { cp: ch.codePointAt(0), strokes: [], pen: sawPen };
  store[ch].pen = sawPen;
  store[ch].slot = lineStart() + drawCell;   // which occurrence this ink is
  store[ch].strokes.push(drawing);
  lastCh = ch; idx = lineStart() + drawCell;
  drawing = null;
  persist(); refresh();
}
cv.addEventListener("pointerup", endStroke);
cv.addEventListener("pointercancel", endStroke);
cv.addEventListener("pointerleave", endStroke);

const r1 = v => Math.round(v * 10) / 10;
const r2 = v => Math.round(v * 100) / 100;

// --- palm rejection for the buttons -----------------------------------------
// The canvas ignores touch once a pen has been seen, but HTML controls have no
// such thing: a palm landing on 交出 is an ordinary click. And the tablet only
// locks out touch AFTER it has registered the pen, so the exposed window is
// before the first pen contact -- exactly when the hand comes down. Contact
// size is the signal available: a fingertip reports a few millimetres, a palm
// far more.
const PALM_PX = 28;          // raise it if a real fingertip ever gets rejected
let blockClicksUntil = 0;
for (const zone of document.querySelectorAll("nav, #foot, #sizebar")) {
  zone.addEventListener("pointerdown", e => {
    if (e.pointerType === "touch" && (e.width > PALM_PX || e.height > PALM_PX)) {
      blockClicksUntil = Date.now() + 700;
      e.preventDefault(); e.stopPropagation();
      say("挡掉一次手掌误触（接触面 " + Math.round(Math.max(e.width, e.height)) + "px）。");
    }
  }, true);
  zone.addEventListener("click", e => {
    if (Date.now() < blockClicksUntil) { e.preventDefault(); e.stopPropagation(); }
  }, true);
}

function go(n) {
  idx = (n + CHARS.length) % CHARS.length;
  drawing = null; lastCh = null; fit(); refresh();
}
document.getElementById("prev").onclick = () => go(lineStart() - PER);
document.getElementById("next").onclick = () => go(lineStart() + PER);
document.getElementById("dir").onclick = () => {
  // 直书 and 横书 are not the same hand: the wrist travels differently and the
  // strokes come out at different angles, so this is captured, not cosmetic
  vertical = !vertical;
  localStorage.setItem("spen:vertical", vertical ? "1" : "0");
  fit(); refresh();
};
document.getElementById("undo").onclick = () => {
  const ch = lastCh || lineChars()[drawCell];
  const g = store[ch];
  if (!g || !g.strokes.length) return;
  g.strokes.pop();
  if (!g.strokes.length) delete store[ch];
  persist(); refresh();
};
document.getElementById("clr").onclick = () => {
  const ch = lastCh || lineChars()[drawCell];
  delete store[ch]; persist(); refresh();
};
document.getElementById("tog").onclick = () => {
  document.getElementById("grid").classList.toggle("on");
};

function refresh() {
  const done = CHARS.filter(c => store[c] && store[c].strokes.length).length;
  document.getElementById("prog").innerHTML =
    "<b>" + done + "</b> / " + CHARS.length + " 已写";
  const line = lineChars();
  document.getElementById("target").textContent = line.join("");
  document.getElementById("dir").textContent = vertical ? "横书" : "直书";
  document.getElementById("strip").className = vertical ? "v" : "";
  const lab = document.getElementById("labels");
  lab.className = vertical ? "v" : "";
  lab.innerHTML = "";
  line.forEach((c, i) => {
    const s = document.createElement("span");
    s.textContent = c;
    // mark the slot that actually holds the ink, not every slot showing that
    // character -- a repeated 一 must not look already-written
    const g = store[c];
    if (g && g.strokes.length && g.slot === lineStart() + i) s.className = "done";
    lab.appendChild(s);
  });
  const g = document.getElementById("grid");
  g.innerHTML = "";
  CHARS.forEach((c, i) => {
    const s = document.createElement("span");
    s.textContent = c;
    if (store[c] && store[c].strokes.length) s.className = "done";
    if (i === idx) s.className += " cur";
    s.onclick = () => go(i);
    g.appendChild(s);
  });
  redraw();
}

document.getElementById("save").onclick = async () => {
  const glyphs = {};
  for (const c of CHARS) {
    const g = store[c];
    if (g && g.strokes.length) glyphs[g.cp] = { char: c, pen: !!g.pen, strokes: g.strokes };
  }
  const n = Object.keys(glyphs).length;
  if (!n) { say("还没写任何字。", true); return; }
  const data = JSON.stringify({
    version: 2, set_id: SET_ID, box: U, base_width: BASE_W,
    // the physical size the writer actually wrote at; the first capture failed
    // on exactly this and nothing in the file recorded it
    cell_px: cellPx(), cell_mm: Math.round(cellPx() / pxPerMm),
    vertical: vertical, per_line: PER,
    // the build must rasterise with the same nib it was written with
    pen_model: { type: "__PEN__", nib_angle_deg: __NIB_ANGLE__,
                 nib_ratio: __NIB_RATIO__, press: [__PRESS_A__, __PRESS_B__] },
    created: new Date().toISOString(), glyphs: glyphs
  });
  const name = "strokes-" + SET_ID + ".json";

  if (location.protocol === "http:" || location.protocol === "https:") {
    try {
      const res = await fetch("/save?name=" + encodeURIComponent(name),
                              { method: "POST", body: data });
      const txt = await res.text();
      if (res.ok) { say("已送到电脑：" + txt + "（" + n + " 字）"); return; }
      say("上传被拒：" + txt + "。改用下载。", true);
    } catch (err) { say("连不上电脑：" + err.message + "。改用下载。", true); }
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([data], { type: "application/json" }));
  a.download = name; a.click();
  const out = document.getElementById("out");
  out.value = data; out.style.display = "block";
  say("已下载 " + name + "（" + n + " 字）。下载失败就长按上面文字全选复制。");
};

window.addEventListener("resize", fit);
initCell(); refresh();
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--chars-file")
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--manifest",
                    help="take the character list (and order) from a paper "
                         "manifest.json, so both routes cover the same set")
    ap.add_argument("--base-width", type=float, default=45.0,
                    help="stroke width in units of a 1000-wide em. 45 matches a "
                         "0.8mm pen in the paper route's 17.8mm cell, so both "
                         "routes yield comparable weight. The value is baked "
                         "into the page and carried in its output, so the .ttf "
                         "gets exactly the weight you saw while writing.")
    ap.add_argument("--title", default="手写采集")
    ap.add_argument("--text", help="write this text instead of a bare character "
                                   "list, so whole sentences are written in one "
                                   "line and the hand keeps its rhythm. Repeats "
                                   "are allowed; the last one written wins.")
    ap.add_argument("--per-line", type=int, default=10,
                    help="cells shown per page")
    ap.add_argument("--pen", choices=sorted(PENS), default="fountain")
    ap.add_argument("--nib-angle", type=float,
                    help="override the preset nib angle, degrees")
    ap.add_argument("--nib-ratio", type=float,
                    help="override the preset nib ratio (1.0 = round tip)")
    args = ap.parse_args()

    if args.text:
        chars = [c for c in args.text if not c.isspace()]
    elif args.manifest:
        with open(args.manifest, encoding="utf-8") as f:
            man = json.load(f)
        chars = [c["char"] for s in man["sheets"] for c in s["cells"]]
    elif args.chars_file:
        with open(args.chars_file, encoding="utf-8") as f:
            chars = build_charset(f.read(), args.count)
    else:
        chars = build_charset(PILOT_CHARS, args.count)

    nib = dict(PENS[args.pen])
    if args.nib_angle is not None:
        nib["angle"] = args.nib_angle
    if args.nib_ratio is not None:
        nib["ratio"] = args.nib_ratio

    set_id = hashlib.sha1("".join(chars).encode("utf-8")).hexdigest()[:8]
    html = (PAGE
            .replace("__CHARS__", json.dumps(chars, ensure_ascii=False))
            .replace("__SET_ID__", set_id)
            .replace("__BASE_W__", repr(args.base_width))
            .replace("__PER__", str(max(1, args.per_line)))
            .replace("__PEN__", args.pen)
            .replace("__NIB_ANGLE__", repr(nib["angle"]))
            .replace("__NIB_RATIO__", repr(nib["ratio"]))
            .replace("__PRESS_A__", repr(nib["press"][0]))
            .replace("__PRESS_B__", repr(nib["press"][1]))
            .replace("__TITLE__", args.title))

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "writer.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{path}")
    print(f"chars={len(chars)}  set_id={set_id}  base_width={args.base_width}")
    print(f"localStorage key = spen:{set_id}  "
          f"(changing the character list changes this, so old work is kept "
          f"separate rather than silently mismatched)")


if __name__ == "__main__":
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        # Windows consoles and piped stdout default to cp1252, which
        # raises UnicodeEncodeError the moment a CJK character is printed.
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()

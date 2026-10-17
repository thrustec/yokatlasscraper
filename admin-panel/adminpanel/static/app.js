/* ÜniRota admin paneli arayüzü. Derleme adımı yok; tek dosya, saf JavaScript. */
"use strict";

/* ------------------------------------------------------------------ yardımcılar */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const nf = new Intl.NumberFormat("tr-TR");
const num = (n) => (n == null ? "–" : nf.format(n));
const AYLAR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];
const pad = (n) => String(n).padStart(2, "0");

function fmtDate(iso, withSec) {
  if (!iso) return "–";
  const d = new Date(iso), now = new Date();
  const t = `${pad(d.getHours())}:${pad(d.getMinutes())}${withSec ? ":" + pad(d.getSeconds()) : ""}`;
  const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diff = Math.round((day - today) / 86400000);
  if (diff === 0) return `bugün ${t}`;
  if (diff === -1) return `dün ${t}`;
  if (diff === 1) return `yarın ${t}`;
  return `${d.getDate()} ${AYLAR[d.getMonth()]}${d.getFullYear() !== now.getFullYear() ? " " + d.getFullYear() : ""} ${t}`;
}
function rel(iso) {
  if (!iso) return "–";
  const s = Math.round((new Date(iso) - Date.now()) / 1000), a = Math.abs(s);
  let txt;
  if (a < 10) return "az önce";
  if (a < 60) txt = `${a} sn`;
  else if (a < 3600) txt = `${Math.round(a / 60)} dk`;
  else if (a < 86400 * 2) txt = `${Math.round(a / 3600)} sa`;
  else txt = `${Math.round(a / 86400)} gün`;
  return s < 0 ? `${txt} önce` : `${txt} sonra`;
}
function dur(sec) {
  if (sec == null) return "–";
  sec = Math.max(0, Math.round(sec));
  if (sec < 60) return `${sec} sn`;
  const m = Math.floor(sec / 60), s = sec % 60;
  if (m < 60) return s ? `${m} dk ${s} sn` : `${m} dk`;
  const h = Math.floor(m / 60);
  return `${h} sa ${m % 60} dk`;
}
const gb = (b) => (b == null ? "–" : (b / 1024 ** 3).toLocaleString("tr-TR", { maximumFractionDigits: 1 }) + " GB");
const mb = (b) => (b == null ? "–" : b > 1024 ** 3 ? gb(b) : Math.round(b / 1024 ** 2).toLocaleString("tr-TR") + " MB");
const initials = (name) => (name || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toLocaleUpperCase("tr")).join("");
const slugify = (s) => s.toLocaleLowerCase("tr").replace(/ı/g, "i").replace(/ğ/g, "g").replace(/ü/g, "u").replace(/ş/g, "s")
  .replace(/ö/g, "o").replace(/ç/g, "c").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40);

const STATE = { running: "Çalışıyor", queued: "Sırada", idle: "Hazır", error: "Hata verdi", off: "Kapalı" };
const RUN = { running: "Çalışıyor", queued: "Sırada", succeeded: "Başarılı", failed: "Hata", stopped: "Durduruldu", timed_out: "Zaman aşımı" };
const TRIG = { manual: "Elle", schedule: "Zamanlayıcı", retry: "Yeniden deneme" };
const CHECK = { pass: "Geçti", warn: "Uyarı", fail: "Kaldı" };
const pill = (cls, txt) => `<span class="pill s-${esc(cls)}">${esc(txt)}</span>`;

const PRESETS = [
  ["", "Sadece elle"],
  ["0 3 * * *", "Her gece 03:00"],
  ["30 3 * * *", "Her gece 03:30"],
  ["0 */6 * * *", "6 saatte bir"],
  ["0 * * * *", "Saatte bir"],
  ["0 3 * * 1", "Haftada bir (Pazartesi 03:00)"],
  ["0 3 1 * *", "Ayda bir (ayın 1'i, 03:00)"],
];
const EXTRA_CRON = { "* * * * *": "Her dakika", "*/5 * * * *": "5 dakikada bir", "*/15 * * * *": "15 dakikada bir", "*/30 * * * *": "30 dakikada bir" };
const cronText = (c) => (!c ? "Sadece elle" : (PRESETS.find((p) => p[0] === c) || [, EXTRA_CRON[c] || `Özel: ${c}`])[1]);

const I = {
  plane: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M2 11.5 22 3l-6.5 18-3.6-6.6L2 11.5Z"/><path d="M11.9 14.4 22 3 9 12.2Z" opacity=".55"/></svg>',
  play: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7 4.5v15a1 1 0 0 0 1.5.86l12.4-7.5a1 1 0 0 0 0-1.72L8.5 3.64A1 1 0 0 0 7 4.5Z"/></svg>',
  stop: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="5" y="5" width="14" height="14" rx="2.5"/></svg>',
  retry: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="18" height="18" aria-hidden="true"><path d="m3 11 9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="18" height="18" aria-hidden="true"><path d="M9 12l2 2 4-4"/><path d="M12 3l7 3v5c0 4.5-3 8.5-7 10-4-1.5-7-5.5-7-10V6z"/></svg>',
  db: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" aria-hidden="true"><ellipse cx="12" cy="5.5" rx="8" ry="3"/><path d="M4 5.5v13c0 1.7 3.6 3 8 3s8-1.3 8-3v-13M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/></svg>',
  bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="18" height="18" aria-hidden="true"><path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/></svg>',
  team: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="18" height="18" aria-hidden="true"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.8-3.5 3.4-5.5 6.5-5.5s5.7 2 6.5 5.5"/><circle cx="17" cy="9" r="2.5"/><path d="M16.5 14.5c2.6.2 4.4 2 5 4.5"/></svg>',
  warn: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4M12 17v.5"/></svg>',
  info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/></svg>',
  ok: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>',
};

function toast(msg, bad) {
  const t = document.createElement("div");
  t.className = "toast" + (bad ? " bad" : "");
  t.textContent = msg;
  $("#toasts").append(t);
  setTimeout(() => t.remove(), bad ? 6000 : 3500);
}

class ApiError extends Error {}
async function api(path, { method = "GET", body } = {}) {
  const opt = { method, headers: { "X-Requested-With": "unirota" }, credentials: "same-origin" };
  if (body !== undefined) {
    opt.headers["Content-Type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  let r;
  try {
    r = await fetch(path, opt);
  } catch {
    throw new ApiError("Sunucuya ulaşılamadı. Bağlantınızı ya da SSH tünelini kontrol edin.");
  }
  if (r.status === 401 && state.me && !path.startsWith("/api/auth/")) {
    state.me = null;
    renderLogin();
    throw new ApiError("Oturum kapandı");
  }
  const data = r.headers.get("content-type")?.includes("json") ? await r.json() : null;
  if (!r.ok) {
    let d = data?.detail;
    if (Array.isArray(d)) d = d.map((e) => (e.msg || "").replace(/^Value error, /, "")).join(" ");
    throw new ApiError(d || `Hata (${r.status})`);
  }
  return data;
}

/* bir düğmeye basınca işlem bitene kadar kilitle */
async function busy(btn, fn) {
  if (btn) btn.disabled = true;
  try {
    return await fn();
  } catch (e) {
    if (e.message !== "Oturum kapandı") toast(e.message, true);
  } finally {
    if (btn && btn.isConnected) btn.disabled = false;
  }
}

function modal(html, onMount) {
  const bg = document.createElement("div");
  bg.className = "modal-bg";
  bg.innerHTML = `<div class="modal" role="dialog" aria-modal="true">${html}</div>`;
  const close = () => { bg.remove(); document.removeEventListener("keydown", onKey); };
  const onKey = (e) => { if (e.key === "Escape") close(); };
  bg.addEventListener("click", (e) => { if (e.target === bg || e.target.closest("[data-close]")) close(); });
  document.addEventListener("keydown", onKey);
  document.body.append(bg);
  onMount?.(bg.firstElementChild, close);
  bg.querySelector("input,textarea,select,button:not([data-close])")?.focus();
  return close;
}

function sparkline(runs) {
  const vals = (runs || []).map((r) => r.records_written || 0);
  if (vals.length < 2) return `<svg class="spark" viewBox="0 0 120 34" aria-hidden="true"><text x="120" y="22" text-anchor="end" font-size="10" fill="currentColor" opacity=".5">az veri</text></svg>`;
  const max = Math.max(...vals, 1), w = 120, h = 34, p = 3;
  const pts = vals.map((v, i) => [p + (i * (w - 2 * p)) / (vals.length - 1), h - p - (v / max) * (h - 2 * p)]);
  const line = pts.map((q, i) => `${i ? "L" : "M"}${q[0].toFixed(1)},${q[1].toFixed(1)}`).join("");
  const last = pts[pts.length - 1];
  const bad = runs.map((r, i) => (["failed", "timed_out"].includes(r.status) ? `<circle cx="${pts[i][0].toFixed(1)}" cy="${pts[i][1].toFixed(1)}" r="2.6" fill="var(--coral-dot)"/>` : "")).join("");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" role="img" aria-label="Son ${vals.length} çalışmada yazılan kayıt sayısı">
    <path d="${line}L${last[0]},${h}L${p},${h}Z" fill="currentColor" opacity=".12"/>
    <path d="${line}" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>${bad}
    <circle cx="${last[0]}" cy="${last[1]}" r="3.2" fill="currentColor"/></svg>`;
}

function progress(cur, tot, label) {
  const pct = tot ? Math.min(100, (cur / tot) * 100) : null;
  return `<div class="prog">
    <div class="bar"><i style="width:${pct == null ? 100 : pct.toFixed(1)}%;${pct == null ? "opacity:.35" : ""}"></i></div>
    ${pct == null ? "" : `<span class="plane" style="left:${pct.toFixed(1)}%">${I.plane}</span>`}
    <div class="txt"><span>${esc(label || "İlerleme")}</span><span class="num">${tot ? `${num(cur)} / ${num(tot)} · %${Math.floor(pct)}` : cur ? num(cur) : "başlıyor…"}</span></div>
  </div>`;
}

/* ------------------------------------------------------------------ durum ve yönlendirme */
const state = { me: null, timers: [], users: null, nav: {} };

function clearTimers() {
  state.timers.forEach(clearInterval);
  state.timers = [];
}
function every(ms, fn) {
  state.timers.push(setInterval(() => { if (!document.hidden) fn(); }, ms));
}

const routes = [
  [/^$/, pageOverview],
  [/^bot\/(\d+)$/, pageBot],
  [/^yeni-bot$/, pageNewBot],
  [/^kalite$/, pageQuality],
  [/^kapsam$/, pageCoverage],
  [/^bildirimler$/, pageAlerts],
  [/^ekip$/, pageTeam],
];

async function route() {
  if (!state.me) return;
  clearTimers();
  const h = location.hash.replace(/^#\/?/, "");
  const found = routes.find(([re]) => re.test(h)) || routes[0];
  const m = h.match(found[0]) || [];
  renderShell(h);
  const main = $("#main");
  main.innerHTML = `<div class="boot">Yükleniyor…</div>`;
  try {
    await found[1](main, ...m.slice(1));
  } catch (e) {
    if (e.message !== "Oturum kapandı") main.innerHTML = `<div class="note bad">${I.warn}<div>${esc(e.message)}</div></div>`;
  }
  main.focus?.({ preventScroll: true });
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);

function renderShell(h) {
  const items = [
    ["", "Genel bakış", "Genel bakış", I.home],
    ["kalite", "Veri kalitesi", "Kalite", I.check],
    ["kapsam", "Veri kapsamı", "Kapsam", I.db],
    ["bildirimler", "E-posta bildirimleri", "Bildirim", I.bell],
    ["ekip", "Ekip ve işlem kaydı", "Ekip", I.team],
  ];
  const active = h.startsWith("bot/") || h === "yeni-bot" ? "" : h;
  if (!$(".shell")) {
    $("#app").innerHTML = `<div class="shell">
      <aside class="side">
        <a class="brand" href="#/" aria-label="ÜniRota admin paneli, genel bakış">
          <svg width="36" height="36" viewBox="0 0 36 36" aria-hidden="true"><rect width="36" height="36" rx="11" fill="#3448D8"/><path d="M7 18.5 29 9l-7 20-4-7.3Z" fill="#fff"/><path d="m18 21.7 11-12.7-14.4 10.2Z" fill="#C9CCF8"/></svg>
          <span><b>ÜniRota</b><small>kontrol kulesi</small></span>
        </a>
        <div><div class="nav-title">Panel</div><nav class="nav" id="nav"></nav></div>
        <div class="side-foot">
          <div class="runner-dot" id="runnerDot"></div>
          <div class="me"><span class="avatar">${esc(initials(state.me.full_name))}</span><span>${esc(state.me.full_name)}</span></div>
          <button id="logout" type="button">Çıkış yap</button>
        </div>
      </aside>
      <main class="main" id="main" tabindex="-1"></main></div>`;
    $("#logout").onclick = async () => { await api("/api/auth/logout", { method: "POST" }).catch(() => {}); state.me = null; renderLogin(); };
  }
  $("#nav").innerHTML = items.map(([k, long, short, ic]) =>
    `<a href="#/${k}" ${k === active ? 'aria-current="page"' : ""}>${ic}<span class="lbl-long">${long}</span><span class="lbl-short" hidden>${short}</span>${k === "kalite" && state.nav.quarantine ? `<span class="count">${state.nav.quarantine}</span>` : ""}</a>`).join("");
  if (matchMedia("(max-width:860px)").matches) $$("#nav .lbl-short").forEach((e) => (e.hidden = false));
}

function setRunnerDot(runner) {
  const el = $("#runnerDot");
  if (!el) return;
  const ok = runner && runner.age_seconds < 30;
  el.innerHTML = `<span class="pill ${ok ? "s-idle" : "s-error"}" title="Botları başlatan çalıştırıcı">${ok ? "Çalıştırıcı açık" : "Çalıştırıcı kapalı"}</span>`;
}

/* ------------------------------------------------------------------ giriş */
async function renderLogin() {
  clearTimers();
  let needsSetup = false;
  try { needsSetup = (await api("/api/auth/state")).needs_setup; } catch {}
  $("#app").innerHTML = `<div class="login"><form class="card form" id="loginForm" novalidate>
    <div>
      <svg class="plane-hero" viewBox="0 0 24 24" aria-hidden="true">${I.plane.replace(/<\/?svg[^>]*>/g, "")}</svg>
      <h1>ÜniRota</h1><div class="sub">kontrol kulesi</div>
      ${needsSetup ? `<p class="muted" style="margin:0">Henüz kimse yok. İlk yönetici hesabını oluşturun; diğer ekip üyelerini sonra panelden eklersiniz.</p>` : ""}
    </div>
    ${needsSetup ? `
      <div class="field"><label for="fn">Ad soyad</label><input class="input" id="fn" required autocomplete="name"></div>
      <div class="field"><label for="em">E-posta (bildirimler için)</label><input class="input" id="em" type="email" autocomplete="email"></div>` : ""}
    <div class="field"><label for="un">Kullanıcı adı</label><input class="input" id="un" required autocomplete="username" autocapitalize="none" ${needsSetup ? 'placeholder="ör. merve"' : ""}></div>
    <div class="field"><label for="pw">Parola</label><input class="input" id="pw" type="password" required autocomplete="${needsSetup ? "new-password" : "current-password"}">
      ${needsSetup ? '<span class="hint">En az 10 karakter.</span>' : ""}</div>
    <div class="form-err" id="lerr" role="alert"></div>
    <button class="btn btn-primary" type="submit">${needsSetup ? "Hesabı oluştur ve gir" : "Giriş yap"}</button>
  </form></div>`;
  $("#un").focus();
  $("#loginForm").onsubmit = async (e) => {
    e.preventDefault();
    const btn = e.submitter;
    btn.disabled = true;
    $("#lerr").textContent = "";
    try {
      if (needsSetup) {
        await api("/api/auth/setup", { method: "POST", body: { username: $("#un").value.trim().toLowerCase(), full_name: $("#fn").value.trim(), email: $("#em").value.trim() || null, password: $("#pw").value } });
      } else {
        await api("/api/auth/login", { method: "POST", body: { username: $("#un").value.trim(), password: $("#pw").value } });
      }
      await boot();
    } catch (err) {
      $("#lerr").textContent = err.message;
      btn.disabled = false;
    }
  };
}

/* ------------------------------------------------------------------ genel bakış */
async function pageOverview(main) {
  main.innerHTML = `
    <div class="page-head"><div><h1>Genel bakış</h1><p>Bütün botların ve sunucunun şu anki durumu. Sayfa birkaç saniyede bir kendini yeniler.</p></div>
      <a class="btn btn-primary" href="#/yeni-bot">${I.plus} Yeni bot ekle</a></div>
    <div class="stack"><div id="runnerNote"></div><div class="grid g-stats" id="stats"></div>
      <section class="card"><div class="card-head"><h2>Sunucu</h2><span class="muted" id="srvMeta"></span></div><div class="server" id="server"></div></section>
      <section><div class="card-head"><h2>Botlar</h2><span class="muted" id="botCount"></span></div><div class="grid g-bots" id="bots"></div></section>
      <section class="card"><div class="card-head"><h2>Son olaylar</h2></div><ul class="events" id="events"></ul></section>
    </div>`;
  const load = async () => {
    const d = await api("/api/overview");
    const h = d.health;
    setRunnerDot(h.runner);
    $("#runnerNote").innerHTML = h.runner && h.runner.age_seconds < 30 ? "" :
      `<div class="note bad">${I.warn}<div><b>Çalıştırıcı çalışmıyor.</b> Botları başlatan program ${h.runner ? `${rel(h.runner.heartbeat_at)} beri ses vermiyor` : "hiç başlatılmamış"}. Bu sürede ne zamanlanmış ne de elle başlatılan botlar çalışır. Sunucuda <span class="mono">docker compose -f compose.admin.yaml up -d</span> ile başlatılabilir.</div></div>`;
    const c = d.counts;
    $("#stats").innerHTML = [
      ["Şu an çalışan", num(c.running), `${d.bots.length} bottan`],
      ["Son 24 saat başarılı", num(c.ok_24h), "çalışma"],
      ["Son 24 saat hatalı", num(c.failed_24h), c.failed_24h ? "botların sayfasına bakın" : "sorun yok"],
      ["Son 24 saatte kayıt", num(c.records_24h), "yazılan satır"],
    ].map(([k, v, s]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${s}</div></div>`).join("");
    const meter = (label, used, total, pct, fmt) => {
      const cls = pct >= 90 ? "crit" : pct >= 75 ? "warn" : "";
      return `<div class="meter"><div class="top"><span class="label">${label}</span><span class="val">${fmt(used)} / ${fmt(total)}</span></div>
        <div class="bar ${cls}"><i style="width:${Math.min(100, pct).toFixed(1)}%"></i></div><div class="muted" style="font-size:.8rem;margin-top:4px">%${Math.round(pct)} dolu</div></div>`;
    };
    $("#server").innerHTML =
      (h.disk.error ? `<div class="meter"><span class="label">Disk</span><div class="muted">${esc(h.disk.error)}</div></div>` : meter("Disk", h.disk.used, h.disk.total, h.disk.percent, gb)) +
      meter("Bellek", h.memory.used, h.memory.total, h.memory.percent, gb) +
      `<div class="meter"><div class="top"><span class="label">İşlemci</span><span class="val">${h.cpu_count} çekirdek</span></div>
        <div class="bar ${h.cpu_percent >= 90 ? "crit" : h.cpu_percent >= 75 ? "warn" : ""}"><i style="width:${h.cpu_percent}%"></i></div><div class="muted" style="font-size:.8rem;margin-top:4px">%${Math.round(h.cpu_percent)} kullanımda</div></div>` +
      `<div class="meter"><div class="top"><span class="label">Veritabanı</span><span class="val">${esc(h.database.version)}</span></div>
        <div style="font-family:var(--fd);font-size:1.35rem;margin-top:6px" class="num">${mb(h.database.size)}</div><div class="muted" style="font-size:.8rem">${dur(h.database.uptime_seconds)} açık</div></div>`;
    $("#srvMeta").textContent = `${h.hostname} · ${dur(h.uptime_seconds)} açık`;
    $("#botCount").textContent = `${d.bots.length} bot`;
    $("#bots").innerHTML = d.bots.length ? d.bots.map(botCard).join("") :
      `<div class="card empty" style="grid-column:1/-1"><b>Henüz bot yok</b>İlk botu ekleyin; eklediğiniz her bot burada ayrı bir kart olarak görünür.<div style="margin-top:14px"><a class="btn btn-primary" href="#/yeni-bot">${I.plus} Yeni bot ekle</a></div></div>`;
    $("#events").innerHTML = d.events.length ? d.events.map(eventRow).join("") : `<li class="empty" style="display:block">Henüz hiçbir bot çalışmadı.</li>`;
    const q = await api("/api/quality/summary").catch(() => null);
    if (q) { state.nav.quarantine = q.quarantine_open; }
  };
  await load();
  every(5000, () => load().catch(() => {}));
}

function botCard(b) {
  const err = b.state === "error" && b.last_error ? `<div class="err">${esc(b.last_error.slice(0, 160))}</div>` : "";
  const live = b.state === "running" ? progress(b.progress_current, b.progress_total, b.progress_label) :
    b.state === "queued" ? `<div class="muted" style="font-size:.85rem">Sırada, çalıştırıcı birazdan başlatacak.</div>` : "";
  return `<a class="card bot" href="#/bot/${b.bot_id}">
    <div class="t"><div style="min-width:0"><h3>${esc(b.name)}</h3><div class="src">${esc(b.description || b.slug)}</div></div>${pill(b.state, STATE[b.state])}</div>
    ${live}
    <dl>
      <dt>Son çalışma</dt><dd>${b.last_finished_at ? `${rel(b.last_finished_at)} · ${RUN[b.last_status]}` : "henüz yok"}</dd>
      <dt>Kayıt</dt><dd>${b.state === "running" ? num(b.active_records) + " (şu an)" : num(b.last_records)}</dd>
      <dt>Zamanlama</dt><dd>${esc(cronText(b.schedule_cron))}</dd>
      ${b.next_run_at ? `<dt>Sonraki</dt><dd>${fmtDate(b.next_run_at)}</dd>` : ""}
      ${b.open_failed ? `<dt>Bekleyen hata</dt><dd style="color:var(--coral)">${num(b.open_failed)} istek</dd>` : ""}
    </dl>${err}
    <div class="foot"><span class="owner">${b.owner_name ? `<span class="avatar">${esc(initials(b.owner_name))}</span>${esc(b.owner_name)}` : "Sorumlu yok"}</span>${sparkline(b.recent)}</div>
  </a>`;
}

function eventRow(e) {
  const map = {
    succeeded: ["s-succeeded", I.ok, `${num(e.records_written)} kayıt yazdı`],
    failed: ["s-failed", I.x, e.error_message || "hata verdi"],
    timed_out: ["s-failed", I.x, "zaman aşımına uğradı"],
    stopped: ["s-stopped", I.stop, "durduruldu"],
    running: ["s-running", I.play, "çalışmaya başladı"],
    queued: ["s-queued", I.play, "sıraya alındı"],
  };
  const [cls, ic, txt] = map[e.status] || map.queued;
  const who = e.trigger === "schedule" ? "" : e.by_name;
  return `<li><span class="ic ${cls}">${ic}</span><div style="min-width:0"><a href="#/bot/${e.bot_id}" style="font-weight:700;color:var(--ink)">${esc(e.bot_name)}</a> ${esc(txt.length > 140 ? txt.slice(0, 140) + "…" : txt)}
    <div class="muted" style="font-size:.8rem">#${e.run_id} · ${esc(TRIG[e.trigger])}${who ? " · " + esc(who) : ""}</div></div><span class="when" title="${esc(fmtDate(e.ts, true))}">${rel(e.ts)}</span></li>`;
}

/* ------------------------------------------------------------------ bot sayfası */
async function pageBot(main, id) {
  const ui = { tab: sessionGet("bottab") || "runs", run: null, logRun: null, logLast: 0, logLevel: "", logQ: "", follow: true };
  let b = await api(`/api/bots/${id}`);
  main.innerHTML = `
    <div class="crumb"><a href="#/">Genel bakış</a> / ${esc(b.name)}</div>
    <div class="page-head" id="head"></div>
    <div class="stack">
      <div id="live"></div>
      <div class="grid g-stats" id="bstats"></div>
      <section class="card"><div class="tabs" role="tablist" id="tabs"></div><div id="tabBody"></div></section>
    </div>`;

  const renderHead = () => {
    const active = ["running", "queued"].includes(b.state);
    $("#head").innerHTML = `<div style="min-width:0"><div class="row"><h1>${esc(b.name)}</h1>${pill(b.state, STATE[b.state])}</div>
        <p>${esc(b.description || "")}${b.source_url ? ` <a href="${esc(b.source_url)}" target="_blank" rel="noopener">Kaynak</a>` : ""}</p></div>
      <div class="row">
        ${active ? `<button class="btn btn-danger" id="stopBtn" ${b.active_stop_requested ? "disabled" : ""}>${I.stop} ${b.active_stop_requested ? "Duruyor…" : "Durdur"}</button>`
                 : `<button class="btn btn-primary" id="runBtn" ${b.enabled ? "" : 'disabled title="Bot kapalı"'}>${I.play} Şimdi çalıştır</button>`}
        <button class="btn btn-ghost" id="retryBtn" ${!b.open_failed || active || !b.enabled ? "disabled" : ""}>${I.retry} Hatalıları yeniden dene${b.open_failed ? ` (${num(b.open_failed)})` : ""}</button>
        <label class="switch" title="Kapalı bot ne zamanlayıcıyla ne elle çalışır"><input type="checkbox" id="enSw" ${b.enabled ? "checked" : ""}><span class="tr"></span><span id="enTxt">${b.enabled ? "Açık" : "Kapalı"}</span></label>
      </div>`;
    $("#runBtn") && ($("#runBtn").onclick = (e) => busy(e.currentTarget, async () => {
      const r = await api(`/api/bots/${id}/run`, { method: "POST" });
      toast(`Bot sıraya alındı (#${r.run_id}). Çalıştırıcı birkaç saniye içinde başlatır.`);
      ui.logRun = null; ui.logLast = 0;
      await refresh();
    }));
    $("#stopBtn") && ($("#stopBtn").onclick = () => modal(`<h2>Bot durdurulsun mu?</h2>
        <p class="muted">${esc(b.name)} o anki işini bitirip duracak. Yazılan kayıtlar silinmez; bot bir sonraki çalışmada baştan ya da kaldığı yerden devam eder (botun yazılışına bağlı).</p>
        <div class="acts"><button class="btn btn-ghost" data-close>Vazgeç</button><button class="btn btn-danger" id="yes">${I.stop} Durdur</button></div>`,
      (m, close) => { $("#yes", m).onclick = (e) => busy(e.currentTarget, async () => { await api(`/api/bots/${id}/stop`, { method: "POST" }); close(); toast("Durdurma isteği gönderildi."); await refresh(); }); }));
    $("#retryBtn").onclick = (e) => busy(e.currentTarget, async () => {
      const r = await api(`/api/bots/${id}/retry`, { method: "POST" });
      toast(`${num(r.count)} başarısız istek yeniden denenecek (#${r.run_id}).`);
      await refresh();
    });
    $("#enSw").onchange = (e) => busy(null, async () => {
      try {
        b = { ...b, ...(await api(`/api/bots/${id}`, { method: "PATCH", body: { enabled: e.target.checked } })) };
        toast(b.enabled ? "Bot açıldı." : "Bot kapatıldı. Zamanlayıcı da onu çalıştırmayacak.");
      } catch (err) { e.target.checked = !e.target.checked; throw err; }
      renderAll();
    });
  };

  const renderLive = () => {
    const el = $("#live");
    if (!["running", "queued"].includes(b.state)) { el.innerHTML = ""; return; }
    el.innerHTML = `<section class="card"><div class="card-head"><h2>${b.state === "queued" ? "Sırada bekliyor" : "Şu an çalışıyor"}</h2>
      <span class="muted">#${b.active_run_id} · ${esc(TRIG[b.active_trigger])}</span></div>
      ${b.state === "running" ? progress(b.progress_current, b.progress_total, b.progress_label) : `<p class="muted">Çalıştırıcı boşta olunca başlayacak.</p>`}
      ${b.state === "running" ? `<div class="runsum" style="margin-top:14px">
        <div><span>Başladı</span><b>${fmtDate(b.active_started_at)}</b></div>
        <div><span>Geçen süre</span><b>${dur((Date.now() - new Date(b.active_started_at)) / 1000)}</b></div>
        <div><span>Son ses</span><b>${rel(b.active_heartbeat_at)}</b></div>
        <div><span>Yazılan kayıt</span><b>${num(b.active_records)}</b></div></div>` : ""}</section>`;
  };

  const renderStats = () => {
    const s = b.stats;
    $("#bstats").innerHTML = [
      ["Toplam çalışma", num(s.runs), `${num(s.ok)} başarılı, ${num(s.failed)} hatalı`],
      ["Başarı oranı", s.runs ? `%${Math.round((s.ok / s.runs) * 100)}` : "–", "bütün çalışmalarda"],
      ["Ortalama süre", dur(s.avg_seconds), "başarılı çalışmalarda"],
      ["Toplam kayıt", num(s.records), "bütün çalışmalarda"],
      ["Sonraki çalışma", b.next_run_at ? fmtDate(b.next_run_at) : "–", cronText(b.schedule_cron)],
    ].map(([k, v, t]) => `<div class="stat"><div class="k">${k}</div><div class="v" style="font-size:1.2rem">${v}</div><div class="s">${esc(t)}</div></div>`).join("");
  };

  const TABS = [["runs", "Çalışmalar"], ["logs", "Loglar"], ["failed", "Başarısız istekler"], ["settings", "Ayarlar"], ["audit", "İşlem kaydı"]];
  const renderTabs = () => {
    $("#tabs").innerHTML = TABS.map(([k, t]) => `<button role="tab" aria-selected="${ui.tab === k}" data-tab="${k}">${t}${k === "failed" && b.open_failed ? `<span class="badge">${num(b.open_failed)}</span>` : ""}</button>`).join("");
    $$("#tabs button").forEach((x) => (x.onclick = () => { ui.tab = x.dataset.tab; sessionSet("bottab", ui.tab); renderTabs(); renderTab(); }));
  };

  const renderTab = async (poll) => {
    const body = $("#tabBody");
    if (ui.tab === "runs") return tabRuns(body, poll);
    if (ui.tab === "logs") return tabLogs(body, poll);
    if (poll) return;
    if (ui.tab === "failed") return tabFailed(body);
    if (ui.tab === "settings") return tabSettings(body);
    if (ui.tab === "audit") return tabAudit(body);
  };

  async function tabRuns(body, poll) {
    const runs = await api(`/api/bots/${id}/runs?limit=50`);
    if (!runs.length) { body.innerHTML = `<div class="empty"><b>Bu bot henüz hiç çalışmadı</b>"Şimdi çalıştır" ile ilk çalışmayı başlatabilirsiniz.</div>`; return; }
    if (poll && $("#runTbl") && $("#runTbl").dataset.sig === sig(runs)) return;
    body.innerHTML = `<div class="tbl-wrap"><table id="runTbl" data-sig="${sig(runs)}"><thead><tr><th>#</th><th>Durum</th><th>Başlatan</th><th>Başladı</th><th class="n">Süre</th><th class="n">Kayıt</th><th class="n">İstek (başarılı / hatalı)</th><th class="n">Uyarı / hata</th></tr></thead><tbody>
      ${runs.map((r) => `<tr class="click ${ui.run === r.run_id ? "sel" : ""}" data-run="${r.run_id}" tabindex="0">
        <td class="n">${r.run_id}</td><td>${pill(r.status, RUN[r.status])}</td>
        <td>${esc(r.trigger === "schedule" ? "Zamanlayıcı" : (r.by_name || "–") + (r.trigger === "retry" ? " (yeniden deneme)" : ""))}</td>
        <td>${fmtDate(r.started_at || r.queued_at)}</td><td class="n">${r.started_at ? dur(r.seconds) : "–"}</td>
        <td class="n">${num(r.records_written)}</td><td class="n">${num(r.pages_ok)} / <span style="color:${r.pages_failed ? "var(--coral)" : "inherit"}">${num(r.pages_failed)}</span></td>
        <td class="n">${num(r.warnings)} / ${num(r.errors)}</td></tr>`).join("")}</tbody></table></div><div id="runDetail"></div>`;
    $$("#runTbl tr.click").forEach((tr) => {
      const open = () => { ui.run = +tr.dataset.run; $$("#runTbl tr").forEach((x) => x.classList.toggle("sel", x === tr)); showRun(ui.run); };
      tr.onclick = open;
      tr.onkeydown = (e) => { if (e.key === "Enter") open(); };
    });
    if (ui.run) showRun(ui.run);
  }

  async function showRun(runId) {
    const r = await api(`/api/runs/${runId}`);
    const el = $("#runDetail");
    if (!el) return;
    const extra = Object.entries(r.summary || {}).map(([k, v]) => `<div><span>${esc(k)}</span><b>${esc(typeof v === "object" ? JSON.stringify(v) : v)}</b></div>`).join("");
    el.innerHTML = `<div style="margin-top:18px;border-top:1px solid var(--line);padding-top:16px">
      <div class="card-head"><h3>Çalışma #${r.run_id} özeti</h3>
        <button class="btn btn-ghost btn-sm" id="toLogs">Bu çalışmanın loglarını aç</button></div>
      ${r.error_message ? `<div class="note bad" style="margin-bottom:12px">${I.warn}<div class="mono">${esc(r.error_message)}</div></div>` : ""}
      <div class="runsum">
        <div><span>Durum</span><b>${esc(RUN[r.status])}</b></div>
        <div><span>Başladı</span><b>${fmtDate(r.started_at, true)}</b></div>
        <div><span>Bitti</span><b>${fmtDate(r.finished_at, true)}</b></div>
        <div><span>Süre</span><b>${r.started_at ? dur(r.seconds) : "–"}</b></div>
        <div><span>İstenen sayfa</span><b>${num(r.pages_requested)}</b></div>
        <div><span>Başarılı</span><b>${num(r.pages_ok)}</b></div>
        <div><span>Başarısız</span><b>${num(r.pages_failed)}</b></div>
        <div><span>Yazılan kayıt</span><b>${num(r.records_written)}</b></div>
        <div><span>Uyarı</span><b>${num(Math.max(r.warnings, r.log_counts.warning))}</b></div>
        <div><span>Kritik hata</span><b>${num(Math.max(r.errors, r.log_counts.error))}</b></div>
        <div><span>Çıkış kodu</span><b>${r.exit_code ?? "–"}</b></div>
        <div><span>Ham kayıt no</span><b>${r.ingestion_run_id ?? "–"}</b></div>${extra}
      </div></div>`;
    $("#toLogs").onclick = () => { ui.logRun = r.run_id; ui.logLast = 0; ui.tab = "logs"; sessionSet("bottab", "logs"); renderTabs(); renderTab(); };
  }

  async function tabLogs(body, poll) {
    if (!poll || !$("#logbox")) {
      const runs = await api(`/api/bots/${id}/runs?limit=30`);
      if (!runs.length) { body.innerHTML = `<div class="empty"><b>Henüz log yok</b>Bot ilk kez çalıştığında çıktısı burada canlı akar.</div>`; return; }
      if (!ui.logRun || !runs.some((r) => r.run_id === ui.logRun)) ui.logRun = runs[0].run_id;
      body.innerHTML = `<div class="row" style="margin-bottom:12px">
          <select class="input" id="logRun" style="width:auto">${runs.map((r) => `<option value="${r.run_id}" ${r.run_id === ui.logRun ? "selected" : ""}>#${r.run_id} · ${fmtDate(r.started_at || r.queued_at)} · ${RUN[r.status]}</option>`).join("")}</select>
          <select class="input" id="logLvl" style="width:auto"><option value="">Bütün satırlar</option><option value="warning" ${ui.logLevel === "warning" ? "selected" : ""}>Uyarı ve hatalar</option><option value="error" ${ui.logLevel === "error" ? "selected" : ""}>Sadece hatalar</option></select>
          <input class="input" id="logQ" placeholder="Logda ara" style="width:auto;flex:1;min-width:140px" value="${esc(ui.logQ)}">
          <label class="switch"><input type="checkbox" id="follow" ${ui.follow ? "checked" : ""}><span class="tr"></span>Canlı takip</label>
        </div><div class="logbox" id="logbox" role="log"></div>`;
      ui.logLast = 0;
      $("#logRun").onchange = (e) => { ui.logRun = +e.target.value; ui.logLast = 0; $("#logbox").innerHTML = ""; fetchLogs(); };
      $("#logLvl").onchange = (e) => { ui.logLevel = e.target.value; ui.logLast = 0; $("#logbox").innerHTML = ""; fetchLogs(); };
      let t;
      $("#logQ").oninput = (e) => { clearTimeout(t); t = setTimeout(() => { ui.logQ = e.target.value.trim(); ui.logLast = 0; $("#logbox").innerHTML = ""; fetchLogs(); }, 300); };
      $("#follow").onchange = (e) => (ui.follow = e.target.checked);
    }
    await fetchLogs();
  }

  async function fetchLogs() {
    const box = $("#logbox");
    if (!box) return;
    const p = new URLSearchParams({ after_id: ui.logLast, limit: ui.logLast ? 1000 : 800 });
    if (ui.logLevel) p.set("level", ui.logLevel);
    if (ui.logQ) p.set("q", ui.logQ);
    const runAtStart = ui.logRun;
    const rows = await api(`/api/runs/${ui.logRun}/logs?${p}`);
    if (runAtStart !== ui.logRun || !box.isConnected) return;
    if (!rows.length && !ui.logLast) { box.innerHTML = `<div class="none">${ui.logLevel || ui.logQ ? "Bu filtreye uyan satır yok." : "Bu çalışmada henüz log yok."}</div>`; return; }
    if (!rows.length) return;
    $(".none", box)?.remove();
    box.insertAdjacentHTML("beforeend", rows.map((l) => `<div class="l ${l.level === "error" ? "lv-row-error" : ""}"><span class="ts">${new Date(l.ts).toLocaleTimeString("tr-TR")}</span><span class="lv lv-${l.level}">${{ info: "BİLGİ", debug: "AYRINTI", warning: "UYARI", error: "HATA" }[l.level]}</span><span class="m">${esc(l.message)}</span></div>`).join(""));
    ui.logLast = rows[rows.length - 1].log_id;
    if (ui.follow) box.scrollTop = box.scrollHeight;
  }

  async function tabFailed(body) {
    const rows = await api(`/api/bots/${id}/failed`);
    if (!rows.length) { body.innerHTML = `<div class="empty"><b>Bekleyen başarısız istek yok</b>Bot bir sayfayı indiremezse burada listelenir; buradan tekrar denetebilirsiniz.</div>`; return; }
    body.innerHTML = `<div class="row" style="justify-content:space-between;margin-bottom:12px"><span class="muted">${num(rows.length)} istek bekliyor. "Hatalıları yeniden dene" sadece bunları tekrar dener.</span></div>
      <div class="tbl-wrap"><table><thead><tr><th>İstek</th><th>Adres</th><th class="n">HTTP</th><th>Hata</th><th class="n">Deneme</th><th>Ne zaman</th><th></th></tr></thead><tbody>
      ${rows.map((f) => `<tr><td class="mono">${esc(f.request_key)}</td><td class="mono" style="max-width:280px;overflow-wrap:anywhere">${esc(f.url || "–")}</td><td class="n">${f.http_status ?? "–"}</td>
        <td style="max-width:280px">${esc(f.error || "–")}</td><td class="n">${f.attempts}</td><td>${fmtDate(f.created_at)}</td>
        <td><button class="btn btn-ghost btn-sm" data-dismiss="${f.failed_id}" title="Bu isteği listeden kaldır, yeniden deneme">Yok say</button></td></tr>`).join("")}</tbody></table></div>`;
    $$("[data-dismiss]", body).forEach((btn) => (btn.onclick = () => busy(btn, async () => {
      await api(`/api/failed/${btn.dataset.dismiss}/dismiss`, { method: "POST" });
      toast("İstek listeden kaldırıldı.");
      await refresh(); tabFailed(body);
    })));
  }

  async function tabSettings(body) {
    const users = await getUsers();
    body.innerHTML = botForm(b, users) + `
      <div style="margin-top:28px;border-top:1px solid var(--line);padding-top:18px" class="row">
        <div style="flex:1;min-width:220px"><h3>Botu sil</h3><p class="muted" style="margin:4px 0 0">Bot, bütün çalışma geçmişi ve logları silinir. Topladığı veri tablolarda kalır.</p></div>
        <button class="btn btn-danger" id="delBot">Botu sil</button></div>`;
    wireBotForm(body, async (data, btn) => {
      await busy(btn, async () => {
        const nb = await api(`/api/bots/${id}`, { method: "PATCH", body: data });
        b = { ...b, ...nb };
        toast("Ayarlar kaydedildi.");
        renderHead(); renderStats();
      });
    });
    $("#delBot").onclick = () => modal(`<h2>${esc(b.name)} silinsin mi?</h2><p class="muted">Bu geri alınamaz. Onaylamak için botun kısa adını yazın: <b class="mono">${esc(b.slug)}</b></p>
      <input class="input" id="cs" autocomplete="off"><div class="form-err" id="cserr"></div>
      <div class="acts"><button class="btn btn-ghost" data-close>Vazgeç</button><button class="btn btn-danger" id="yes">Kalıcı olarak sil</button></div>`,
      (m) => { $("#yes", m).onclick = (e) => busy(e.currentTarget, async () => {
        await api(`/api/bots/${id}`, { method: "DELETE", body: { confirm_slug: $("#cs", m).value.trim() } });
        m.parentElement.remove(); toast("Bot silindi."); location.hash = "#/";
      }); });
  }

  async function tabAudit(body) {
    const rows = await api(`/api/audit?bot_id=${id}&limit=100`);
    body.innerHTML = auditTable(rows, "Bu bot için henüz kimse bir şey yapmadı.");
  }

  const renderAll = () => { renderHead(); renderLive(); renderStats(); renderTabs(); };
  async function refresh(poll) {
    const prevState = b.state;
    b = await api(`/api/bots/${id}`);
    if (!poll || prevState !== b.state) renderHead();
    renderLive(); renderStats();
    if (!poll) renderTabs();
    else { const badge = $('#tabs [data-tab="failed"]'); if (badge) badge.innerHTML = `Başarısız istekler${b.open_failed ? `<span class="badge">${num(b.open_failed)}</span>` : ""}`; }
    if (poll && prevState !== b.state && ui.tab === "logs" && b.active_run_id && b.active_run_id !== ui.logRun) { ui.logRun = null; return renderTab(); }
    await renderTab(poll);
  }
  renderAll();
  await renderTab();
  every(3000, () => refresh(true).catch(() => {}));
}

const sig = (runs) => runs.map((r) => `${r.run_id}:${r.status}:${r.records_written}:${r.pages_ok}:${r.pages_failed}`).join("|");
function sessionGet(k) { try { return sessionStorage.getItem("unirota." + k); } catch { return null; } }
function sessionSet(k, v) { try { sessionStorage.setItem("unirota." + k, v); } catch {} }

async function getUsers(force) {
  if (!state.users || force) state.users = await api("/api/users");
  return state.users;
}

/* ------------------------------------------------------------------ bot formu (yeni / ayarlar) */
function botForm(b, users, isNew) {
  const s = b.settings || {};
  const preset = PRESETS.some((p) => p[0] === (b.schedule_cron || "")) ? b.schedule_cron || "" : "custom";
  const kvRow = (k = "", v = "") => `<div class="kv"><input class="input mono" placeholder="ayar adı" value="${esc(k)}" data-k><input class="input mono" placeholder="değer" value="${esc(typeof v === "object" ? JSON.stringify(v) : v)}" data-v><button type="button" class="btn btn-ghost btn-sm" data-rm aria-label="Satırı sil">${I.x.replace("<svg", '<svg width="14" height="14"')}</button></div>`;
  return `<form class="form" id="botForm" novalidate>
    <div class="f2">
      <div class="field"><label for="f_name">Bot adı</label><input class="input" id="f_name" value="${esc(b.name || "")}" required placeholder="ör. YÖK Atlas · Netler"></div>
      ${isNew ? `<div class="field"><label for="f_slug">Kısa ad</label><input class="input mono" id="f_slug" value="${esc(b.slug || "")}" required placeholder="ör. yokatlas-netler"><span class="hint">Küçük harf, rakam ve tire. Sonra değiştirilemez.</span></div>` : `<div class="field"><span class="lbl">Kısa ad</span><div class="mono" style="padding:10px 0">${esc(b.slug)}</div></div>`}
    </div>
    <div class="field"><label for="f_desc">Açıklama</label><input class="input" id="f_desc" value="${esc(b.description || "")}" placeholder="Bot ne topluyor, nereden?"></div>
    <div class="f2">
      <div class="field"><label for="f_src">Kaynak adresi</label><input class="input" id="f_src" value="${esc(b.source_url || "")}" placeholder="https://…"></div>
      <div class="field"><label for="f_owner">Sorumlu</label><select class="input" id="f_owner"><option value="">Sorumlu yok</option>${users.filter((u) => u.is_active).map((u) => `<option value="${u.user_id}" ${u.user_id === b.owner_user_id ? "selected" : ""}>${esc(u.full_name)}</option>`).join("")}</select></div>
    </div>
    <div class="f2">
      <div class="field"><label for="f_cmd">Çalıştırma komutu</label><input class="input mono" id="f_cmd" value="${esc(b.command || "")}" required placeholder="python -m scraper.yokatlas_netler"><span class="hint">Sunucuda repo klasöründen çalıştırılır.</span></div>
      <div class="field"><label for="f_wd">Çalışma klasörü</label><input class="input mono" id="f_wd" value="${esc(b.working_dir || ".")}" placeholder="."><span class="hint">Repo köküne göre. "." = repo kökü.</span></div>
    </div>
    <div class="f2">
      <div class="field"><label for="f_sched">Ne zaman çalışsın?</label><select class="input" id="f_sched">${PRESETS.map(([v, t]) => `<option value="${esc(v)}" ${preset === v ? "selected" : ""}>${esc(t)}</option>`).join("")}<option value="custom" ${preset === "custom" ? "selected" : ""}>Özel (cron)</option></select></div>
      <div class="field" id="cronWrap" ${preset === "custom" ? "" : "hidden"}><label for="f_cron">Özel zamanlama (cron, Türkiye saati)</label><input class="input mono" id="f_cron" value="${esc(preset === "custom" ? b.schedule_cron : "")}" placeholder="0 3 * * *"><span class="hint">dakika saat gün ay haftanın-günü</span></div>
    </div>
    <div class="f2">
      <div class="field"><label for="f_to">Zaman aşımı (dakika)</label><input class="input" id="f_to" type="number" min="1" max="2880" value="${esc(b.timeout_minutes || 180)}"><span class="hint">Bu süreyi aşan çalışma durdurulur.</span></div>
      <div class="field"><label for="f_min">Beklenen en az kayıt</label><input class="input" id="f_min" type="number" min="0" value="${esc(b.expected_min_records ?? "")}" placeholder="boş = kontrol yok"><span class="hint">Daha az gelirse e-posta uyarısı gider (site yapısı değişmiş olabilir).</span></div>
    </div>
    <div class="field"><span class="lbl">Bot ayarları</span><span class="hint">Bot bunları <span class="mono">bot.settings</span> ile okur. Örnek: bekleme_saniye, deneme_sayisi, puan_turleri.</span>
      <div id="kvList" style="display:grid;gap:8px">${Object.entries(s).map(([k, v]) => kvRow(k, v)).join("") || kvRow()}</div>
      <div><button type="button" class="btn btn-ghost btn-sm" id="kvAdd">${I.plus.replace("<svg", '<svg width="14" height="14"')} Ayar ekle</button></div></div>
    <div class="form-err" id="ferr" role="alert"></div>
    <div><button class="btn btn-primary" type="submit">${isNew ? "Botu ekle" : "Ayarları kaydet"}</button></div>
  </form>`;
}

function wireBotForm(root, onSubmit) {
  const f = $("#botForm", root);
  const kvRowHtml = () => `<div class="kv"><input class="input mono" placeholder="ayar adı" data-k><input class="input mono" placeholder="değer" data-v><button type="button" class="btn btn-ghost btn-sm" data-rm aria-label="Satırı sil">${I.x.replace("<svg", '<svg width="14" height="14"')}</button></div>`;
  $("#kvAdd", f).onclick = () => $("#kvList", f).insertAdjacentHTML("beforeend", kvRowHtml());
  $("#kvList", f).onclick = (e) => { const b = e.target.closest("[data-rm]"); if (b) b.parentElement.remove(); };
  $("#f_sched", f).onchange = (e) => ($("#cronWrap", f).hidden = e.target.value !== "custom");
  const nameEl = $("#f_name", f), slugEl = $("#f_slug", f);
  if (slugEl) { let touched = !!slugEl.value; slugEl.oninput = () => (touched = true); nameEl.oninput = () => { if (!touched) slugEl.value = slugify(nameEl.value); }; }
  f.onsubmit = (e) => {
    e.preventDefault();
    $("#ferr", f).textContent = "";
    const settings = {};
    for (const row of $$("#kvList .kv", f)) {
      const k = $("[data-k]", row).value.trim(), raw = $("[data-v]", row).value.trim();
      if (!k) continue;
      let v = raw;
      if (/^-?\d+(\.\d+)?$/.test(raw)) v = Number(raw);
      else if (raw === "true" || raw === "false") v = raw === "true";
      else if (/^[[{]/.test(raw)) { try { v = JSON.parse(raw); } catch { $("#ferr", f).textContent = `"${k}" ayarının değeri geçerli JSON değil.`; return; } }
      settings[k] = v;
    }
    const sched = $("#f_sched", f).value;
    const data = {
      name: nameEl.value.trim(), description: $("#f_desc", f).value.trim(), source_url: $("#f_src", f).value.trim() || null,
      owner_user_id: $("#f_owner", f).value ? +$("#f_owner", f).value : null, command: $("#f_cmd", f).value.trim(),
      working_dir: $("#f_wd", f).value.trim() || ".", schedule_cron: sched === "custom" ? $("#f_cron", f).value.trim() : sched,
      timeout_minutes: +$("#f_to", f).value || 180, expected_min_records: $("#f_min", f).value === "" ? null : +$("#f_min", f).value, settings,
    };
    if (slugEl) data.slug = slugEl.value.trim();
    if (!data.name || !data.command || (slugEl && !data.slug)) { $("#ferr", f).textContent = "Bot adı, kısa ad ve çalıştırma komutu zorunlu."; return; }
    if (sched === "custom" && !data.schedule_cron) { $("#ferr", f).textContent = "Özel zamanlamayı yazın ya da listeden seçin."; return; }
    onSubmit(data, e.submitter).catch?.((err) => ($("#ferr", f).textContent = err.message));
  };
}

async function pageNewBot(main) {
  const users = await getUsers();
  main.innerHTML = `<div class="crumb"><a href="#/">Genel bakış</a> / Yeni bot</div>
    <div class="page-head"><div><h1>Yeni bot ekle</h1><p>Bot eklemek panelin kodunu değiştirmez. Botun kodu sunucudaki repoda olmalı; burada sadece nasıl ve ne zaman çalışacağını söylüyorsunuz.</p></div></div>
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));align-items:start">
      <section class="card" id="nb"></section>
      <section class="card" style="background:var(--bg-2);box-shadow:none">
        <h2 style="margin-bottom:10px">Bot panelle nasıl konuşur?</h2>
        <p class="muted" style="margin-top:0">Her komut çalışır; çıktısı log olarak görünür, çıkış kodu 0 ise başarılı sayılır. İlerleme, kayıt sayısı, başarısız istekler ve durdurma için botun içinde <span class="mono">botkit</span> kullanın:</p>
        <pre class="logbox" style="padding:14px;margin:0;white-space:pre;overflow:auto">from botkit import Bot

with Bot.from_env() as bot:
    bekle = bot.settings.get("bekleme_saniye", 1.5)
    for i, sayfa in enumerate(sayfalar, 1):
        if bot.should_stop():
            break
        bot.progress(i, len(sayfalar), "Sayfalar")
        try:
            veri = indir(sayfa)
            bot.request_ok()
            bot.records(kaydet(veri))
        except Exception as e:
            bot.request_failed(f"sayfa:{sayfa}", error=str(e))
        bot.sleep(bekle)</pre>
        <p class="muted" style="margin-bottom:0">Ayrıntılı örnek: repodaki <span class="mono">admin-panel/bots/ornek_bot.py</span>.</p>
      </section></div>`;
  $("#nb").innerHTML = botForm({ settings: { bekleme_saniye: 1.5, deneme_sayisi: 3 }, working_dir: ".", timeout_minutes: 180 }, users, true);
  wireBotForm($("#nb"), async (data, btn) => {
    btn.disabled = true;
    try {
      const nb = await api("/api/bots", { method: "POST", body: data });
      toast(`${nb.name} eklendi.`);
      location.hash = `#/bot/${nb.bot_id}`;
    } catch (e) { btn.disabled = false; throw e; }
  });
}

/* ------------------------------------------------------------------ veri kalitesi */
async function pageQuality(main) {
  const ui = { tab: "checks", status: "" };
  main.innerHTML = `<div class="page-head"><div><h1>Veri kalitesi</h1><p>Botların çalıştırdığı kalite kontrolleri ve şüpheli diye karantinaya alınan kayıtlar. Karantinadaki kayıt incelenip "çözüldü" diye işaretlenir.</p></div></div>
    <div class="stack"><div class="grid g-stats" id="qs"></div>
    <section class="card"><div class="tabs" role="tablist" id="qtabs"></div><div id="qbody"></div></section></div>`;
  const loadSummary = async () => {
    const s = await api("/api/quality/summary");
    state.nav.quarantine = s.quarantine_open;
    $("#qs").innerHTML = [["Son 7 gün kontrol", s.checks_7d], ["Kalan kontrol", s.fail_7d], ["Uyarı", s.warn_7d], ["Karantinada bekleyen", s.quarantine_open]]
      .map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${num(v)}</div></div>`).join("");
    $("#qtabs").innerHTML = [["checks", "Kontroller"], ["quarantine", "Karantina"]].map(([k, t]) => `<button role="tab" aria-selected="${ui.tab === k}" data-t="${k}">${t}${k === "quarantine" && s.quarantine_open ? `<span class="badge">${num(s.quarantine_open)}</span>` : ""}</button>`).join("");
    $$("#qtabs button").forEach((b) => (b.onclick = () => { ui.tab = b.dataset.t; loadSummary(); loadTab(); }));
  };
  const loadTab = async () => {
    const body = $("#qbody");
    if (ui.tab === "checks") {
      const rows = await api(`/api/quality/checks${ui.status ? "?status=" + ui.status : ""}`);
      body.innerHTML = `<div class="row" style="margin-bottom:12px"><select class="input" id="qf" style="width:auto"><option value="">Bütün sonuçlar</option><option value="fail" ${ui.status === "fail" ? "selected" : ""}>Kalanlar</option><option value="warn" ${ui.status === "warn" ? "selected" : ""}>Uyarılar</option><option value="pass" ${ui.status === "pass" ? "selected" : ""}>Geçenler</option></select></div>` +
        (rows.length ? `<div class="tbl-wrap"><table><thead><tr><th>Sonuç</th><th>Kontrol</th><th>Bot</th><th>Görülen değer</th><th>Ne zaman</th></tr></thead><tbody>
        ${rows.map((c) => `<tr><td>${pill(c.status, CHECK[c.status] || c.status)}</td><td>${esc(c.check_name)}</td><td>${c.bot_id ? `<a href="#/bot/${c.bot_id}">${esc(c.bot_name)}</a>` : esc(c.source_system || "–")}</td>
          <td class="mono" style="max-width:320px;overflow-wrap:anywhere">${esc(c.observed_value == null ? "–" : JSON.stringify(c.observed_value))}</td><td>${fmtDate(c.executed_at)}</td></tr>`).join("")}</tbody></table></div>`
        : `<div class="empty"><b>Henüz kalite kontrolü yok</b>Botlar <span class="mono">bot.check(...)</span> ile kontrol yazdıkça burada görünür.</div>`);
      $("#qf").onchange = (e) => { ui.status = e.target.value; loadTab(); };
    } else {
      const rows = await api("/api/quality/quarantine");
      body.innerHTML = rows.length ? `<div class="tbl-wrap"><table><thead><tr><th>Varlık</th><th>Neden</th><th>Anahtar</th><th>Kaynak</th><th>Ne zaman</th><th></th></tr></thead><tbody>
        ${rows.map((q) => `<tr><td>${esc(q.entity)}</td><td>${esc(q.reason)}</td><td class="mono" style="max-width:260px;overflow-wrap:anywhere">${esc(q.natural_key == null ? "–" : JSON.stringify(q.natural_key))}</td>
          <td>${esc(q.source_system || "–")}</td><td>${fmtDate(q.created_at)}</td><td><button class="btn btn-ghost btn-sm" data-q="${q.quarantine_id}">Çözüldü</button></td></tr>`).join("")}</tbody></table></div>`
        : `<div class="empty"><b>Karantinada bekleyen kayıt yok</b>Bot şüpheli bir kayıt bulursa (ör. aynı programdan iki farklı değer) burada görünür.</div>`;
      $$("[data-q]", body).forEach((b) => (b.onclick = () => modal(`<h2>Kayıt çözüldü mü?</h2><p class="muted">Ne yaptığınızı kısaca yazın; ekip arkadaşlarınız görecek.</p>
        <textarea class="input" id="res" placeholder="ör. Doğru değer YÖK Atlas sitesinden kontrol edildi, ikinci kayıt silindi"></textarea><div class="form-err" id="rerr"></div>
        <div class="acts"><button class="btn btn-ghost" data-close>Vazgeç</button><button class="btn btn-primary" id="yes">Çözüldü olarak işaretle</button></div>`,
        (m, close) => { $("#yes", m).onclick = (e) => busy(e.currentTarget, async () => {
          await api(`/api/quality/quarantine/${b.dataset.q}/resolve`, { method: "POST", body: { resolution: $("#res", m).value.trim() } });
          close(); toast("Kayıt çözüldü olarak işaretlendi."); loadSummary(); loadTab();
        }); })));
    }
  };
  await loadSummary();
  await loadTab();
}

/* ------------------------------------------------------------------ veri kapsamı */
async function pageCoverage(main) {
  const d = await api("/api/coverage");
  const bySource = {};
  d.tables.forEach((t) => (bySource[t.source] ||= []).push(t));
  main.innerHTML = `<div class="page-head"><div><h1>Veri kapsamı</h1><p>Veritabanında şu an ne kadar veri var ve her kaynak en son ne zaman geldi. Sayılar canlı olarak tablolardan okunuyor.</p></div></div>
    <div class="stack">
      <div class="grid g-2">${Object.entries(bySource).map(([src, rows]) => `<section class="card"><div class="card-head"><h2>${esc(src)}</h2></div>
        <div class="tbl-wrap"><table><tbody>${rows.map((t) => `<tr><td>${esc(t.label)}<div class="muted mono">${esc(t.table)}</div></td><td class="n" style="font-weight:700">${num(t.rows)}${t.last ? `<div class="muted" style="font-weight:400;font-size:.8rem">son: ${fmtDate(t.last)}</div>` : ""}</td></tr>`).join("")}</tbody></table></div></section>`).join("")}</div>
      <section class="card"><div class="card-head"><h2>Ham veri yüklemeleri (kaynağa göre)</h2></div>
        ${d.sources.length ? `<div class="tbl-wrap"><table><thead><tr><th>Kaynak</th><th class="n">Yükleme</th><th>Son yükleme</th><th>Son durum</th><th>Sürüm</th></tr></thead><tbody>
        ${d.sources.map((s) => `<tr><td class="mono">${esc(s.source_system)}</td><td class="n">${num(s.runs)}</td><td>${fmtDate(s.last_completed)}</td><td>${esc(s.last_status)}</td><td class="mono">${esc(s.last_version || "–")}</td></tr>`).join("")}</tbody></table></div>`
        : `<div class="empty">Henüz yükleme kaydı yok.</div>`}</section></div>`;
}

/* ------------------------------------------------------------------ bildirimler */
const RULES = {
  run_failed: ["Bot hata verince", "Bir çalışma hatayla ya da zaman aşımıyla biterse.", null],
  stalled: ["Bot takılınca", "Çalışan bot bu kadar dakikadır hiçbir şey yazmıyorsa.", "dakika"],
  schedule_missed: ["Planlı bot çalışmayınca", "Zamanlanmış bot bu kadar saattir başarıyla çalışmadıysa.", "saat"],
  low_records: ["Az kayıt gelince", "Kayıt sayısı botun ayarındaki \"beklenen en az kayıt\"tan azsa.", null],
  disk_usage: ["Disk dolunca", "Sunucu diski bu yüzdeyi geçince (günde en fazla bir e-posta).", "%"],
};
async function pageAlerts(main) {
  const d = await api("/api/alerts");
  const noEmail = d.recipients.filter((u) => u.receive_alerts && !u.email);
  main.innerHTML = `<div class="page-head"><div><h1>E-posta bildirimleri</h1><p>Bir şey ters gidince ekibe e-posta gider. Aynı sorun için tekrar tekrar e-posta atılmaz.</p></div>
      <button class="btn btn-ghost" id="testBtn">Deneme e-postası gönder</button></div>
    <div class="stack">
      ${d.smtp_configured ? `<div class="note info">${I.info}<div>E-postalar <b>${esc(d.smtp_from)}</b> adresinden gönderiliyor.</div></div>`
        : `<div class="note bad">${I.warn}<div><b>E-posta sunucusu ayarlı değil.</b> Bildirimler kaydediliyor ama gönderilemiyor. Sunucudaki <span class="mono">.env</span> dosyasına <span class="mono">ADMIN_SMTP_*</span> ayarlarını girin (kurulum belgesinde Gmail ile nasıl yapılacağı yazıyor).</div></div>`}
      <section class="card"><div class="card-head"><h2>Ne zaman e-posta gelsin?</h2></div><div class="stack" style="gap:14px" id="rules"></div></section>
      <section class="card"><div class="card-head"><h2>Kimlere gidecek?</h2><a href="#/ekip" class="btn btn-ghost btn-sm">Ekipte düzenle</a></div>
        ${noEmail.length ? `<div class="note" style="margin-bottom:12px">${I.warn}<div>${noEmail.map((u) => esc(u.full_name)).join(", ")} için e-posta adresi girilmemiş.</div></div>` : ""}
        <div class="row">${d.recipients.map((u) => `<span class="pill ${u.receive_alerts && u.email ? "s-idle" : "s-off"}">${esc(u.full_name)}${u.email ? ` · ${esc(u.email)}` : ""}${u.receive_alerts ? "" : " · almıyor"}</span>`).join("") || '<span class="muted">Henüz kimse yok.</span>'}</div></section>
      <section class="card"><div class="card-head"><h2>Gönderilenler</h2></div>
        ${d.sent.length ? `<div class="tbl-wrap"><table><thead><tr><th>Ne zaman</th><th>Konu</th><th>Bot</th><th>Kime</th><th>Durum</th></tr></thead><tbody>
        ${d.sent.map((a) => `<tr><td>${fmtDate(a.ts)}</td><td>${esc(a.subject)}</td><td>${a.bot_id ? `<a href="#/bot/${a.bot_id}">${esc(a.bot_name)}</a>` : "–"}</td><td>${num(a.recipients.length)} kişi</td>
          <td>${a.delivered ? pill("succeeded", "Gönderildi") : `<span title="${esc(a.error || "")}">${pill("failed", "Gönderilemedi")}</span><div class="muted" style="font-size:.78rem;max-width:260px">${esc(a.error || "")}</div>`}</td></tr>`).join("")}</tbody></table></div>`
        : `<div class="empty">Henüz bildirim gönderilmedi.</div>`}</section></div>`;
  $("#rules").innerHTML = d.rules.filter((r) => RULES[r.rule_key]).map((r) => {
    const [t, desc, unit] = RULES[r.rule_key];
    return `<div class="row" style="justify-content:space-between;border-bottom:1px dashed var(--line);padding-bottom:12px">
      <div style="flex:1;min-width:220px"><b>${t}</b><div class="muted" style="font-size:.88rem">${esc(desc)}</div></div>
      ${unit ? `<label class="row" style="gap:6px"><input class="input" type="number" min="1" style="width:90px" value="${esc(r.threshold ?? "")}" data-th="${r.rule_key}" aria-label="${t} sınırı"><span class="muted">${unit}</span></label>` : ""}
      <label class="switch"><input type="checkbox" data-rule="${r.rule_key}" ${r.enabled ? "checked" : ""}><span class="tr"></span><span>${r.enabled ? "Açık" : "Kapalı"}</span></label></div>`;
  }).join("");
  $$("[data-rule]").forEach((sw) => (sw.onchange = () => busy(null, async () => {
    try { await api(`/api/alerts/rules/${sw.dataset.rule}`, { method: "PUT", body: { enabled: sw.checked } }); }
    catch (e) { sw.checked = !sw.checked; throw e; }
    sw.parentElement.lastElementChild.textContent = sw.checked ? "Açık" : "Kapalı";
    toast("Kaydedildi.");
  })));
  $$("[data-th]").forEach((inp) => (inp.onchange = () => busy(null, async () => {
    await api(`/api/alerts/rules/${inp.dataset.th}`, { method: "PUT", body: { threshold: +inp.value } });
    toast("Sınır kaydedildi.");
  })));
  $("#testBtn").onclick = (e) => busy(e.currentTarget, async () => {
    const r = await api("/api/alerts/test", { method: "POST" });
    toast(`Deneme e-postası ${r.recipients.length} kişiye gönderildi.`);
    pageAlerts(main);
  }).finally(() => { if (!d.smtp_configured) pageAlerts(main); });
}

/* ------------------------------------------------------------------ ekip */
function auditTable(rows, emptyTxt) {
  if (!rows.length) return `<div class="empty">${esc(emptyTxt)}</div>`;
  const det = (d) => {
    if (!d || !Object.keys(d).length) return "";
    if (d["değişenler"]) return Object.entries(d["değişenler"]).map(([k, v]) => `${k}: ${JSON.stringify(v["önce"])} → ${JSON.stringify(v["sonra"])}`).join("; ");
    return Object.entries(d).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(", ");
  };
  return `<div class="tbl-wrap"><table><thead><tr><th>Ne zaman</th><th>Kim</th><th>Ne yaptı</th><th>Bot</th><th>Ayrıntı</th></tr></thead><tbody>
    ${rows.map((a) => `<tr><td style="white-space:nowrap">${fmtDate(a.ts)}</td><td>${esc(a.user_name || "–")}</td><td>${esc(a.action)}</td><td>${a.bot_id ? `<a href="#/bot/${a.bot_id}">${esc(a.bot_name)}</a>` : "–"}</td>
      <td class="mono muted" style="max-width:360px;overflow-wrap:anywhere;font-size:.78rem">${esc(det(a.details))}</td></tr>`).join("")}</tbody></table></div>`;
}

async function pageTeam(main) {
  const [users, audit] = await Promise.all([getUsers(true), api("/api/audit?limit=150")]);
  main.innerHTML = `<div class="page-head"><div><h1>Ekip ve işlem kaydı</h1><p>Panele girebilen herkes bütün botları yönetebilir. Kimin neyi ne zaman yaptığı aşağıda kayıtlı.</p></div>
      <button class="btn btn-primary" id="addUser">${I.plus} Ekip üyesi ekle</button></div>
    <div class="stack">
      <section class="card"><div class="tbl-wrap"><table><thead><tr><th>Kişi</th><th>Kullanıcı adı</th><th>E-posta</th><th>Bildirim</th><th>Son giriş</th><th></th></tr></thead><tbody>
      ${users.map((u) => `<tr style="${u.is_active ? "" : "opacity:.55"}"><td><span class="owner" style="color:var(--ink);font-size:.95rem"><span class="avatar">${esc(initials(u.full_name))}</span>${esc(u.full_name)}${u.user_id === state.me.user_id ? ' <span class="muted">(siz)</span>' : ""}</span></td>
        <td class="mono">${esc(u.username)}</td><td>${esc(u.email || "–")}</td><td>${u.receive_alerts ? "Alıyor" : "Almıyor"}</td><td>${u.last_login_at ? rel(u.last_login_at) : "hiç girmedi"}</td>
        <td><button class="btn btn-ghost btn-sm" data-u="${u.user_id}">Düzenle</button></td></tr>`).join("")}</tbody></table></div></section>
      <section class="card"><div class="card-head"><h2>İşlem kaydı</h2><span class="muted">son 150</span></div>${auditTable(audit, "Henüz kayıt yok.")}</section></div>`;
  const userModal = (u) => modal(`<h2>${u ? esc(u.full_name) : "Ekip üyesi ekle"}</h2>
    <form class="form" id="uf" novalidate style="margin-top:12px">
      ${u ? "" : `<div class="field"><label for="u_un">Kullanıcı adı</label><input class="input" id="u_un" autocapitalize="none" placeholder="ör. kullanıcı"></div>`}
      <div class="field"><label for="u_fn">Ad soyad</label><input class="input" id="u_fn" value="${esc(u?.full_name || "")}"></div>
      <div class="field"><label for="u_em">E-posta</label><input class="input" id="u_em" type="email" value="${esc(u?.email || "")}"></div>
      <div class="field"><label for="u_pw">${u ? "Yeni parola (değiştirmeyecekseniz boş bırakın)" : "Parola"}</label><input class="input" id="u_pw" type="password" autocomplete="new-password"><span class="hint">En az 10 karakter. Kişiye güvenli bir yoldan iletin; ilk girişte kendisi değiştirebilir.</span></div>
      <label class="switch"><input type="checkbox" id="u_al" ${!u || u.receive_alerts ? "checked" : ""}><span class="tr"></span>E-posta bildirimlerini alsın</label>
      ${u && u.user_id !== state.me.user_id ? `<label class="switch"><input type="checkbox" id="u_ac" ${u.is_active ? "checked" : ""}><span class="tr"></span>Hesap açık (kapalıysa giriş yapamaz)</label>` : ""}
      <div class="form-err" id="uerr" role="alert"></div>
      <div class="acts"><button type="button" class="btn btn-ghost" data-close>Vazgeç</button><button class="btn btn-primary" type="submit">${u ? "Kaydet" : "Ekle"}</button></div>
    </form>`, (m, close) => {
    $("#uf", m).onsubmit = async (e) => {
      e.preventDefault();
      const btn = e.submitter; btn.disabled = true;
      const body = { full_name: $("#u_fn", m).value.trim(), email: $("#u_em", m).value.trim(), receive_alerts: $("#u_al", m).checked };
      if ($("#u_pw", m).value) body.password = $("#u_pw", m).value;
      if ($("#u_ac", m)) body.is_active = $("#u_ac", m).checked;
      try {
        if (u) await api(`/api/users/${u.user_id}`, { method: "PATCH", body });
        else await api("/api/users", { method: "POST", body: { ...body, username: $("#u_un", m).value.trim().toLowerCase() } });
        close(); toast(u ? "Kaydedildi." : "Ekip üyesi eklendi."); pageTeam(main);
      } catch (err) { $("#uerr", m).textContent = err.message; btn.disabled = false; }
    };
  });
  $("#addUser").onclick = () => userModal(null);
  $$("[data-u]").forEach((b) => (b.onclick = () => userModal(users.find((u) => u.user_id === +b.dataset.u))));
}

/* ------------------------------------------------------------------ başlat */
async function boot() {
  try {
    state.me = await api("/api/me");
  } catch {
    return renderLogin();
  }
  $("#app").innerHTML = "";
  route();
}
boot();

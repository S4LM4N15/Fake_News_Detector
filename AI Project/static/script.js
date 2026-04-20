/* =========================================================
   script.js — Fake News Detector Frontend Logic
   ========================================================= */

"use strict";

// ── DOM refs ────────────────────────────────────────────
const queryInput     = document.getElementById("query-input");
const checkBtn       = document.getElementById("check-btn");
const loadingSection = document.getElementById("loading-section");
const errorSection   = document.getElementById("error-section");
const errorMsg       = document.getElementById("error-msg");
const resultSection  = document.getElementById("result-section");

// Result display elements
const verdictBadge   = document.getElementById("verdict-badge");
const scoreNumber    = document.getElementById("score-number");
const progressBar    = document.getElementById("progress-bar");
const signalsGrid    = document.getElementById("signals-grid");
const sourcesList    = document.getElementById("sources-list");
const sourcesCount   = document.getElementById("sources-count");
const searchTimeTxt  = document.getElementById("search-time");

// Loading steps
const steps = [
  document.getElementById("step-1"),
  document.getElementById("step-2"),
  document.getElementById("step-3"),
];

// ── Sample queries (hint chips) ─────────────────────────
document.querySelectorAll(".hint-chip").forEach(chip => {
  chip.addEventListener("click", () => {
    queryInput.value = chip.dataset.query;
    queryInput.focus();
  });
});

// ── Enter key support ───────────────────────────────────
queryInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !checkBtn.disabled) runCheck();
});

// ── Main button ─────────────────────────────────────────
checkBtn.addEventListener("click", runCheck);

async function runCheck() {
  const query = queryInput.value.trim();
  if (!query) {
    queryInput.focus();
    shake(queryInput);
    return;
  }

  // Reset UI
  hideAll();
  setLoading(true);
  advanceStep(0);

  try {
    // Simulate progressive steps for UX
    const stepTimer1 = setTimeout(() => advanceStep(1), 1200);
    const stepTimer2 = setTimeout(() => advanceStep(2), 2400);

    const res = await fetch("/api/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    clearTimeout(stepTimer1);
    clearTimeout(stepTimer2);
    advanceStep(2);

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || `Server error ${res.status}`);
    }

    const data = await res.json();

    // Small delay so loading feels intentional
    await sleep(400);
    setLoading(false);
    renderResult(data);

  } catch (err) {
    setLoading(false);
    showError(err.message || "Could not reach the server. Is Flask running?");
  }
}

// ── Render result ───────────────────────────────────────
function renderResult(data) {
  // Verdict badge
  const classes = { REAL: "real", LIKELY_REAL: "likely", FAKE: "fake" };
  verdictBadge.className = "verdict-badge " + (classes[data.verdict] || "fake");
  verdictBadge.innerHTML = `<span>${data.verdict_emoji}</span> ${data.verdict_label}`;

  // Score
  animateCounter(scoreNumber, 0, data.score, 1000);

  // Progress bar colour
  const barColor = data.verdict_color || "#8b5cf6";
  progressBar.style.background = `linear-gradient(90deg, ${barColor}aa, ${barColor})`;
  // Animate width after next frame
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      progressBar.style.width = data.score + "%";
    });
  });

  // Search time
  if (searchTimeTxt && data.search_time_seconds !== undefined) {
    searchTimeTxt.textContent = `Search completed in ${data.search_time_seconds}s`;
  }

  // Signals
  renderSignals(data.breakdown);

  // Sources
  renderSources(data.matched_sources || []);

  resultSection.classList.add("visible");
}

// ── Signals breakdown ───────────────────────────────────
const SIGNAL_ICONS = {
  trusted_domain:     { pass: "🔒", fail: "🔓" },
  multiple_sources:   { pass: "📰", fail: "📄" },
  recent_publication: { pass: "🗓️",  fail: "⏳" },
  headline_match:     { pass: "🎯", fail: "🔍" },
};

function renderSignals(breakdown) {
  if (!breakdown) return;
  signalsGrid.innerHTML = "";

  Object.entries(breakdown).forEach(([key, sig]) => {
    const icons = SIGNAL_ICONS[key] || { pass: "✅", fail: "❌" };
    const icon  = sig.passed ? icons.pass : icons.fail;
    const pts   = sig.points > 0 ? `+${sig.points}` : "0";
    const cls   = sig.points > 0 ? "pass" : "fail";

    const el = document.createElement("div");
    el.className = "signal-item";
    el.innerHTML = `
      <div class="signal-icon">${icon}</div>
      <div class="signal-info">
        <div class="signal-name">${sig.label}</div>
        <div class="signal-detail">${sig.detail}</div>
      </div>
      <div class="signal-pts ${cls}">${pts}/${sig.max}</div>
    `;
    signalsGrid.appendChild(el);
  });
}

// ── Sources list ────────────────────────────────────────
function renderSources(sources) {
  sourcesList.innerHTML = "";

  const visible = sources.filter(s => s.url && s.title);
  sourcesCount.textContent = `${visible.length} source${visible.length !== 1 ? "s" : ""}`;

  if (!visible.length) {
    sourcesList.innerHTML = `
      <div class="no-sources">
        <div style="font-size:2rem;margin-bottom:.5rem">🔎</div>
        No sources found for this query.
      </div>`;
    return;
  }

  visible.forEach((src, i) => {
    const card = document.createElement("a");
    card.className = "source-card" + (src.is_trusted ? " trusted" : "");
    card.href   = src.url || "#";
    card.target = "_blank";
    card.rel    = "noopener noreferrer";
    card.style.animationDelay = `${i * 60}ms`;

    const domainBadgeClass = src.is_trusted ? "source-domain-badge trusted" : "source-domain-badge";
    const trustedLabel     = src.is_trusted ? "✓ Trusted" : src.domain || "Unknown";
    const dateHtml         = src.date
      ? `<span>📅 ${src.date}</span>` : "";

    card.innerHTML = `
      <div class="${domainBadgeClass}">${trustedLabel}</div>
      <div class="source-info">
        <div class="source-title">${escHtml(src.title)}</div>
        <div class="source-meta">
          <span>🌐 ${escHtml(src.domain || "")}</span>
          ${dateHtml}
        </div>
      </div>
      <div style="color:var(--text-muted);font-size:1.1rem;flex-shrink:0">↗</div>
    `;
    sourcesList.appendChild(card);
  });
}

// ── Loading step manager ────────────────────────────────
let currentStep = -1;
function advanceStep(idx) {
  steps.forEach((s, i) => {
    s.classList.remove("active", "done");
    if (i < idx)  s.classList.add("done");
    if (i === idx) s.classList.add("active");
  });
  currentStep = idx;
}

// ── UI helpers ──────────────────────────────────────────
function setLoading(on) {
  checkBtn.disabled = on;
  if (on) {
    checkBtn.innerHTML = `<span class="btn-icon">⏳</span> Checking…`;
    currentStep = -1;
    advanceStep(0);
    loadingSection.classList.add("visible");
  } else {
    checkBtn.innerHTML = `<span class="btn-icon">🔍</span> Check News`;
    loadingSection.classList.remove("visible");
  }
}

function hideAll() {
  resultSection.classList.remove("visible");
  errorSection.classList.remove("visible");
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorSection.classList.add("visible");
}

function animateCounter(el, from, to, duration) {
  const start = performance.now();
  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(from + (to - from) * eased);
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function shake(el) {
  el.animate([
    { transform: "translateX(0)" },
    { transform: "translateX(-8px)" },
    { transform: "translateX(8px)" },
    { transform: "translateX(-4px)" },
    { transform: "translateX(4px)" },
    { transform: "translateX(0)" },
  ], { duration: 400, easing: "ease-in-out" });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

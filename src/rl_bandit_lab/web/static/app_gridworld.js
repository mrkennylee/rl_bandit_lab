// Gridworld driver: create a run, then loop POST /sweep (auto or manual),
// animating the value heatmap + greedy-policy arrows until Bellman convergence.
(() => {
  const $ = (id) => document.getElementById(id);
  const GLYPH = { U: "↑", D: "↓", L: "←", R: "→" };

  let runId = null;
  let rows = 0, cols = 0, terminals = {}, walls = new Set();
  let playing = false, timer = null, converged = false, lastFormulaKey = null;

  const intervalMs = () => 1000 / +$("speed").value;

  function renderFormula(formula) {
    if (!formula || formula.key === lastFormulaKey) return;
    lastFormulaKey = formula.key;
    $("formula-title").textContent = formula.title;
    katex.render(formula.latex, $("formula-main"), { displayMode: true, throwOnError: false });
    $("formula-explain").textContent = formula.plain_explain || "";
    const container = $("formula-steps");
    container.innerHTML = "";
    formula.steps.forEach((s) => {
      const wrap = document.createElement("div");
      wrap.className = "dstep";
      const math = document.createElement("div");
      katex.render(s.latex, math, { displayMode: true, throwOnError: false });
      const note = document.createElement("p");
      note.className = "muted";
      note.textContent = s.note;
      wrap.append(math, note);
      container.appendChild(wrap);
    });
  }

  function buildGrid() {
    const grid = $("grid");
    grid.innerHTML = "";
    grid.style.gridTemplateColumns = `repeat(${cols}, 92px)`;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const k = `${r},${c}`;
        const cell = document.createElement("div");
        cell.className = "cell";
        cell.id = `cell-${k}`;
        if (walls.has(k)) {
          cell.classList.add("wall");
          cell.textContent = "▩";
        } else if (k in terminals) {
          cell.classList.add("terminal", terminals[k] > 0 ? "term-pos" : "term-neg");
          cell.innerHTML = `<div class="val">${terminals[k] > 0 ? "+1" : "−1"}</div>`;
        } else {
          cell.innerHTML = `<div class="arrow"></div><div class="val">0.00</div>`;
        }
        grid.appendChild(cell);
      }
    }
  }

  function valColor(v) {
    const t = Math.max(-1, Math.min(1, v));
    return t >= 0
      ? `rgba(56,211,159,${0.12 + 0.5 * t})`
      : `rgba(239,100,97,${0.12 + 0.5 * -t})`;
  }

  function render(res) {
    $("sweep-no").textContent = res.sweep_no;
    $("delta").textContent = res.max_delta.toExponential(1);
    converged = res.converged;
    const badge = $("conv");
    badge.textContent = converged ? "converged ✓" : "iterating";
    badge.classList.toggle("ok", converged);
    for (const [k, v] of Object.entries(res.values)) {
      if (walls.has(k) || k in terminals) continue;
      const cell = $(`cell-${k}`);
      if (!cell) continue;
      cell.style.background = valColor(v);
      cell.querySelector(".val").textContent = v.toFixed(2);
      const action = res.policy[k];
      cell.querySelector(".arrow").textContent = action ? GLYPH[action] : "";
    }
    renderFormula(res.formula);
  }

  async function sweep() {
    const resp = await fetch(`/runs/${runId}/sweep`, { method: "POST" });
    if (!resp.ok) return;
    render(await resp.json());
    if (converged) stop();
  }

  function setPlaying(state) {
    playing = state;
    $("play").disabled = state;
    $("pause").disabled = !state;
  }

  function play() {
    if (converged) return;
    setPlaying(true);
    const tick = async () => {
      if (!playing) return;
      await sweep();
      if (playing && !converged) timer = setTimeout(tick, intervalMs());
    };
    tick();
  }

  function stop() {
    playing = false;
    clearTimeout(timer);
    setPlaying(false);
  }

  async function init() {
    const resp = await fetch("/runs/gridworld", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    const data = await resp.json();
    runId = data.run_id;
    rows = data.rows;
    cols = data.cols;
    terminals = data.terminals;
    walls = new Set(data.walls);
    converged = false;
    lastFormulaKey = null;
    buildGrid();
    $("sweep-no").textContent = "0";
    $("delta").textContent = "—";
    $("conv").textContent = "iterating";
    $("conv").classList.remove("ok");
  }

  $("sweep").addEventListener("click", () => { stop(); sweep(); });
  $("play").addEventListener("click", play);
  $("pause").addEventListener("click", stop);
  $("speed").addEventListener("input", () => {
    $("speed-label").textContent = `${$("speed").value} / s`;
  });
  $("restart").addEventListener("click", () => { stop(); init(); });

  init();
})();

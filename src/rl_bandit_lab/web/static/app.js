// Bandit lab client: drives the SSE auto-play, animates lever pulls, updates the
// Q-value bars + "why this arm" panel, and renders the formula/derivation via KaTeX.
(() => {
  const lab = document.querySelector(".lab");
  const runId = lab.dataset.runId;
  const nArms = +lab.dataset.nArms;
  const $ = (id) => document.getElementById(id);

  let es = null;
  let playing = false;
  let lastFormulaKey = null;
  let speedTimer = null;

  const intervalSeconds = () => 1 / +$("speed").value;

  function renderFormula(formula) {
    if (!formula || formula.key === lastFormulaKey) return; // formula is stable per algo
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

  function pullLever(arm, reward) {
    const machine = $(`machine-${arm}`);
    if (!machine) return;
    machine.classList.remove("pull");
    void machine.offsetWidth; // restart the CSS animation
    machine.classList.add("pull");
    const reel = machine.querySelector(".reel");
    reel.textContent = reward === 1 ? "💰" : "✖";
    reel.classList.toggle("win", reward === 1);
    reel.classList.toggle("lose", reward === 0);
  }

  function updateMachines(data) {
    for (let i = 0; i < nArms; i++) {
      const machine = $(`machine-${i}`);
      if (!machine) continue;
      const q = data.q_values[i] ?? 0;
      const n = data.counts[i] ?? 0;
      machine.querySelector(".qfill").style.height = `${Math.round(q * 100)}%`;
      machine.querySelector(".qval").textContent = `Q=${q.toFixed(2)} · n=${n}`;
      machine.classList.toggle("chosen", i === data.arm_chosen);
    }
  }

  function updateWhy(data) {
    const why = $("why-text");
    why.textContent = data.explanation.text;
    why.className = "why-text " + data.reason_code;
    const tbody = $("why-table").querySelector("tbody");
    tbody.innerHTML = "";
    data.scores.forEach((score, i) => {
      const tr = document.createElement("tr");
      if (i === data.arm_chosen) tr.className = "chosen";
      const shown = score === null || score === undefined ? "∞" : (+score).toFixed(3);
      tr.innerHTML = `<td>Machine ${i}</td><td>${shown}</td>`;
      tbody.appendChild(tr);
    });
  }

  function onStep(rawData) {
    const data = JSON.parse(rawData);
    $("step-no").textContent = data.step_no;
    pullLever(data.arm_chosen, data.reward);
    updateMachines(data);
    updateWhy(data);
    renderFormula(data.formula);
  }

  function setPlaying(state) {
    playing = state;
    $("play").disabled = state;
    $("pause").disabled = !state;
    $("step").disabled = state;
  }

  function startStream() {
    stopStream();
    es = new EventSource(`/runs/${runId}/stream?interval=${intervalSeconds()}&max_steps=100000`);
    es.addEventListener("step", (e) => onStep(e.data));
    es.addEventListener("done", stopStream);
    setPlaying(true);
  }

  function stopStream() {
    if (es) { es.close(); es = null; }
    setPlaying(false);
  }

  $("play").addEventListener("click", startStream);
  $("pause").addEventListener("click", stopStream);
  $("step").addEventListener("click", async () => {
    stopStream();
    const resp = await fetch(`/runs/${runId}/step`, { method: "POST" });
    if (resp.ok) onStep(await resp.text());
  });
  $("speed").addEventListener("input", () => {
    $("speed-label").textContent = `${$("speed").value} / s`;
    if (playing) { clearTimeout(speedTimer); speedTimer = setTimeout(startStream, 150); }
  });
})();

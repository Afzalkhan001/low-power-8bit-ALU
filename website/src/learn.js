/* ================= Start-here demos ================= */
(function learn() {
  const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, Math.round(+x || 0)));
  const sp = (b) => `<span class="b${b}">${b}</span>`;

  /* ---- 2. binary converter */
  let bv = 45;
  const binEl = $("#w-bin");
  binEl.innerHTML = [7, 6, 5, 4, 3, 2, 1, 0].map((i) => `<button class="bitbtn" data-i="${i}" aria-pressed="false" aria-label="bit ${i}, worth ${1 << i}"><span>0</span><small>${1 << i}</small></button>`).join("");
  function drawBin() {
    binEl.querySelectorAll("button").forEach((b) => { const on = (bv >> +b.dataset.i) & 1; b.setAttribute("aria-pressed", on ? "true" : "false"); b.firstElementChild.textContent = on; });
    const parts = [7, 6, 5, 4, 3, 2, 1, 0].filter((i) => (bv >> i) & 1).map((i) => 1 << i);
    $("#w-bin-out").innerHTML = `${bitsHTML(bin(bv))}<br>= ${parts.length ? parts.join(" + ") : "0"} = <b>${bv}</b><br><span class="small muted">hex ${hex(bv)} · ${bin(bv).slice(0, 4)} → ${hex(bv >> 4, 1)}, ${bin(bv).slice(4)} → ${hex(bv & 15, 1)}</span>`;
    const n = $("#w-bin-num"); if (document.activeElement !== n) n.value = bv;
  }
  binEl.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { bv ^= 1 << +b.dataset.i; drawBin(); } });
  $("#w-bin-num").addEventListener("input", (e) => { bv = clamp(e.target.value, 0, 255); drawBin(); });
  drawBin();

  /* ---- 3. addition */
  const colTable = (rows) => `<table class="cols">${rows.join("")}</table>`;
  const trow = (lab, bits, dec, cls = "") => `<tr class="${cls}"><td class="lab">${lab}</td>${bits.map((b) => `<td>${b === "" ? "" : sp(b)}</td>`).join("")}<td class="dec">${dec}</td></tr>`;
  function drawAdd() {
    const a = clamp($("#w-add-a").value, 0, 255), b = clamp($("#w-add-b").value, 0, 255);
    const carries = []; let c = 0;
    for (let i = 0; i < 8; i++) { carries[i] = c; const s = ((a >> i) & 1) + ((b >> i) & 1) + c; c = s >> 1; }
    const sum = a + b, cout = sum >> 8;
    const cin = [7, 6, 5, 4, 3, 2, 1, 0].map((i) => carries[i]);
    $("#w-add").innerHTML = colTable([
      `<tr><th></th>${["C", 7, 6, 5, 4, 3, 2, 1, 0].map((h) => `<th>${h === "C" ? "C" : "b" + h}</th>`).join("")}<th></th></tr>`,
      trow("carry", ["", ...cin], ""),
      trow("A", ["", ...bin(a)], `= ${a}`),
      trow("+ B", ["", ...bin(b)], `= ${b}`),
      trow("Y", [cout, ...bin(sum & 255)], `= ${sum & 255}${cout ? "  (C=1, real answer " + sum + ")" : ""}`, "sum")]);
    $("#w-add-note").textContent = cout
      ? `The answer ${sum} is bigger than 255, so the 9th bit comes out as C = 1 and Y keeps only the lower 8 bits.`
      : `A 1 in the carry row means that column received a carry from the column to its right.`;
  }
  ["#w-add-a", "#w-add-b"].forEach((s) => $(s).addEventListener("input", drawAdd));
  drawAdd();

  /* ---- 4. two's complement */
  function drawNeg() {
    const x = clamp($("#w-neg-x").value, 1, 127);
    const inv = ~x & 255, neg = (inv + 1) & 255;
    $("#w-neg").innerHTML = colTable([
      trow("x", [...bin(x)], `= +${x}`),
      trow("flip bits", [...bin(inv)], `= NOT x`),
      trow("+ 1", [..."00000001"], ""),
      trow("−x", [...bin(neg)], `= −${x}`, "sum")]);
    $("#w-neg-note").innerHTML = `Check: ${bin(x)} + ${bin(neg)} = 1 00000000. The 9th bit falls off, leaving 0, so the second number really is −${x}. Bit 7 of −${x} is 1, which marks it negative.`;
  }
  $("#w-neg-x").addEventListener("input", drawNeg);
  drawNeg();

  /* ---- 5. multiplication 4x4 */
  function drawMul() {
    const a = clamp($("#w-mul-a").value, 0, 15), b = clamp($("#w-mul-b").value, 0, 15);
    const rows = [`<tr><th></th>${[7, 6, 5, 4, 3, 2, 1, 0].map((h) => `<th>${1 << h}</th>`).join("")}<th></th></tr>`];
    rows.push(trow("A", ["", "", "", "", ...bin(a, 4)], `= ${a}`));
    rows.push(trow("× B", ["", "", "", "", ...bin(b, 4)], `= ${b}`, "sum"));
    for (let i = 0; i < 4; i++) {
      const bi = (b >> i) & 1, pp = bi ? a : 0;
      const cells = []; for (let col = 7; col >= 0; col--) { const j = col - i; cells.push(j >= 0 && j < 4 ? String((pp >> j) & 1) : ""); }
      rows.push(trow(`b${i}=${bi} → ${bi ? "A" : "0"}`, cells, bi ? `= ${a} × ${1 << i}` : "= 0"));
    }
    rows.push(trow("product", [...bin(a * b, 8)], `= ${a * b}`, "sum"));
    $("#w-mul").innerHTML = colTable(rows);
  }
  ["#w-mul-a", "#w-mul-b"].forEach((s) => $(s).addEventListener("input", drawMul));
  drawMul();

  /* ---- 6. gate playground */
  const GATES = { AND: (a, b) => a & b, OR: (a, b) => a | b, NOT: (a) => a ^ 1, XOR: (a, b) => a ^ b, NAND: (a, b) => (a & b) ^ 1, NOR: (a, b) => (a | b) ^ 1, XNOR: (a, b) => (a ^ b) ^ 1 };
  const gs = { g: "AND", a: 0, b: 0 };
  $("#w-gate-pick").innerHTML = Object.keys(GATES).map((g) => `<button role="tab" data-g="${g}" aria-selected="${g === gs.g}">${g}</button>`).join("");
  function drawGate() {
    const f = GATES[gs.g], one = gs.g === "NOT";
    document.querySelectorAll("#w-gate-pick button").forEach((b) => b.setAttribute("aria-selected", b.dataset.g === gs.g ? "true" : "false"));
    for (const k of ["a", "b"]) { const el = $("#w-gate-" + k); el.setAttribute("aria-pressed", gs[k] ? "true" : "false"); el.firstElementChild.textContent = gs[k]; }
    $("#w-gate-b").hidden = one;
    const y = f(gs.a, gs.b);
    const led = $("#w-gate-y"); led.textContent = y; led.classList.toggle("on", !!y);
    const combos = one ? [[0], [1]] : [[0, 0], [0, 1], [1, 0], [1, 1]];
    $("#w-gate-tt").innerHTML = `<table class="tt"><tr><th>A</th>${one ? "" : "<th>B</th>"}<th>${gs.g}</th></tr>` +
      combos.map(([a, b]) => `<tr class="${a === gs.a && (one || b === gs.b) ? "cur" : ""}"><td>${a}</td>${one ? "" : `<td>${b}</td>`}<td>${sp(f(a, b ?? 0))}</td></tr>`).join("") + "</table>";
  }
  $("#w-gate-pick").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { gs.g = b.dataset.g; drawGate(); } });
  $("#w-gate-a").addEventListener("click", () => { gs.a ^= 1; drawGate(); });
  $("#w-gate-b").addEventListener("click", () => { gs.b ^= 1; drawGate(); });
  drawGate();

  /* ---- 7. CMOS inverter */
  let ia = 0;
  function drawInv() {
    const { mos, rail } = window.SCHEM;
    const pOn = ia === 0, nOn = ia === 1, y = ia ^ 1;
    let s = rail(80, 160, 20, "VDD = 1") + rail(80, 160, 210, "GND = 0");
    s += `<line x1="120" y1="20" x2="120" y2="42" class="${pOn ? "pathon" : "w"}"/>`;
    s += `<g class="${pOn ? "on" : ""}">${mos(120, 66, true, "a=" + ia)}</g>`;
    s += `<line x1="120" y1="90" x2="120" y2="140" class="${pOn || nOn ? "pathon" : "w"}"/>`;
    s += `<g class="${nOn ? "on" : ""}">${mos(120, 164, false, "a=" + ia)}</g>`;
    s += `<line x1="120" y1="188" x2="120" y2="210" class="${nOn ? "pathon" : "w"}"/>`;
    s += `<line x1="120" y1="115" x2="180" y2="115" class="pathon" style="stroke:${y ? "var(--hi)" : "var(--lo)"}"/><circle cx="120" cy="115" r="3" class="ink"/>`;
    s += `<text x="186" y="112" class="gl" style="fill:var(--hi)">y = ${y}</text>`;
    s += `<text x="132" y="62" class="nl">PMOS ${pOn ? "ON" : "off"}</text><text x="132" y="160" class="nl">NMOS ${nOn ? "ON" : "off"}</text>`;
    $("#w-inv").innerHTML = s;
    $("#w-inv-btn").textContent = `Input a = ${ia} · click to flip`;
    $("#w-inv-note").textContent = pOn
      ? "a = 0 turns the PMOS on and the NMOS off. The output connects to VDD, so y = 1."
      : "a = 1 turns the NMOS on and the PMOS off. The output connects to ground, so y = 0.";
  }
  $("#w-inv-btn").addEventListener("click", () => { ia ^= 1; drawInv(); });
  drawInv();

  /* ---- 8. full adder + mux */
  const fa = { a: 0, b: 0, c: 0 }, mx = { d0: 0, d1: 1, s: 0 };
  function drawFA() {
    document.querySelectorAll("[data-fa]").forEach((b) => { const v = fa[b.dataset.fa]; b.setAttribute("aria-pressed", v ? "true" : "false"); b.firstElementChild.textContent = v; });
    const sum = fa.a + fa.b + fa.c, s = sum & 1, co = sum >> 1;
    $("#w-fa-s").textContent = s; $("#w-fa-s").classList.toggle("on", !!s);
    $("#w-fa-co").textContent = co; $("#w-fa-co").classList.toggle("on", !!co);
    $("#w-fa-note").textContent = `${fa.a} + ${fa.b} + ${fa.c} = ${sum}, which is ${co}${s} in binary: Cout = ${co}, S = ${s}.`;
    document.querySelectorAll("[data-mx]").forEach((b) => { const v = mx[b.dataset.mx]; b.setAttribute("aria-pressed", v ? "true" : "false"); b.firstElementChild.textContent = v; });
    const y = mx.s ? mx.d1 : mx.d0;
    $("#w-mx-y").textContent = y; $("#w-mx-y").classList.toggle("on", !!y);
    $("#w-mx-note").textContent = `sel = ${mx.s}, so the output copies d${mx.s} = ${y}.`;
  }
  document.querySelectorAll("[data-fa]").forEach((b) => b.addEventListener("click", () => { fa[b.dataset.fa] ^= 1; drawFA(); }));
  document.querySelectorAll("[data-mx]").forEach((b) => b.addEventListener("click", () => { mx[b.dataset.mx] ^= 1; drawFA(); }));
  drawFA();

  /* ---- 9. ops table */
  const unitOf = (op) => (op <= 3 || op === 15 ? "Arithmetic" : op === 4 ? "Multiplier" : op <= 11 ? "Logic" : "Shifter");
  $("#w-ops").innerHTML = `<tr><th class="m">Opcode</th><th>Op</th><th>Block</th></tr>` +
    ALU.OPCODES.map(([c, m], op) => `<tr><td class="m">${c}</td><td class="m"><b>${m}</b></td><td>${unitOf(op)}</td></tr>`).join("");

  /* ---- 10. power calculator */
  function drawP() {
    const a = +$("#w-p-a").value, C = +$("#w-p-c").value, V = +$("#w-p-v").value, f = +$("#w-p-f").value;
    $("#w-p-a-v").textContent = a.toFixed(2); $("#w-p-c-v").textContent = C + " fF"; $("#w-p-v-v").textContent = V.toFixed(2) + " V"; $("#w-p-f-v").textContent = f + " MHz";
    const P = a * C * 1e-15 * V * V * f * 1e6 * 1e6; // µW
    const P10 = a * C * 1e-15 * 1 * f * 1e6 * 1e6;
    $("#w-p-out").innerHTML = `P = ${a.toFixed(2)} × ${C} fF × ${V.toFixed(2)}² × ${f} MHz<br>= <b>${P.toFixed(2)} µW</b><br><span class="small muted">${V === 1 ? "Move V to see the V² effect." : `At 1.00 V it would be ${P10.toFixed(2)} µW, so this voltage ${V < 1 ? "saves" : "costs"} ${Math.abs(100 * (1 - V * V)).toFixed(0)}%.`}</span>`;
  }
  ["#w-p-a", "#w-p-c", "#w-p-v", "#w-p-f"].forEach((s) => $(s).addEventListener("input", drawP));
  drawP();

  /* ---- 12. quiz */
  const Q = [
    ["What is 00001010 in decimal?", "8 + 2 = 10."],
    ["What is the largest number 8 bits can hold, and why?", "255, because 128+64+32+16+8+4+2+1 = 255. Counting 0, that is 256 values."],
    ["What do you get for 1 + 1 in one binary column?", "Write 0 and carry 1, because 1 + 1 = 2 = 10 in binary."],
    ["How does the ALU compute 9 − 4 with an adder?", "9 + (NOT 4) + 1. NOT 4 = 11111011, and adding 1 makes −4 = 11111100. 00001001 + 11111100 = 1 00000101 = 5, and the carry C = 1 means no borrow."],
    ["Which transistor conducts when its gate is 0?", "The PMOS. The NMOS conducts when its gate is 1."],
    ["Why does CMOS use almost no power when nothing changes?", "In every gate only the pull-up or the pull-down network is on, so there is no direct path from VDD to ground. Energy is used mainly when wires switch."],
    ["In P = α·C·V²·f, which change saves the most: halving α or lowering V from 1.0 to 0.8 V?", "Halving α saves 50%. Lowering V to 0.8 V saves 36% (0.8² = 0.64). Here halving α wins, but both help, and the savings multiply when you do both."],
    ["What does operand isolation do?", "It feeds zeros to the blocks that are not being used, so their wires do not flip and they use almost no dynamic energy."],
    ["What are the flags after CMP with A = 20 and B = 20?", "Z = 1 because 20 − 20 = 0, C = 1 because there is no borrow, N = 0, V = 0, and WE = 0 because CMP does not store a result."],
    ["What is a netlist?", "A text description of a circuit that lists every component and the wires (nodes) it connects to. Spectre simulates netlists."],
  ];
  $("#quiz").innerHTML = Q.map(([q, a], i) => `<details><summary>${i + 1}. ${q}</summary><p>${a}</p></details>`).join("");

  /* ---- 13. glossary */
  const G = [
    ["ALU", "Arithmetic Logic Unit: the part of a processor that does math and logic operations."],
    ["Bit", "One binary digit, 0 or 1. In a chip, 0 V or the supply voltage."],
    ["Byte", "8 bits. Holds 0 to 255."],
    ["MSB / LSB", "Most / least significant bit: the leftmost (bit 7, worth 128) and rightmost (bit 0, worth 1) bit."],
    ["Hexadecimal", "Base 16, written 0–9 and A–F. One hex digit = 4 bits."],
    ["Two's complement", "How chips store negative numbers: flip all bits and add 1."],
    ["Opcode", "The code that selects the operation. Ours is 4 bits, so 16 operations."],
    ["Operand", "An input number to an operation. Our operands are A and B."],
    ["Carry", "The bit passed to the next column when a column's sum is 2 or 3."],
    ["Ripple carry", "An adder where each column waits for the carry from the column before it."],
    ["Full adder", "A circuit that adds three bits and gives a sum bit and a carry bit."],
    ["Mirror adder", "A 28-transistor CMOS full adder whose pull-up network mirrors its pull-down network."],
    ["Partial product", "One row in binary long multiplication: A ANDed with one bit of B."],
    ["Array multiplier", "A multiplier built as a grid of AND gates and full adders."],
    ["Flag", "A one-bit status output: C carry, Z zero, N negative, V overflow."],
    ["Overflow", "When a signed result does not fit in −128 to 127."],
    ["Logic gate", "A circuit that computes one output bit from input bits by a fixed rule."],
    ["Truth table", "A table listing a gate's output for every input combination."],
    ["Multiplexer (mux)", "A selector: a select input chooses which data input reaches the output."],
    ["Decoder", "A circuit that turns a binary code into one active output wire."],
    ["MOSFET", "Metal-Oxide-Semiconductor Field-Effect Transistor: a voltage-controlled switch."],
    ["NMOS / PMOS", "NMOS conducts when its gate is 1. PMOS conducts when its gate is 0."],
    ["CMOS", "Complementary MOS: logic built from NMOS and PMOS pairs. Uses power mostly when switching."],
    ["Transmission gate", "An NMOS and PMOS in parallel used as a switch that passes a signal both ways."],
    ["Gate / source / drain", "The control terminal and the two switched terminals of a MOSFET."],
    ["W / L", "Transistor width and length. Ours: L = 45 nm, W = 120 nm (NMOS) or 240 nm (PMOS)."],
    ["VDD / GND", "The supply voltage (logic 1, here 1.0 V) and ground (logic 0, 0 V)."],
    ["Dynamic power", "Power used when wires switch: P = α·C·V²·f."],
    ["Leakage", "Small current that flows even when nothing switches. Spectre includes it."],
    ["Switching activity (α)", "How often a wire flips per clock cycle."],
    ["Capacitance (C)", "How much charge a wire holds per volt. Bigger C means more energy per flip."],
    ["Glitch", "An unwanted temporary flip before a signal settles. It wastes energy."],
    ["Operand isolation", "Holding the inputs of idle blocks at 0 so they do not switch."],
    ["Propagation delay", "How long the output takes to respond after an input changes."],
    ["Critical path", "The slowest path through the circuit. It sets the maximum speed."],
    ["VLSI", "Very Large Scale Integration: designing chips with very many transistors."],
    ["PDK", "Process Design Kit: the foundry's transistor models and rules. We use gpdk045."],
    ["Schematic", "A circuit drawing made of symbols and wires."],
    ["Netlist", "A text file listing every component and the nodes it connects to."],
    ["Node / net", "A wire, or any set of points that are connected together."],
    ["Subcircuit (subckt)", "A reusable circuit block in a netlist, like a function in code."],
    ["Virtuoso", "Cadence's tool for drawing schematics and layouts."],
    ["Spectre", "Cadence's circuit simulator."],
    ["ADE Explorer", "The Virtuoso window for setting up and running simulations."],
    ["Transient analysis", "A simulation of voltages over time."],
    ["Testbench", "The circuit that feeds inputs to the design and loads its outputs."],
    ["PWL source", "Piece-wise linear voltage source: a voltage defined by a list of (time, value) points."],
    ["Waveform", "A plot of a signal against time."],
    ["OCEAN", "Cadence's scripting language for running simulations and measuring results."],
    ["Golden model", "A simple trusted reference (here, Python integer math) that the design is checked against."],
  ];
  function drawGl() {
    const q = $("#gl-q").value.trim().toLowerCase();
    const rows = G.filter(([t, d]) => !q || t.toLowerCase().includes(q) || d.toLowerCase().includes(q));
    $("#gl").innerHTML = `<tr><th>Term</th><th>Meaning</th></tr>` + (rows.length ? rows.map(([t, d]) => `<tr><td>${t}</td><td>${d}</td></tr>`).join("") : `<tr><td colspan="2" class="muted">No term matches "${esc(q)}". Try a shorter word.</td></tr>`);
  }
  $("#gl-q").addEventListener("input", drawGl);
  drawGl();
})();

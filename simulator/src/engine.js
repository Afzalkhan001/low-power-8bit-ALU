/* ALU8 gate-level engine.
 * The netlist below is generated from model/alu_gates.py by simulator/build_sim.py,
 * so it is the same circuit as the Spectre netlist (virtuoso/alu8.scs). */
const ALU = (() => {
  const NET = /*@@NET@@*/ null;
  const names = NET.names;
  const N = names.length;
  const id = Object.create(null);
  names.forEach((n, i) => (id[n] = i));
  const UNITS = NET.units;
  const gates = NET.gates.map(([t, ins, outs, u]) => ({ t, ins, outs, u }));

  // ---- capacitance estimate per node (fF) for switching-energy numbers
  const C_PIN = 0.25;          // gate load per cell input pin
  const C_SELF = { INV: 0.15, BUF: 0.3, NAND2: 0.25, NOR2: 0.25, AND2: 0.4, OR2: 0.4,
                   XOR2: 0.6, XNOR2: 0.6, MUX2: 0.35, MUX4: 1.0, FA: 0.9 };
  const C_OUT_LOAD = 5.0;      // same 5 fF load as the Spectre testbench
  const cap = new Float64Array(N);
  const driverUnit = new Int8Array(N).fill(-1);
  for (const g of gates) {
    for (const i of g.ins) cap[i] += C_PIN;
    for (const o of g.outs) { cap[o] += C_SELF[g.t]; driverUnit[o] = g.u; }
  }
  for (const o of NET.outputs) cap[id[o]] += C_OUT_LOAD;

  function evalGate(t, v, ins) {
    const a = v[ins[0]], b = v[ins[1]];
    switch (t) {
      case "INV": return [a ^ 1];
      case "BUF": return [a];
      case "NAND2": return [(a & b) ^ 1];
      case "NOR2": return [(a | b) ^ 1];
      case "AND2": return [a & b];
      case "OR2": return [a | b];
      case "XOR2": return [a ^ b];
      case "XNOR2": return [(a ^ b) ^ 1];
      case "MUX2": return [a ? v[ins[2]] : b];                    // sel, d0, d1
      case "MUX4": return [v[ins[2 + ((a << 1) | b)]]];          // s1, s0, d0..d3
      case "FA": {
        const c = v[ins[2]];
        return [a ^ b ^ c, (a & b) | (c & (a ^ b))];
      }
    }
    throw new Error("unknown cell " + t);
  }

  function applyInputs(v, a, b, op, iso) {
    for (let i = 0; i < 8; i++) { v[id["A" + i]] = (a >> i) & 1; v[id["B" + i]] = (b >> i) & 1; }
    for (let i = 0; i < 4; i++) v[id["OP" + i]] = (op >> i) & 1;
    v[id.ISO_OFF] = iso ? 0 : 1;          // iso = true means operand isolation is ON
    v[id.VDD] = 1; v[id.GND] = 0;
  }

  /** zero-delay evaluation: settled value of every node */
  function evaluate(a, b, op, iso = true) {
    const v = new Uint8Array(N);
    applyInputs(v, a, b, op, iso);
    for (const g of gates) {
      const r = evalGate(g.t, v, g.ins);
      for (let k = 0; k < g.outs.length; k++) v[g.outs[k]] = r[k];
    }
    return v;
  }

  /** unit-delay simulation from a settled state `prev` to new inputs.
   *  Every cell takes one delay step. Returns snapshots per step, toggles (glitches included)
   *  and switching energy per unit at the given vdd. */
  function propagate(prev, a, b, op, iso = true, vdd = 1.0) {
    let cur = prev.slice();
    applyInputs(cur, a, b, op, iso);
    const snaps = [cur.slice()];
    const togglesPerStep = [];
    const unitToggles = new Array(UNITS.length).fill(0);
    const unitEnergy = new Array(UNITS.length).fill(0);   // fJ
    const settle = new Int16Array(N);
    const nodeToggles = new Uint16Array(N);
    for (let step = 1; step < 400; step++) {
      const next = cur.slice();
      let changed = 0;
      for (const g of gates) {
        const r = evalGate(g.t, cur, g.ins);
        for (let k = 0; k < g.outs.length; k++) {
          const o = g.outs[k];
          if (r[k] !== cur[o]) {
            next[o] = r[k]; changed++;
            unitToggles[g.u]++; nodeToggles[o]++; settle[o] = step;
            unitEnergy[g.u] += 0.5 * cap[o] * vdd * vdd;
          }
        }
      }
      if (!changed) break;
      togglesPerStep.push(changed);
      snaps.push(next);
      cur = next;
    }
    return { final: cur, snaps, togglesPerStep, unitToggles, unitEnergy, settle, nodeToggles,
             depth: togglesPerStep.length };
  }

  function byte(v, prefix) {
    let x = 0;
    for (let i = 0; i < 8; i++) x |= v[id[prefix + i]] << i;
    return x;
  }
  function read(v) {
    return { Y: byte(v, "Y"), YH: byte(v, "YH"), C: v[id.C], Z: v[id.Z], N: v[id.N],
             V: v[id.V], WE: v[id.WE] };
  }
  const val = (v, name) => v[id[name]];

  /** behavioural reference (plain integer math) used by the in-page self-test */
  function ref(a, b, op) {
    const s8 = (x) => (x & 0x80 ? x - 256 : x);
    const name = NET.opcodes[op][1];
    let y = 0, yh = 0, c = 0, vf = 0;
    if (["ADD", "SUB", "INC", "DEC", "CMP"].includes(name)) {
      const rhs = { ADD: b, SUB: -b, CMP: -b, INC: 1, DEC: -1 }[name];
      const res = a + rhs;
      c = name === "ADD" || name === "INC" ? +(res > 255) : +(res >= 0);
      const sr = s8(a) + (name === "ADD" ? s8(b) : name === "INC" ? 1 : name === "DEC" ? -1 : -s8(b));
      vf = +(sr < -128 || sr > 127);
      y = res & 0xff;
    } else if (name === "MUL") { const p = a * b; y = p & 0xff; yh = p >> 8; c = vf = +(yh !== 0); }
    else if (name === "AND") y = a & b;
    else if (name === "OR") y = a | b;
    else if (name === "XOR") y = a ^ b;
    else if (name === "NOT") y = ~a & 0xff;
    else if (name === "NAND") y = ~(a & b) & 0xff;
    else if (name === "NOR") y = ~(a | b) & 0xff;
    else if (name === "XNOR") y = ~(a ^ b) & 0xff;
    else if (name === "SHL") { y = (a << 1) & 0xff; c = a >> 7; }
    else if (name === "SHR") { y = a >> 1; c = a & 1; }
    else if (name === "ROL") { y = ((a << 1) | (a >> 7)) & 0xff; c = a >> 7; }
    return { Y: y, YH: yh, C: c, Z: +(y === 0 && yh === 0), N: name === "MUL" ? 0 : y >> 7,
             V: vf, WE: name === "CMP" ? 0 : 1 };
  }

  return { NET, id, UNITS, gates, cap, driverUnit, evaluate, propagate, read, byte, val, ref,
           OPCODES: NET.opcodes, PROGRAM: NET.program, STATS: NET.stats };
})();
if (typeof module !== "undefined") module.exports = ALU;

// node simulator/test_engine.js
// Checks the web simulator's gate engine against vectors produced by the Python golden model,
// with operand isolation on and off, and checks the unit-delay simulation settles to the same state.
const fs = require("fs");
const path = require("path");
const ALU = require("./alu_engine.js");
const vecs = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "model", "check_vectors.json"), "utf8"));

let bad = 0, checked = 0;
let prev = ALU.evaluate(0, 0, 0, true);
for (const [op, a, b, Y, YH, C, Z, N, V, WE] of vecs) {
  const exp = { Y, YH, C, Z, N, V, WE };
  for (const iso of [true, false]) {
    const got = ALU.read(ALU.evaluate(a, b, op, iso));
    checked++;
    if (JSON.stringify(got) !== JSON.stringify(exp)) {
      if (++bad <= 5) console.log("MISMATCH", { op, a, b, iso, got, exp });
    }
  }
  const p = ALU.propagate(prev, a, b, op, true);
  const z = ALU.evaluate(a, b, op, true);
  if (Buffer.compare(Buffer.from(p.final), Buffer.from(z)) !== 0) {
    if (++bad <= 5) console.log("UNIT-DELAY did not settle to zero-delay state", { op, a, b });
  }
  prev = p.final;
}
// in-page reference model vs python vectors too
for (const [op, a, b, Y, YH, C, Z, N, V, WE] of vecs) {
  if (JSON.stringify(ALU.ref(a, b, op)) !== JSON.stringify({ Y, YH, C, Z, N, V, WE })) {
    if (++bad <= 5) console.log("JS REF MISMATCH", { op, a, b });
  }
}
console.log(`${checked} gate evaluations + ${vecs.length} unit-delay runs + ${vecs.length} ref checks: ` +
            (bad ? `FAIL (${bad})` : "PASS"));
process.exit(bad ? 1 : 0);

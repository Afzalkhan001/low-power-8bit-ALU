"""
Build the virtual-lab web page from the single circuit description.

    python simulator/build_sim.py

  model/alu_gates.py  --(gate list JSON)-->  simulator/alu_engine.js
  simulator/src/lab.html + alu_engine.js  -->  simulator/alu_virtual_lab.html  (one self-contained file)
"""
import csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "model"))
from alu_gates import build, INPUTS, OUTPUTS, UNITS, OPCODES, GND, VDD  # noqa: E402

TCOUNT = {"INV": 2, "BUF": 4, "NAND2": 4, "NOR2": 4, "AND2": 6, "OR2": 6, "XOR2": 12,
          "XNOR2": 12, "MUX2": 6, "MUX4": 22, "FA": 28}


def main():
    c = build()
    names = [GND, VDD] + INPUTS
    for g in c.gates:
        names += g["outs"]
    idx = {n: i for i, n in enumerate(names)}
    assert len(idx) == len(names)
    gates = [[g["t"], [idx[n] for n in g["ins"]], [idx[n] for n in g["outs"]], UNITS.index(g["unit"])]
             for g in c.gates]
    with open(os.path.join(ROOT, "model", "test_vectors.csv")) as f:
        program = [[int(r["op_bin"], 2), int(r["A_hex"], 16), int(r["B_hex"], 16)] for r in csv.DictReader(f)]
    by_unit = {u: 0 for u in UNITS}
    for g in c.gates:
        by_unit[g["unit"]] += TCOUNT[g["t"]]
    net = {"names": names, "units": UNITS, "gates": gates, "outputs": OUTPUTS,
           "opcodes": [list(o) for o in OPCODES], "program": program,
           "stats": {"cells": len(c.gates), "transistors": sum(by_unit.values()), "byUnit": by_unit}}

    engine_src = open(os.path.join(HERE, "src", "engine.js"), encoding="utf-8").read()
    engine = engine_src.replace("/*@@NET@@*/ null", json.dumps(net, separators=(",", ":")))
    with open(os.path.join(HERE, "alu_engine.js"), "w", encoding="utf-8", newline="\n") as f:
        f.write(engine)

    lab = open(os.path.join(HERE, "src", "lab.html"), encoding="utf-8").read()
    assert "/*@@ENGINE@@*/" in lab
    page = lab.replace("/*@@ENGINE@@*/", engine)
    with open(os.path.join(HERE, "alu_virtual_lab.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    print(f"engine: {len(c.gates)} cells, {len(names)} nodes, {net['stats']['transistors']} transistors")
    print(f"wrote simulator/alu_engine.js and simulator/alu_virtual_lab.html ({len(page)//1024} KB)")


if __name__ == "__main__":
    main()

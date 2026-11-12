"""
Switch-level check of the generated TRANSISTOR netlist (no SPICE needed).

    python virtuoso/switch_sim.py

Parses cells.scs + alu8.scs exactly as Spectre would see them, flattens every subckt down to
individual MOSFETs, then treats each transistor as a switch (nmos ON when gate=1, pmos ON when
gate=0) and resolves every node to 0/1 by finding what it is connected to (VDD or GND).
Each vector in model/test_vectors.csv is applied with operand isolation ON and OFF and the
outputs are compared with the golden model. It also flags any VDD-GND short or floating output.

This proves the wiring of every transistor is right; timing and power still need Spectre.
"""
import csv, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "model"))
from alu_gates import INPUTS, OUTPUTS  # noqa: E402


def parse(paths):
    subckts, models = {}, set()
    cur = None
    for path in paths:
        for raw in open(path):
            line = raw.split("//")[0].strip()
            if not line or line.startswith("simulator") or line.startswith("include"):
                continue
            m = re.match(r"subckt\s+(\w+)\s*\(([^)]*)\)", line)
            if m:
                cur = {"pins": m.group(2).split(), "insts": []}
                subckts[m.group(1)] = cur
                continue
            if line.startswith("ends"):
                cur = None
                continue
            m = re.match(r"(\w+)\s*\(([^)]*)\)\s*(\w+)", line)
            if m and cur is not None:
                cur["insts"].append((m.group(1), m.group(2).split(), m.group(3)))
    return subckts


def flatten(subckts, top):
    mos = []            # (kind, d, g, s)
    kinds = {}

    def walk(name, mapping, path):
        sc = subckts[name]
        for iname, nodes, master in sc["insts"]:
            def mp(n):
                if n in mapping: return mapping[n]
                return f"{path}/{n}"
            if master in subckts:
                sub = subckts[master]
                assert len(sub["pins"]) == len(nodes), f"pin count mismatch {path}/{iname} -> {master}"
                walk(master, {p: mp(n) for p, n in zip(sub["pins"], nodes)}, f"{path}/{iname}")
            else:
                assert len(nodes) == 4, f"{path}/{iname}: MOSFET needs 4 terminals"
                # bulk tied to the cell's vdd pin -> pmos, to vss -> nmos
                kind = "p" if nodes[3] == "vdd" else "n"
                assert kinds.setdefault(master, kind) == kind, f"model {master} used as both n and p"
                d, g, s, _b = (mp(n) for n in nodes)
                mos.append((kind, d, g, s))
    top_pins = subckts[top]["pins"]
    walk(top, {p: p for p in top_pins}, "")
    return mos, kinds


def solve(mos, fixed, state):
    """Iterate switch network to a fixpoint. fixed: node->0/1. state: node->0/1/None (warm start)."""
    nodes = set(state)
    for _k, d, g, s in mos:
        nodes.update((d, g, s))
    idx = {n: i for i, n in enumerate(nodes)}
    val = [state.get(n) for n in nodes]
    for n, v in fixed.items():
        val[idx[n]] = v
    fixed_i = {idx[n]: v for n, v in fixed.items()}
    T = [(k == "n", idx[d], idx[g], idx[s]) for k, d, g, s in mos]
    names = list(nodes)
    for it in range(500):
        parent = list(range(len(nodes)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for is_n, d, g, s in T:
            gv = val[g]
            if gv is None:
                continue
            if (gv == 1) == is_n:
                rd, rs = find(d), find(s)
                if rd != rs:
                    parent[rd] = rs
        src = {}
        for i, v in fixed_i.items():
            r = find(i)
            src.setdefault(r, set()).add(v)
        new = val[:]
        shorts = []
        for i in range(len(nodes)):
            if i in fixed_i:
                continue
            s = src.get(find(i))
            if not s:
                new[i] = None
            elif len(s) == 2:
                new[i] = None; shorts.append(names[i])
            else:
                new[i] = next(iter(s))
        if new == val:
            return {n: val[idx[n]] for n in nodes}, shorts, it
        val = new
    raise RuntimeError("no convergence")


def main():
    subckts = parse([os.path.join(HERE, "cells.scs"), os.path.join(HERE, "alu8.scs")])
    mos, kinds = flatten(subckts, "alu8")
    print(f"Flattened alu8: {len(mos)} MOSFETs, models {kinds}")
    supplies = ["vdd_ctrl", "vdd_arith", "vdd_mul", "vdd_logic", "vdd_shift"]
    vecs = list(csv.DictReader(open(os.path.join(ROOT, "model", "test_vectors.csv"))))
    fails = 0
    for iso_off in (0, 1):
        state = {}
        for v in vecs:
            a, b, op = int(v["A_hex"], 16), int(v["B_hex"], 16), int(v["op_bin"], 2)
            fixed = {s: 1 for s in supplies}
            fixed["vss"] = 0
            fixed.update({f"A{i}": (a >> i) & 1 for i in range(8)})
            fixed.update({f"B{i}": (b >> i) & 1 for i in range(8)})
            fixed.update({f"OP{i}": (op >> i) & 1 for i in range(4)})
            fixed["ISO_OFF"] = iso_off
            state, shorts, iters = solve(mos, fixed, state)
            outs = {o: state.get(o) for o in OUTPUTS}
            if None in outs.values():
                print(f"  vec {v['idx']}: undefined outputs {[o for o, x in outs.items() if x is None]}")
                fails += 1; continue
            y = sum(outs[f"Y{i}"] << i for i in range(8))
            yh = sum(outs[f"YH{i}"] << i for i in range(8))
            got = (y, yh, outs["C"], outs["Z"], outs["N"], outs["V"], outs["WE"])
            exp = (int(v["Y_hex"], 16), int(v["YH_hex"], 16), int(v["C"]), int(v["Z"]),
                   int(v["N"]), int(v["V"]), int(v["WE"]))
            ok = got == exp and not shorts
            fails += not ok
            print(f"  iso={'OFF' if iso_off else 'ON '} #{int(v['idx']):2d} {v['op']:<4} A={v['A_hex']} "
                  f"B={v['B_hex']} -> Y={y:02X} YH={yh:02X} CZNV={got[2]}{got[3]}{got[4]}{got[5]} "
                  f"WE={got[6]}  {'PASS' if ok else 'FAIL exp ' + str(exp)}"
                  f"{'  SHORT ' + str(shorts[:3]) if shorts else ''}  ({iters} it)")
    print(f"\nSWITCH-LEVEL RESULT: {'PASS' if fails == 0 else 'FAIL'} "
          f"({2*len(vecs) - fails}/{2*len(vecs)} vectors)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

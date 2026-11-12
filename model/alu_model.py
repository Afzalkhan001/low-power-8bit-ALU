"""
Golden model of the 8-bit ALU + exhaustive check of the gate-level structure.

    python model/alu_model.py            # check all 16 ops x 65,536 operand pairs, write vectors

Flag conventions
  C : carry-out of the adder (ADD/INC), NOT-borrow for SUB/DEC/CMP (1 = A >= B),
      shifted-out bit for SHL/SHR/ROL, "product needs >8 bits" for MUL, 0 for logic ops
  Z : result (Y, and Y_HI for MUL) is all zeros
  N : Y[7] (sign of the 8-bit result); 0 for MUL (unsigned product)
  V : signed (2's complement) overflow for ADD/SUB/INC/DEC/CMP, same as C for MUL, else 0
  WE: register write-enable, 0 only for CMP (result is computed but not stored)
"""
import json, os, random, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alu_gates import build, evaluate, OPCODES, OUTPUTS, simulate  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MNEMONIC = {int(code, 2): name for code, name, _ in OPCODES}


def s8(x):
    """unsigned byte -> signed value"""
    return x - 256 if x & 0x80 else x


def alu_ref(a, b, op):
    """Behavioural reference written with ordinary integer math (independent of the gates)."""
    name = MNEMONIC[op]
    yh, c, v = 0, 0, 0
    if name in ("ADD", "SUB", "INC", "DEC", "CMP"):
        if name == "ADD":
            res = a + b;            c = int(res > 255)
        elif name == "INC":
            res = a + 1;            c = int(res > 255)
        elif name in ("SUB", "CMP"):
            res = a - b;            c = int(a >= b)           # no borrow
        else:  # DEC
            res = a - 1;            c = int(a >= 1)
        sres = s8(a) + (s8(b) if name == "ADD" else -s8(b) if name in ("SUB", "CMP")
                        else 1 if name == "INC" else -1)
        v = int(not -128 <= sres <= 127)
        y = res & 0xFF
    elif name == "MUL":
        p = a * b
        y, yh = p & 0xFF, p >> 8
        c = v = int(yh != 0)
    elif name == "AND":  y = a & b
    elif name == "OR":   y = a | b
    elif name == "XOR":  y = a ^ b
    elif name == "NOT":  y = ~a & 0xFF
    elif name == "NAND": y = ~(a & b) & 0xFF
    elif name == "NOR":  y = ~(a | b) & 0xFF
    elif name == "XNOR": y = ~(a ^ b) & 0xFF
    elif name == "SHL":  y = (a << 1) & 0xFF; c = a >> 7
    elif name == "SHR":  y = a >> 1;          c = a & 1
    elif name == "ROL":  y = ((a << 1) | (a >> 7)) & 0xFF; c = a >> 7
    z = int(y == 0 and yh == 0)
    n = 0 if name == "MUL" else y >> 7
    we = 0 if name == "CMP" else 1
    return {"Y": y, "YH": yh, "C": c, "Z": z, "N": n, "V": v, "WE": we}


def exhaustive_check(circuit):
    """Bit-parallel gate evaluation: one Python int holds all 65,536 (A,B) pairs."""
    W = 1 << 16
    MASK = (1 << W) - 1
    ops = {"zero": 0, "one": MASK, "and": lambda x, y: x & y, "or": lambda x, y: x | y,
           "xor": lambda x, y: x ^ y, "not": lambda x: x ^ MASK}
    # pair index k = A + 256*B
    bitstr = {}
    for i in range(8):
        pa = "".join("1" if (k >> i) & 1 else "0" for k in range(W))[::-1]
        pb = "".join("1" if (k >> (8 + i)) & 1 else "0" for k in range(W))[::-1]
        bitstr[f"A{i}"] = int(pa, 2); bitstr[f"B{i}"] = int(pb, 2)
    total_bad = 0
    for op in range(16):
        op_bad = 0
        for iso_off in (0, 1):
            vals = dict(bitstr)
            vals.update({f"OP{i}": MASK if (op >> i) & 1 else 0 for i in range(4)})
            vals["ISO_OFF"] = MASK if iso_off else 0
            v = evaluate(circuit, vals, ops)
            outs = {o: format(v[o], f"0{W}b")[::-1] for o in OUTPUTS}
            bad = 0
            for k in range(W):
                a, b = k & 0xFF, k >> 8
                r = alu_ref(a, b, op)
                y = sum((outs[f"Y{i}"][k] == "1") << i for i in range(8))
                yh = sum((outs[f"YH{i}"][k] == "1") << i for i in range(8))
                got = {"Y": y, "YH": yh, **{f: int(outs[f][k]) for f in ("C", "Z", "N", "V", "WE")}}
                if got != r:
                    bad += 1
                    if bad <= 3:
                        print(f"  MISMATCH op={op:04b} A={a:02X} B={b:02X} got={got} exp={r}")
            total_bad += bad
            op_bad += bad
        print(f"  {op:04b} {MNEMONIC[op]:<5} 65536 pairs x iso on/off : "
              f"{'PASS' if op_bad == 0 else f'{op_bad} FAIL'}")
    return total_bad


def spectre_vectors():
    """Short directed list for the transistor-level transient run (~10 ns each)."""
    V = []
    add = lambda name, a, b: V.append((int([c for c, n, _ in OPCODES if n == name][0], 2), a, b))
    add("ADD", 0x2D, 0x17); add("ADD", 0xFF, 0x01); add("ADD", 0x7F, 0x01)   # 45+23, wrap, signed ovf
    add("SUB", 0x2D, 0x17); add("SUB", 0x17, 0x2D); add("SUB", 0x80, 0x01)
    add("INC", 0x0F, 0x00); add("INC", 0xFF, 0x00)
    add("DEC", 0x10, 0x00); add("DEC", 0x00, 0x00)
    add("MUL", 0x0C, 0x0B); add("MUL", 0xFF, 0xFF); add("MUL", 0x10, 0x10)
    add("AND", 0xCA, 0x5F); add("OR", 0xCA, 0x5F); add("XOR", 0xCA, 0x5F); add("XOR", 0xAA, 0xAA)
    add("NOT", 0xCA, 0x00); add("NAND", 0xCA, 0x5F); add("NOR", 0xCA, 0x5F); add("XNOR", 0xCA, 0x5F)
    add("SHL", 0x81, 0x00); add("SHR", 0x81, 0x00); add("ROL", 0x81, 0x00); add("ROL", 0x40, 0x00)
    add("CMP", 0x37, 0x37); add("CMP", 0x10, 0x20); add("CMP", 0x20, 0x10)
    add("ADD", 0x00, 0x00); add("MUL", 0xA5, 0x5A)
    return V


def main():
    t0 = time.time()
    c = build()
    print(f"Gate-level ALU: {len(c.gates)} cells")

    # quick sanity on the scalar path
    for op, a, b in [(0, 45, 23), (1, 23, 45), (4, 12, 11), (14, 0x81, 0)]:
        assert simulate(a, b, op, circuit=c) == alu_ref(a, b, op)

    print("Exhaustive check (gate structure vs integer math):")
    bad = exhaustive_check(c)
    print(f"RESULT: {'PASS - 0 mismatches' if bad == 0 else f'FAIL - {bad} mismatches'}"
          f"  ({time.time() - t0:.1f} s)")

    # ---- directed vectors for Spectre + expected outputs
    vecs = spectre_vectors()
    with open(os.path.join(HERE, "test_vectors.csv"), "w", newline="") as f:
        f.write("idx,op_bin,op,A_hex,B_hex,A_dec,B_dec,Y_hex,YH_hex,C,Z,N,V,WE\n")
        for k, (op, a, b) in enumerate(vecs):
            r = alu_ref(a, b, op)
            f.write(f"{k},{op:04b},{MNEMONIC[op]},{a:02X},{b:02X},{a},{b},{r['Y']:02X},{r['YH']:02X},"
                    f"{r['C']},{r['Z']},{r['N']},{r['V']},{r['WE']}\n")
    print(f"Wrote model/test_vectors.csv ({len(vecs)} vectors)")

    # ---- random + edge vectors to cross-check the web simulator engine
    rnd = random.Random(8)
    edge = [0x00, 0x01, 0x7F, 0x80, 0xFF, 0x55, 0xAA]
    checks = []
    for op in range(16):
        pairs = [(x, y) for x in edge for y in edge] + [(rnd.randrange(256), rnd.randrange(256)) for _ in range(150)]
        for a, b in pairs:
            r = alu_ref(a, b, op)
            checks.append([op, a, b, r["Y"], r["YH"], r["C"], r["Z"], r["N"], r["V"], r["WE"]])
    with open(os.path.join(HERE, "check_vectors.json"), "w") as f:
        json.dump(checks, f, separators=(",", ":"))
    print(f"Wrote model/check_vectors.json ({len(checks)} vectors for the simulator check)")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

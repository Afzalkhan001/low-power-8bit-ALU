"""
Gate-level structure of the low-power 8-bit ALU.

This file is the SINGLE SOURCE OF TRUTH for the circuit. It is used by:
  * model/alu_model.py          -> exhaustive gate-level check vs. behavioural math
  * virtuoso/gen_netlist.py     -> Spectre transistor-level netlist for Cadence
  * simulator/build_sim.py      -> gate list embedded in the virtual-lab web page

Cells (each maps 1:1 to a CMOS subcircuit in virtuoso/cells.scs):
  INV, BUF, NAND2, NOR2, AND2, OR2, XOR2, XNOR2,
  MUX2 (sel, d0, d1)            transmission-gate 2:1 mux
  MUX4 (s1, s0, d0, d1, d2, d3) transmission-gate 4:1 mux + restoring buffer
  FA   (a, b, cin) -> (s, cout) 28-transistor mirror full adder

Opcode map (OP[3:0]):
  0000 ADD   0001 SUB   0010 INC   0011 DEC
  0100 MUL   0101 AND   0110 OR    0111 XOR
  1000 NOT   1001 NAND  1010 NOR   1011 XNOR
  1100 SHL   1101 SHR   1110 ROL   1111 CMP
"""

GND, VDD = "GND", "VDD"          # constant nodes (tie-low / tie-high)

OPCODES = [
    ("0000", "ADD",  "Y = A + B"),
    ("0001", "SUB",  "Y = A - B"),
    ("0010", "INC",  "Y = A + 1"),
    ("0011", "DEC",  "Y = A - 1"),
    ("0100", "MUL",  "{Y_HI,Y} = A x B"),
    ("0101", "AND",  "Y = A & B"),
    ("0110", "OR",   "Y = A | B"),
    ("0111", "XOR",  "Y = A ^ B"),
    ("1000", "NOT",  "Y = ~A"),
    ("1001", "NAND", "Y = ~(A & B)"),
    ("1010", "NOR",  "Y = ~(A | B)"),
    ("1011", "XNOR", "Y = ~(A ^ B)"),
    ("1100", "SHL",  "Y = A << 1"),
    ("1101", "SHR",  "Y = A >> 1"),
    ("1110", "ROL",  "Y = rotate-left(A)"),
    ("1111", "CMP",  "flags of A - B (WE=0)"),
]

CELL_PINS = {            # input pins, output pins
    "INV":   (["a"], ["y"]),
    "BUF":   (["a"], ["y"]),
    "NAND2": (["a", "b"], ["y"]),
    "NOR2":  (["a", "b"], ["y"]),
    "AND2":  (["a", "b"], ["y"]),
    "OR2":   (["a", "b"], ["y"]),
    "XOR2":  (["a", "b"], ["y"]),
    "XNOR2": (["a", "b"], ["y"]),
    "MUX2":  (["sel", "d0", "d1"], ["y"]),
    "MUX4":  (["s1", "s0", "d0", "d1", "d2", "d3"], ["y"]),
    "FA":    (["a", "b", "ci"], ["s", "co"]),
}

INPUTS = ([f"A{i}" for i in range(8)] + [f"B{i}" for i in range(8)] +
          [f"OP{i}" for i in range(4)] + ["ISO_OFF"])
OUTPUTS = ([f"Y{i}" for i in range(8)] + [f"YH{i}" for i in range(8)] +
           ["C", "Z", "N", "V", "WE"])
UNITS = ["ctrl", "arith", "mul", "logic", "shift"]


class Circuit:
    def __init__(self):
        self.gates = []          # dicts: t, ins, outs, unit
        self.driven = set(INPUTS) | {GND, VDD}

    def add(self, t, ins, outs, unit):
        for n in ins:
            assert n in self.driven, f"{t}: input {n} used before it is driven"
        for n in outs:
            assert n not in self.driven, f"node {n} driven twice"
            self.driven.add(n)
        assert unit in UNITS
        self.gates.append({"t": t, "ins": list(ins), "outs": list(outs), "unit": unit})
        return outs[0] if len(outs) == 1 else tuple(outs)

    # one-output helpers
    def g(self, t, out, unit, *ins):
        return self.add(t, ins, [out], unit)


def build():
    c = Circuit()
    A = [f"A{i}" for i in range(8)]
    B = [f"B{i}" for i in range(8)]
    op = [f"OP{i}" for i in range(4)]

    # ------------------------------------------------------------ decoder
    u = "ctrl"
    nop = [c.g("INV", f"nOP{i}", u, op[i]) for i in range(4)]
    nand01 = c.g("NAND2", "nand01", u, op[0], op[1])
    nand23 = c.g("NAND2", "nand23", u, op[2], op[3])
    is1111 = c.g("NOR2", "is1111", u, nand01, nand23)
    WE = c.g("OR2", "WE", u, nand01, nand23)                 # 0 only for CMP
    n3n2 = c.g("AND2", "n3n2", u, nop[3], nop[2])            # 00xx
    n3p2 = c.g("AND2", "n3p2", u, nop[3], op[2])             # 01xx
    p3n2 = c.g("AND2", "p3n2", u, op[3], nop[2])             # 10xx
    p3p2 = c.g("AND2", "p3p2", u, op[3], op[2])              # 11xx
    or10 = c.g("OR2", "or10", u, op[1], op[0])
    nor10 = c.g("NOR2", "nor10", u, op[1], op[0])
    en_ar = c.g("OR2", "EN_ARITH", u, n3n2, is1111)
    en_mu = c.g("AND2", "EN_MUL", u, n3p2, nor10)
    en_lg_a = c.g("AND2", "en_lg_a", u, n3p2, or10)
    en_lg = c.g("OR2", "EN_LOGIC", u, en_lg_a, p3n2)
    en_sh = c.g("AND2", "EN_SHIFT", u, p3p2, nand01)

    # operand-isolation enables (ISO_OFF=1 disables isolation for power comparison)
    eg = {}
    for name, en in (("ar", en_ar), ("mu", en_mu), ("lg", en_lg), ("sh", en_sh)):
        eg[name] = c.g("OR2", f"ISO_EN_{name.upper()}", u, en, "ISO_OFF")

    def isolate(prefix, unit_sig, bits, label):
        return [c.g("AND2", f"{prefix}_{label}{i}", u, bits[i], eg[unit_sig])
                for i in range(len(bits))]

    ar_a = isolate("ar", "ar", A, "a"); ar_b = isolate("ar", "ar", B, "b")
    mu_a = isolate("mu", "mu", A, "a"); mu_b = isolate("mu", "mu", B, "b")
    lg_a = isolate("lg", "lg", A, "a"); lg_b = isolate("lg", "lg", B, "b")
    sh_a = isolate("sh", "sh", A, "a")

    # ------------------------------------------------------------ arithmetic unit
    u = "arith"
    passb = c.g("OR2", "ar_passb", u, nop[1], op[3])          # 1: use B, 0: use 0
    xr01 = c.g("XOR2", "ar_x01", u, op[0], op[1])
    cin_raw = c.g("OR2", "ar_cinr", u, xr01, op[3])
    inv = c.g("AND2", "ar_inv", u, op[0], eg["ar"])           # 1: invert B (2's comp)
    cin = c.g("AND2", "ar_c0", u, cin_raw, eg["ar"])
    carry = [cin]
    ar_s = []
    for i in range(8):
        bp = c.g("AND2", f"ar_bp{i}", u, ar_b[i], passb)
        bc = c.g("XOR2", f"ar_bc{i}", u, bp, inv)
        s, co = c.add("FA", [ar_a[i], bc, carry[i]], [f"ar_s{i}", f"ar_c{i+1}"], u)
        ar_s.append(s); carry.append(co)
    ar_v = c.g("XOR2", "ar_v", u, carry[8], carry[7])

    # ------------------------------------------------------------ 8x8 array multiplier
    u = "mul"
    pp = [[c.g("AND2", f"mu_pp{i}_{j}", u, mu_a[j], mu_b[i]) for j in range(8)]
          for i in range(8)]
    S = pp[0][:]                    # running partial sum (8 bits)
    carry_row = GND
    P = [S[0]]
    for i in range(1, 8):
        X = S[1:] + [carry_row]
        rc = GND
        newS = []
        for j in range(8):
            s, rc = c.add("FA", [X[j], pp[i][j], rc], [f"mu_s{i}_{j}", f"mu_c{i}_{j}"], u)
            newS.append(s)
        S, carry_row = newS, rc
        P.append(S[0])
    P += S[1:] + [carry_row]        # P[0..15]
    # mulC = OR of high byte
    l1 = [c.g("NOR2", f"mu_or1_{k}", u, P[8 + 2*k], P[9 + 2*k]) for k in range(4)]
    l2 = [c.g("NAND2", f"mu_or2_{k}", u, l1[2*k], l1[2*k+1]) for k in range(2)]
    l3 = c.g("NOR2", "mu_or3", u, l2[0], l2[1])
    mulC = c.g("INV", "mu_hi_nz", u, l3)

    # ------------------------------------------------------------ logic unit
    u = "logic"
    lg_y = []
    for i in range(8):
        na = c.g("INV", f"lg_nota{i}", u, lg_a[i])
        nd = c.g("NAND2", f"lg_nand{i}", u, lg_a[i], lg_b[i])
        nr = c.g("NOR2", f"lg_nor{i}", u, lg_a[i], lg_b[i])
        xn = c.g("XNOR2", f"lg_xnor{i}", u, lg_a[i], lg_b[i])
        m = c.g("MUX4", f"lg_m{i}", u, op[1], op[0], na, nd, nr, xn)
        lg_y.append(c.g("XOR2", f"lg_y{i}", u, m, nop[3]))    # invert for AND/OR/XOR

    # ------------------------------------------------------------ shifter
    u = "shift"
    fill = c.g("AND2", "sh_fill", u, op[1], sh_a[7])          # ROL feeds A7 into bit 0
    sh_y = []
    for i in range(8):
        left = sh_a[i-1] if i > 0 else fill
        right = sh_a[i+1] if i < 7 else GND
        m = c.g("MUX2", f"sh_m{i}", u, op[0], left, right)
        sh_y.append(c.g("BUF", f"sh_y{i}", u, m))
    sh_c = c.g("MUX2", "sh_c", u, op[0], sh_a[7], sh_a[0])

    # ------------------------------------------------------------ output mux + flags
    u = "ctrl"
    s0 = c.g("OR2", "SEL0", u, en_mu, en_sh)
    s1 = c.g("OR2", "SEL1", u, en_lg, en_sh)
    Y = [c.g("MUX4", f"Y{i}", u, s1, s0, ar_s[i], P[i], lg_y[i], sh_y[i]) for i in range(8)]
    YH = [c.g("AND2", f"YH{i}", u, P[8+i], en_mu) for i in range(8)]
    c.g("MUX4", "C", u, s1, s0, carry[8], mulC, GND, sh_c)
    c.g("MUX4", "V", u, s1, s0, ar_v, mulC, GND, GND)
    allbits = Y + YH
    z1 = [c.g("NOR2", f"z1_{k}", u, allbits[2*k], allbits[2*k+1]) for k in range(8)]
    z2 = [c.g("NAND2", f"z2_{k}", u, z1[2*k], z1[2*k+1]) for k in range(4)]
    z3 = [c.g("NOR2", f"z3_{k}", u, z2[2*k], z2[2*k+1]) for k in range(2)]
    z4 = c.g("NAND2", "z4", u, z3[0], z3[1])                 # OR of all 16 bits
    c.g("INV", "Z", u, z4)
    nmul = c.g("INV", "nEN_MUL", u, en_mu)
    c.g("AND2", "N", u, Y[7], nmul)

    for o in OUTPUTS:
        assert o in c.driven, o
    return c


def evaluate(circuit, values, ops):
    """Evaluate gates in order. `values` maps input name -> value.
    `ops` supplies and_/or_/xor_/not_ functions so the same routine works for
    plain bits (0/1) and for bit-parallel Python ints."""
    v = dict(values)
    v[GND] = ops["zero"]; v[VDD] = ops["one"]
    AND, OR, XOR, NOT = ops["and"], ops["or"], ops["xor"], ops["not"]
    for gt in circuit.gates:
        t, i = gt["t"], [v[n] for n in gt["ins"]]
        if t == "INV":   r = [NOT(i[0])]
        elif t == "BUF": r = [i[0]]
        elif t == "NAND2": r = [NOT(AND(i[0], i[1]))]
        elif t == "NOR2":  r = [NOT(OR(i[0], i[1]))]
        elif t == "AND2":  r = [AND(i[0], i[1])]
        elif t == "OR2":   r = [OR(i[0], i[1])]
        elif t == "XOR2":  r = [XOR(i[0], i[1])]
        elif t == "XNOR2": r = [NOT(XOR(i[0], i[1]))]
        elif t == "MUX2":
            s, d0, d1 = i
            r = [OR(AND(NOT(s), d0), AND(s, d1))]
        elif t == "MUX4":
            s1, s0, d0, d1, d2, d3 = i
            lo = OR(AND(NOT(s0), d0), AND(s0, d1))
            hi = OR(AND(NOT(s0), d2), AND(s0, d3))
            r = [OR(AND(NOT(s1), lo), AND(s1, hi))]
        elif t == "FA":
            a, b, ci = i
            r = [XOR(XOR(a, b), ci), OR(AND(a, b), AND(ci, XOR(a, b)))]
        else:
            raise ValueError(t)
        for n, val in zip(gt["outs"], r):
            v[n] = val
    return v


BIT_OPS = {"zero": 0, "one": 1, "and": lambda a, b: a & b, "or": lambda a, b: a | b,
           "xor": lambda a, b: a ^ b, "not": lambda a: a ^ 1}


def simulate(a, b, opcode, iso_off=0, circuit=None):
    """Gate-level evaluation of one vector. Returns dict of outputs."""
    circuit = circuit or build()
    vals = {f"A{i}": (a >> i) & 1 for i in range(8)}
    vals.update({f"B{i}": (b >> i) & 1 for i in range(8)})
    vals.update({f"OP{i}": (opcode >> i) & 1 for i in range(4)})
    vals["ISO_OFF"] = iso_off
    v = evaluate(circuit, vals, BIT_OPS)
    y = sum(v[f"Y{i}"] << i for i in range(8))
    yh = sum(v[f"YH{i}"] << i for i in range(8))
    return {"Y": y, "YH": yh, "C": v["C"], "Z": v["Z"], "N": v["N"], "V": v["V"], "WE": v["WE"]}


if __name__ == "__main__":
    c = build()
    from collections import Counter
    print("gates:", len(c.gates))
    print("by type:", dict(Counter(g["t"] for g in c.gates)))
    print("by unit:", dict(Counter(g["unit"] for g in c.gates)))

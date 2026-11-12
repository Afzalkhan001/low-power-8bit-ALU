# Design and Simulation of a Low-Power 8-Bit ALU in Cadence

A transistor-level 8-bit ALU (3,738 MOSFETs, 341 CMOS cells) with 16 operations, a Spectre testbench for
Cadence Virtuoso, and an interactive **virtual lab** that shows every 0 and 1 moving through the circuit.

**Live website:** https://afzalkhan001.github.io/low-power-8bit-ALU/
**New here? Read [SETUP.md](SETUP.md)** for step-by-step setup, the checks and the Cadence run.

## Project website
Open the live link above, or `website/index.html` in any browser. It is one self-contained file, so you can also upload it to
any static host (GitHub Pages, Netlify). It has these pages:
- **Overview**: abstract, objectives, specification
- **Start here**: 13 beginner chapters (binary, addition, two's complement, multiplication, gates, transistors,
  CMOS, adders, muxes, the ALU, power, Cadence), each with a clickable demo, plus a quiz and a glossary
- **Virtual lab**: the full simulator described below
- **Architecture**: block diagram, block descriptions, cell library with transistor diagrams, decoder equations
- **Cadence flow**: the Spectre and Virtuoso steps with copyable commands
- **Results**: verification status, expected outputs, and a table for your Spectre measurements
- **Netlists**: every generated file, ready to copy

Rebuild after any change with `python simulator/build_sim.py` and then `python website/build_site.py`.
Edit the sources in `website/src/` (`site.html`, `learn.html`, `learn.css`, `learn.js`), not the generated `index.html`.

## Open the virtual lab
Open `simulator/alu_virtual_lab.html` in any browser (no install needed). You can:
- flip the A and B bits, pick any of the 16 opcodes, and see Y, Y_HI and the flags C Z N V WE
- see how the math was done: carry rows for ADD/SUB, partial products for MUL, the mux choice for logic ops, bit moves for shifts
- watch the circuit view with live bits on every block, including the isolated (idle) blocks held at 0
- play the signal propagation one cell-delay at a time and see the carry ripple and the glitches
- compare switching energy with operand isolation on and off, and sweep VDD
- run the same 30-vector test program as the Spectre testbench, shown as waveforms

## Opcodes (OP[3:0])

| OP | Op | OP | Op | OP | Op | OP | Op |
|---|---|---|---|---|---|---|---|
| 0000 | ADD | 0100 | MUL (16-bit) | 1000 | NOT A | 1100 | SHL |
| 0001 | SUB | 0101 | AND | 1001 | NAND | 1101 | SHR |
| 0010 | INC | 0110 | OR | 1010 | NOR | 1110 | ROL |
| 0011 | DEC | 0111 | XOR | 1011 | XNOR | 1111 | CMP (flags only, WE=0) |

## Architecture
```
OP ─► decoder ─► EN_ARITH / EN_MUL / EN_LOGIC / EN_SHIFT
A,B ─► operand-isolation AND gates ─┬─► Arithmetic: B-control + 8 × 28T mirror full adders (ripple carry)
                                    ├─► Multiplier: 8×8 array, 64 AND + 56 full adders ─► Y_HI
                                    ├─► Logic: NOT/NAND/NOR/XNOR per bit, TG 4:1 mux, XOR invert
                                    └─► Shifter: TG 2:1 mux per bit (SHL/SHR/ROL)
                                         └─► TG 4:1 output mux ─► Y[7:0], flags C Z N V, WE
```
Low-power techniques: operand isolation, gated adder controls, transmission-gate muxes, mirror adder,
minimum sizing, VDD scaling, and per-block supplies for power measurement. `docs/virtuoso_guide.md` explains each one.

## Folder layout
| Path | Purpose |
|---|---|
| `model/alu_gates.py` | **The circuit**: one gate-level description used by every other part |
| `model/alu_model.py` | Golden model; exhaustive check; writes `test_vectors.csv` and `check_vectors.json` |
| `virtuoso/gen_netlist.py` | Writes `cells.scs`, `alu8.scs`, `tb_alu8.scs`, `tb_alu8_noiso.scs`, `alu8_check.ocn` |
| `virtuoso/switch_sim.py` | Switch-level simulation of the transistor netlist |
| `simulator/build_sim.py` | Builds `alu_virtual_lab.html` from `src/` plus the gate list |
| `website/build_site.py` | Builds `website/index.html` from `website/src/` + the lab + the netlists |
| `simulator/test_engine.js` | Checks the web engine against the Python model (`node simulator/test_engine.js`) |
| `docs/virtuoso_guide.md` | Cadence steps: PDK setup, schematics, ADE, power/delay measurement, expected results |

## Rebuild and verify (Python 3, Node optional)
```bash
python model/alu_model.py        # 16 ops x 65,536 operand pairs x isolation on/off
python virtuoso/gen_netlist.py   # add --pdk gpdk090/gpdk180 or --model-file <path>
python virtuoso/switch_sim.py    # transistor netlist, 30 vectors x isolation on/off
python simulator/build_sim.py
node simulator/test_engine.js
```

## Verification status
| Check | Result |
|---|---|
| Gate structure vs integer math, all 16 ops × 65,536 pairs, isolation on and off | PASS, 0 mismatches |
| Transistor netlist (3,738 MOSFETs), switch-level, 60 vector runs | PASS 60/60 |
| Web simulator engine vs Python model, 3,184 vectors + unit-delay settling | PASS |
| Spectre transient (timing, power) | **Not run yet.** Needs your Cadence machine; see `docs/virtuoso_guide.md` |

Model names in `gen_netlist.py` (`g45n1svt`/`g45p1svt` for gpdk045) are typical. Check them against your PDK
before running Spectre (guide, section 2).

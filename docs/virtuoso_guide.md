# Virtuoso / Spectre guide: Low-Power 8-Bit ALU

This guide takes the generated netlists in `virtuoso/` through Cadence: schematic entry in Virtuoso, transient
simulation in Spectre (ADE Explorer or command line), and the power and delay measurements for the report.

> Simulation status: the transistor netlist has been verified **logically** on this PC with
> `virtuoso/switch_sim.py` (all 3,738 MOSFETs treated as switches, 60/60 vectors pass). It has **not** been
> run in Spectre yet, because Cadence is not installed here. Timing and power numbers come from your Spectre run.

---

## 1. Files

| File | What it is |
|---|---|
| `virtuoso/cells.scs` | CMOS cells: `inv buf nand2 nor2 and2 or2 xor2 xnor2 mux2 mux4 fa` |
| `virtuoso/alu8.scs` | The full ALU as one subckt `alu8` (341 cell instances, 3,738 transistors) |
| `virtuoso/tb_alu8.scs` | Testbench, operand isolation **ON** (30 vectors × 10 ns = 300 ns) |
| `virtuoso/tb_alu8_noiso.scs` | Same stimulus, operand isolation **OFF** (for the power comparison) |
| `virtuoso/alu8_check.ocn` | OCEAN script: PASS/FAIL per vector, power per block, worst-case delay |
| `virtuoso/gen_netlist.py` | Regenerates all of the above (PDK, model names, VDD) |
| `virtuoso/switch_sim.py` | Switch-level check of the transistor netlist (no Cadence needed) |

### Pin list of `alu8`
```
A0..A7  B0..B7  OP0..OP3  ISO_OFF          inputs (ISO_OFF=1 disables operand isolation)
Y0..Y7  YH0..YH7  C Z N V WE               outputs
vdd_ctrl vdd_arith vdd_mul vdd_logic vdd_shift vss   one supply per block (to measure each block's power)
```

## 2. Point the netlist at your PDK

The default preset is **gpdk045** (`g45n1svt` / `g45p1svt`, L = 45 nm, Wn = 120 nm, Wp = 240 nm, VDD = 1.0 V).
Model and section names differ between PDK releases, so check yours once:

1. In Virtuoso, place one `nmos1v` (or equivalent) from your PDK library in any schematic.
2. ADE → *Simulation → Netlist → Display*. Note the **model name** on the transistor line and the
   **include path + section** at the top.
3. Regenerate on the Cadence machine:

```bash
python3 gen_netlist.py --pdk gpdk045 --model-file /your/path/gpdk045/models/spectre/gpdk045.scs --section tt
```

Other presets: `--pdk gpdk090` (VDD 1.2 V) and `--pdk gpdk180` (VDD 1.8 V). You can override model names with
`--nmos NAME --pmos NAME`. If Python is not available there, edit the `include` line of `tb_alu8*.scs` by hand,
and replace the model names in `cells.scs` with find/replace.

## 3. Fast path: run Spectre from the command line

```bash
cd virtuoso
spectre tb_alu8.scs +aps -format psfxl -raw ./psf
spectre tb_alu8_noiso.scs +aps -format psfxl -raw ./psf_noiso
```

Check the results with OCEAN:

```text
ocean
> resDir = "./psf"
> load("alu8_check.ocn")
> resDir = "./psf_noiso"
> load("alu8_check.ocn")
```

The script prints one line per vector (`PASS`/`FAIL`), the average power of each block, energy per
operation, and the worst-case carry-ripple delay. To look at waveforms, open `./psf` in Virtuoso
Visualization & Analysis (*Tools → Visualization & Analysis XL*, *File → Open Results*).

## 4. Schematic flow in Virtuoso (what the project report shows)

### 4.1 Library
*File → New → Library* → `ALU8_LP`, **Attach to an existing technology library** → `gpdk045`.

### 4.2 Draw the cells (schematic + symbol each)
Draw each cell exactly as listed in `cells.scs`. Each line `MNx (d g s b) model w= l=` is one transistor:
drain, gate, source, bulk. Every pmos bulk goes to `vdd` and every nmos bulk to `vss`. Add pins `vdd` and `vss`
to every cell, then *Create → Cellview → From Cellview* to make the symbol.

| Cell | Transistors | Structure |
|---|---|---|
| inv | 2 | static CMOS |
| nand2 / nor2 | 4 | static CMOS |
| and2 / or2 | 6 | nand2/nor2 + inv. The and2 is also the **operand-isolation gate** |
| xor2 / xnor2 | 12 | 2 input inverters + complementary pull-up/pull-down |
| mux2 | 6 | 2 transmission gates + select inverter |
| mux4 | 22 | 3 × mux2 tree + 2-inverter restoring buffer |
| fa | 28 | **mirror full adder**: carry stage (10T), sum stage (14T), 2 output inverters |
| buf | 4 | 2 inverters |

Test every cell alone before you build blocks. Drive the inputs with `vpulse` sources at periods 2 ns / 4 ns / 8 ns
so all input combinations appear, and compare against the truth table.

### 4.3 Build the blocks
`alu8.scs` is grouped by block (`// ---- ctrl / arith / mul / logic / shift`). Draw one schematic per block, using
**iterated instances** (`I0<7:0>`) and **bus names** (`A<7:0>`) so you don't place 8 copies by hand:

| Block | Contents |
|---|---|
| `decoder` | 4 inv, nand/nor/and/or gates. Outputs `EN_ARITH EN_MUL EN_LOGIC EN_SHIFT WE` |
| `iso` | `ISO_EN_x = EN_x OR ISO_OFF`, then and2 × 8 per operand per block (`ar_a<7:0> = A<7:0> · ISO_EN_AR`) |
| `arith8` | per bit: and2 (pass B) → xor2 (invert B) → fa; ripple carry `ar_c<0>`→`ar_c<8>`; `V = c8 XOR c7` |
| `mul8` | 64 and2 partial products + 7 rows × 8 fa (array multiplier). Low byte → mux, high byte → `YH` |
| `logic8` | per bit: inv, nand2, nor2, xnor2 → mux4 (sel = OP1 OP0) → xor2 with `nOP3` |
| `shift8` | per bit: mux2 (sel = OP0) + buf; `fill = OP1 · A7` feeds bit 0 for ROL |
| `outmux` | 8 × mux4 for Y, 8 × and2 for YH, mux4 for C and V, NOR tree for Z, `N = Y7 · nEN_MUL` |

The node names in `alu8.scs` match the web simulator, so when you are unsure about a connection,
open the simulator and look at the same node.

**Shortcut:** Virtuoso can create schematics from a netlist (*File → Import → Spectre* or *CDL In*,
depending on your version). The generated schematic works but looks messy. It is good for checking your
hand-drawn version with LVS-style comparison, not for the report figures.

### 4.4 Testbench schematic and ADE Explorer
1. New cell `tb_alu8` (schematic). Place the `alu8` symbol.
2. Supplies: five `vdc` = `vdd` (design variable) on `vdd_ctrl … vdd_shift`, `vss` to `gnd`. `ISO_OFF` from a
   `vdc` = `isooff*vdd`.
3. Inputs: one `vpwl` per input. The PWL points are in `tb_alu8.scs` (the `wave=[ … ]` of each `V*_raw`
   source, in volts for 1 V; multiply by `vdd`). Alternatively include `tb_alu8.scs` stimulus lines with
   *Setup → Simulation Files → Definition files*.
4. Load: 5 fF on every output.
5. ADE Explorer: *Setup → Model Libraries* → gpdk045 file, section `tt`. Analysis **tran**, stop = `300n`,
   errpreset = moderate. Design variables `vdd = 1.0`, `isooff = 0`.
6. Outputs: plot `A<7:0> B<7:0> OP<3:0> Y<7:0> YH<7:0> C Z N V WE`. Save the supply currents:
   *Outputs → Save All → select currents for all terminals*, or add `I("/V0/PLUS")` style expressions.

## 5. Measurements for the report

All of these use the ADE calculator (or the OCEAN script, which does the same):

| Quantity | How |
|---|---|
| Functional check | Sample each output at `(k+1)·10 ns − 1 ns` and compare with the table in section 6 |
| Worst-case delay | Vector 1 is `ADD FF + 01`: the carry ripples through all 8 adders. `delay(A0 rising at 10 ns → Z rising)`, threshold vdd/2 |
| Multiplier delay | Vector 11 `MUL FF × FF`: input edge at 110 ns → last `YH` bit settles |
| Average power per block | `-average(IT("/Varith/PLUS")) * vdd` (repeat for each supply) |
| Total power and energy/op | Sum of the five; energy/op = P × 10 ns |
| Isolation saving | Run with `isooff = 0` and `isooff = 1`. Saving = 1 − P(on)/P(off) |
| Voltage scaling | Parametric sweep `vdd = 0.8, 0.9, 1.0`. Check the functional table still passes and note delay vs power |

### Results table to fill in

| Configuration | P_ctrl | P_arith | P_mul | P_logic | P_shift | P_total | E/op | t_d (ADD FF+01) |
|---|---|---|---|---|---|---|---|---|
| VDD 1.0 V, isolation ON | | | | | | | | |
| VDD 1.0 V, isolation OFF | | | | | | | | |
| VDD 0.8 V, isolation ON | | | | | | | | |

The web simulator estimates about a **37 % switching-energy saving** from operand isolation over this test program
(estimate from fan-out capacitance). Your Spectre numbers are the measured result; they will include leakage
and short-circuit current, which the estimate leaves out.

## 6. Expected outputs (golden model)

Each vector is held for 10 ns. Values in hex. Flags: C carry/no-borrow, Z zero, N negative, V overflow, WE write enable.

| # | t (ns) | OP | A | B | Y | Y_HI | C | Z | N | V | WE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0–10 | 0000 ADD | 2D | 17 | 44 | 00 | 0 | 0 | 0 | 0 | 1 |
| 1 | 10–20 | 0000 ADD | FF | 01 | 00 | 00 | 1 | 1 | 0 | 0 | 1 |
| 2 | 20–30 | 0000 ADD | 7F | 01 | 80 | 00 | 0 | 0 | 1 | 1 | 1 |
| 3 | 30–40 | 0001 SUB | 2D | 17 | 16 | 00 | 1 | 0 | 0 | 0 | 1 |
| 4 | 40–50 | 0001 SUB | 17 | 2D | EA | 00 | 0 | 0 | 1 | 0 | 1 |
| 5 | 50–60 | 0001 SUB | 80 | 01 | 7F | 00 | 1 | 0 | 0 | 1 | 1 |
| 6 | 60–70 | 0010 INC | 0F | 00 | 10 | 00 | 0 | 0 | 0 | 0 | 1 |
| 7 | 70–80 | 0010 INC | FF | 00 | 00 | 00 | 1 | 1 | 0 | 0 | 1 |
| 8 | 80–90 | 0011 DEC | 10 | 00 | 0F | 00 | 1 | 0 | 0 | 0 | 1 |
| 9 | 90–100 | 0011 DEC | 00 | 00 | FF | 00 | 0 | 0 | 1 | 0 | 1 |
| 10 | 100–110 | 0100 MUL | 0C | 0B | 84 | 00 | 0 | 0 | 0 | 0 | 1 |
| 11 | 110–120 | 0100 MUL | FF | FF | 01 | FE | 1 | 0 | 0 | 1 | 1 |
| 12 | 120–130 | 0100 MUL | 10 | 10 | 00 | 01 | 1 | 0 | 0 | 1 | 1 |
| 13 | 130–140 | 0101 AND | CA | 5F | 4A | 00 | 0 | 0 | 0 | 0 | 1 |
| 14 | 140–150 | 0110 OR | CA | 5F | DF | 00 | 0 | 0 | 1 | 0 | 1 |
| 15 | 150–160 | 0111 XOR | CA | 5F | 95 | 00 | 0 | 0 | 1 | 0 | 1 |
| 16 | 160–170 | 0111 XOR | AA | AA | 00 | 00 | 0 | 1 | 0 | 0 | 1 |
| 17 | 170–180 | 1000 NOT | CA | 00 | 35 | 00 | 0 | 0 | 0 | 0 | 1 |
| 18 | 180–190 | 1001 NAND | CA | 5F | B5 | 00 | 0 | 0 | 1 | 0 | 1 |
| 19 | 190–200 | 1010 NOR | CA | 5F | 20 | 00 | 0 | 0 | 0 | 0 | 1 |
| 20 | 200–210 | 1011 XNOR | CA | 5F | 6A | 00 | 0 | 0 | 0 | 0 | 1 |
| 21 | 210–220 | 1100 SHL | 81 | 00 | 02 | 00 | 1 | 0 | 0 | 0 | 1 |
| 22 | 220–230 | 1101 SHR | 81 | 00 | 40 | 00 | 1 | 0 | 0 | 0 | 1 |
| 23 | 230–240 | 1110 ROL | 81 | 00 | 03 | 00 | 1 | 0 | 0 | 0 | 1 |
| 24 | 240–250 | 1110 ROL | 40 | 00 | 80 | 00 | 0 | 0 | 1 | 0 | 1 |
| 25 | 250–260 | 1111 CMP | 37 | 37 | 00 | 00 | 1 | 1 | 0 | 0 | 0 |
| 26 | 260–270 | 1111 CMP | 10 | 20 | F0 | 00 | 0 | 0 | 1 | 0 | 0 |
| 27 | 270–280 | 1111 CMP | 20 | 10 | 10 | 00 | 1 | 0 | 0 | 0 | 0 |
| 28 | 280–290 | 0000 ADD | 00 | 00 | 00 | 00 | 0 | 1 | 0 | 0 | 1 |
| 29 | 290–300 | 0100 MUL | A5 | 5A | 02 | 3A | 1 | 0 | 0 | 1 | 1 |

## 7. Low-power techniques used (for the report)

1. **Operand isolation.** The decoder enables one block at a time. AND gates hold the inputs of the idle
   blocks at 0, so their internal nodes stop switching. The multiplier alone has 1,982 of the 3,738 transistors,
   so keeping it quiet during ADD or logic operations saves the most energy. `ISO_OFF` lets you measure the
   design with and without this technique.
2. **Gated control signals.** The adder's invert and carry-in controls are also ANDed with the enable, so
   the idle adder sits at all-zeros.
3. **Transmission-gate multiplexers.** A TG mux needs 6 transistors where a static CMOS mux needs 12, which
   means less switched capacitance in the output mux, logic unit and shifter. A buffer after each 4:1 mux restores
   the logic levels.
4. **Mirror full adder (28T).** It has symmetric pull-up and pull-down networks and no more than 3 transistors in
   series, so it switches with less capacitance than a gate-level (XOR/AND/OR) adder.
5. **Minimum-size transistors.** Wn = 120 nm and Wp = 240 nm. Dynamic power is proportional to C, and C is proportional to W.
6. **Voltage scaling.** P_dyn = α·C·V²·f, so going from 1.0 V to 0.8 V cuts dynamic energy by 36 % at the cost of
   longer delay. Section 5 shows how to measure it.
7. **Separate supply rails per block.** These measure each block's power and show where the energy goes. In a real
   chip, the same split would allow power gating of the multiplier.

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `model g45n1svt not found` | Wrong model name or section. Redo section 2 and regenerate with `--nmos/--pmos/--section` |
| Outputs stuck at mid-rail | Check that every cell has `vdd`/`vss` pins connected and that the pmos bulks go to `vdd` |
| Wrong result only at high speed | Increase the 10 ns period (edit `T_PERIOD_NS` in `gen_netlist.py`) or check the MUL delay |
| Convergence warnings | Use `errpreset=conservative`, or add `gmin=1e-12` in `simulatorOptions` |
| Want to change the circuit | Edit `model/alu_gates.py`, then run `python model/alu_model.py`, `python virtuoso/gen_netlist.py`, `python virtuoso/switch_sim.py` and `python simulator/build_sim.py`, in that order |

# Setup guide: Low-Power 8-Bit ALU

This guide is for anyone who receives this project. Follow the part you need:

- **Part A:** just look at the website (2 minutes, nothing to install)
- **Part B:** get the files and run the checks on your computer (10 minutes)
- **Part C:** simulate the ALU in Cadence Virtuoso / Spectre (lab machine)
- **Part D:** change the design, rebuild and publish

---

## What this project is

An 8-bit arithmetic logic unit (ALU) designed from CMOS transistors for the VLSI project
**"Design and Simulation of a Low-Power 8-Bit ALU in Cadence"**.

- 16 operations chosen by a 4-bit opcode: ADD, SUB, INC, DEC, MUL, AND, OR, XOR, NOT, NAND, NOR, XNOR, SHL, SHR, ROL, CMP
- Flags: C (carry), Z (zero), N (negative), V (overflow), WE (write enable)
- 341 CMOS cells, 3,738 transistors, gpdk045 (45 nm), 1.0 V
- Low-power techniques: operand isolation, transmission-gate muxes, mirror adder, minimum sizing, voltage scaling

---

## Part A: view the website

Open **https://afzalkhan001.github.io/low-power-8bit-ALU/**

The site has these pages (use the menu at the top):

| Page | What is on it |
|---|---|
| Overview | Abstract, objectives and specification |
| Start here | 13 beginner chapters with clickable demos: binary, adding, negative numbers, gates, transistors, power, Cadence. Read this first if you are new. |
| Virtual lab | Flip bits, pick an opcode and see every 0 and 1 inside the circuit |
| Architecture | Block diagram, transistor diagrams of the cells, decoder equations |
| Cadence flow | The exact commands to run the simulation |
| Results | What has been verified, the expected outputs, and a table for your own measurements |
| Netlists | Every simulation file, ready to copy |

Offline, the same website is the single file `website/index.html`. Double-click it to open it in any browser.

---

## Part B: get the files and run the checks

### 1. Install the tools

| Tool | Needed for | Get it |
|---|---|---|
| Git | downloading the project | https://git-scm.com/downloads |
| Python 3.8 or newer | checks and regenerating netlists | https://www.python.org/downloads (on Windows, tick **"Add Python to PATH"**) |
| Node.js (optional) | testing the website's engine | https://nodejs.org |

No extra Python packages are needed.

### 2. Download the project

```bash
git clone https://github.com/Afzalkhan001/low-power-8bit-ALU.git
```

```bash
cd low-power-8bit-ALU
```

Without Git: open the GitHub page, click **Code → Download ZIP**, and unzip it.

### 3. Run the checks

On Linux and macOS, type `python3` instead of `python`.

Check the gate-level design against ordinary math, for all 16 operations × 65,536 input pairs (takes about 20 seconds):

```bash
python model/alu_model.py
```

Expected last line: `RESULT: PASS - 0 mismatches`

Regenerate the Spectre netlists:

```bash
python virtuoso/gen_netlist.py
```

Check the transistor netlist (every transistor treated as an on/off switch):

```bash
python virtuoso/switch_sim.py
```

Expected last line: `SWITCH-LEVEL RESULT: PASS (60/60 vectors)`

Optional, with Node.js installed, check the website's engine against the Python model:

```bash
node simulator/test_engine.js
```

---

## Part C: simulate in Cadence (Virtuoso / Spectre)

Do this on the Linux machine that has Cadence. The full guide is `docs/virtuoso_guide.md`, and the website's **Cadence flow** page has the same steps with copy buttons.

### 1. Copy the project to the Cadence machine
Clone it there (Part B, step 2) or copy the folder over.

### 2. Find your PDK's model names
Model names differ between PDK installs. To find yours:
1. Start Virtuoso and place one `nmos` from your gpdk045 library in any schematic.
2. In ADE, choose **Simulation → Netlist → Display**.
3. Note the **model name** on the transistor line (for example `g45n1svt`), and the **include path and section** at the top of the netlist.

### 3. Regenerate the netlists for your PDK
Put in your own path and section:

```bash
cd virtuoso
```

```bash
python3 gen_netlist.py --pdk gpdk045 --model-file /your/path/gpdk045/models/spectre/gpdk045.scs --section tt
```

If your model names are different, add `--nmos NAME --pmos NAME`. Other presets are `--pdk gpdk090` (1.2 V) and `--pdk gpdk180` (1.8 V).

### 4. Run Spectre, once with operand isolation on and once with it off

```bash
spectre tb_alu8.scs +aps -format psfxl -raw ./psf
```

```bash
spectre tb_alu8_noiso.scs +aps -format psfxl -raw ./psf_noiso
```

### 5. Check the results automatically
Start `ocean` in the same folder, then type:

```text
resDir = "./psf"
load("alu8_check.ocn")
resDir = "./psf_noiso"
load("alu8_check.ocn")
```

It prints PASS or FAIL for each of the 30 test vectors, the power of each block, energy per operation and the worst-case delay. Write these numbers into the table on the website's **Results** page, then use **Copy as table** to paste them into your report.

### 6. Draw the schematics (for the report)
Follow section 4 of `docs/virtuoso_guide.md`:
1. Create a library (`ALU8_LP`) attached to gpdk045.
2. Draw each cell from `virtuoso/cells.scs` and test it on its own.
3. Build the blocks and the testbench.
4. Run it in ADE Explorer.

---

## Part D: change the design, rebuild and publish

The whole circuit is described in one file: **`model/alu_gates.py`**. After you edit it, run these in order:

```bash
python model/alu_model.py
```

```bash
python virtuoso/gen_netlist.py
```

```bash
python virtuoso/switch_sim.py
```

```bash
python simulator/build_sim.py
```

```bash
python website/build_site.py
```

To change the website's text, edit the files in `website/src/` (not `website/index.html`, which is generated), then run the last two commands.

**Publishing:** push to the `main` branch. The workflow in `.github/workflows/deploy-website.yml` copies `website/index.html` to the `gh-pages` branch, and GitHub Pages serves it within about a minute.

If the website does not appear after the first push, open the repository on GitHub, go to **Settings → Pages**, and set **Source: Deploy from a branch**, **Branch: gh-pages**, folder **/ (root)**.

---

## Folder map

| Folder / file | Contents |
|---|---|
| `model/` | `alu_gates.py`, the circuit. `alu_model.py`, the golden model and checks. Test vectors. |
| `virtuoso/` | Spectre netlists (`cells.scs`, `alu8.scs`), testbenches, OCEAN script, generator, switch-level checker |
| `simulator/` | Standalone virtual lab page and its gate engine |
| `website/` | The project website: `index.html` (generated) and `src/` (what you edit) |
| `docs/virtuoso_guide.md` | Detailed Cadence guide, expected output table, low-power techniques |
| `README.md` | Short project summary |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` is not recognized | Reinstall Python with **Add Python to PATH** ticked, or use `py` on Windows or `python3` on Linux and macOS |
| Spectre says `model g45n1svt not found` | Redo Part C step 2 and regenerate with `--nmos`, `--pmos` and `--section` |
| Spectre cannot open the model file | The `--model-file` path is wrong. Ask your lab admin where gpdk045 is installed |
| OCEAN prints FAIL at high speed | The circuit is slower than 10 ns per vector at your corner. Raise `T_PERIOD_NS` in `virtuoso/gen_netlist.py` and regenerate |
| Website page is blank | Use a current Chrome, Edge or Firefox. Fonts need internet; without it the page uses system fonts but still works |
| GitHub Pages shows 404 | Wait 2 minutes, then check **Settings → Pages** as described in Part D |

## Status

| Check | Result |
|---|---|
| Gate-level design vs math, 1,048,576 cases | PASS, 0 mismatches |
| Transistor netlist, switch-level, 60 runs | PASS |
| Website engine vs Python model | PASS |
| Spectre transient: delay and power | To be run on Cadence (Part C) |

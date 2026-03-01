# fsmgen 🔄

**Modern Python CLI for generating synthesizable Verilog state machines from YAML.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Verified on FPGA](https://img.shields.io/badge/Verified-Spartan--7%20FPGA-brightgreen.svg)](#fpga-verification)

---

## 🌳 Roots & Inspiration

This project stands on the shoulders of [**Fizzim**](https://github.com/zimmerdesignservices/fizzim), a venerable Java-based FSM design tool that has served the digital design community for years. Fizzim pioneered the graphical approach to state machine design with automatic Verilog generation.

Recently, a call went out for enhancements to Fizzim:
- **Nested states** (hierarchical FSMs / superstates)
- **Forked decision trees** (parallel conditional branching)

This sparked an idea: rather than patch a Java Swing GUI, why not reimagine FSM-to-Verilog generation for the modern era?

---

## 💡 Motivation

**The world has changed since Fizzim was created:**

1. **Engineers don't want GUIs for everything.** We want scriptable, repeatable, CI/CD-friendly tools. Define your state machine in a simple YAML file, version control it, and generate Verilog deterministically.

2. **AI agents are writing code now.** LLMs and agentic workflows can easily generate YAML. They struggle with clicking through Java Swing dialogs. `fsmgen` is designed to slot directly into AI-assisted hardware design flows.

3. **Python is the lingua franca.** Every engineer has Python. `pip install fsmgen` and you're generating Verilog in seconds.

4. **Nested states and forked decisions shouldn't require a consultation agreement.** These are fundamental FSM patterns. They should just work.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **YAML-based FSM definition** | Human-readable, version-controllable, AI-friendly |
| **3-always-block Verilog** | Industry-standard synthesizable style |
| **Nested states** | Hierarchical FSMs with automatic parent-active signals |
| **Forked decision trees** | Multiple conditions evaluated from a single state |
| **Automatic I/O inference** | Inputs and outputs derived from your FSM spec |
| **Testbench generation** | Optional `--testbench` flag for simulation |
| **Zero dependencies hell** | Just `click` and `pyyaml` |

---

## 🚀 Quick Start

### Installation

```bash
pip install fsmgen
```

Or from source:
```bash
git clone https://github.com/HankJediAssistant/fsmgen.git
cd fsmgen
pip install .
```

### Basic Usage

**1. Define your FSM in YAML:**

```yaml
# simple_fsm.yaml
fsm:
  name: traffic_light
  clock: clk
  reset: rst
  states:
    RED:
      outputs: {red: 1, yellow: 0, green: 0}
      transitions:
        - to: GREEN
          when: timer_done
    GREEN:
      outputs: {red: 0, yellow: 0, green: 1}
      transitions:
        - to: YELLOW
          when: timer_done
    YELLOW:
      outputs: {red: 0, yellow: 1, green: 0}
      transitions:
        - to: RED
          when: timer_done
```

**2. Generate Verilog:**

```bash
fsmgen generate simple_fsm.yaml -o traffic_light.v
```

**3. Get synthesizable RTL:**

```verilog
module traffic_light (
    input  wire clk,
    input  wire rst,
    input  wire timer_done,
    output reg  green,
    output reg  red,
    output reg  yellow
);

localparam RED              = 2'd0;
localparam GREEN            = 2'd1;
localparam YELLOW           = 2'd2;

reg [1:0] state, next_state;

// State register
always @(posedge clk) begin
    if (rst)
        state <= RED;
    else
        state <= next_state;
end

// Next-state logic
always @(*) begin
    next_state = state;
    case (state)
        RED: begin
            if (timer_done)
                next_state = GREEN;
        end
        GREEN: begin
            if (timer_done)
                next_state = YELLOW;
        end
        YELLOW: begin
            if (timer_done)
                next_state = RED;
        end
        default: ;
    endcase
end

// Output logic
always @(*) begin
    red = 1'd0; yellow = 1'd0; green = 1'd0;
    case (state)
        RED:    begin red = 1'd1; end
        GREEN:  begin green = 1'd1; end
        YELLOW: begin yellow = 1'd1; end
        default: ;
    endcase
end

endmodule
```

---

## 🏗️ Advanced Features

### Nested States (Hierarchical FSMs)

Define substates within a parent state. The parent is considered "active" when any child is active.

```yaml
fsm:
  name: processor
  clock: clk
  reset: rst
  states:
    IDLE:
      transitions:
        - to: PROCESSING.INIT
          when: start
    PROCESSING:
      substates:
        INIT:
          transitions:
            - to: PROCESSING.RUN
              when: init_done
        RUN:
          transitions:
            - to: DONE
              when: complete
      transitions:
        - to: IDLE
          when: abort  # Can abort from any substate
    DONE:
      transitions:
        - to: IDLE
          when: ack
```

Generates a `processing_active` signal automatically:
```verilog
wire processing_active = (state == PROCESSING_INIT) || (state == PROCESSING_RUN);
```

### Forked Decision Trees

Evaluate multiple conditions in parallel from a single state:

```yaml
fsm:
  name: packet_router
  clock: clk
  reset: rst
  states:
    CLASSIFY:
      fork:
        - condition: is_urgent
          to: FAST_PATH
        - condition: is_normal
          to: SLOW_PATH
        - default: DROP
```

Generates clean priority-encoded logic:
```verilog
CLASSIFY: begin
    if (is_urgent)
        next_state = FAST_PATH;
    else if (is_normal)
        next_state = SLOW_PATH;
    else
        next_state = DROP;
end
```

---

## 🔬 FPGA Verification

This tool has been **verified on real hardware**:

- **FPGA:** Digilent Cmod S7 (Xilinx Spartan-7 XC7S25)
- **Toolchain:** Vivado 2025.2
- **Result:** 0 errors, 0 warnings, timing clean

The generated Verilog synthesizes cleanly and runs correctly on silicon.

---

## 🤖 Designed for AI Workflows

`fsmgen` is built with agentic AI in mind:

```python
# In your AI agent or LLM tool
import subprocess

yaml_content = """
fsm:
  name: ai_generated_fsm
  clock: clk
  reset: rst
  states:
    IDLE:
      transitions:
        - to: WORKING
          when: task_ready
    WORKING:
      transitions:
        - to: IDLE
          when: task_done
"""

# Write YAML
with open("fsm.yaml", "w") as f:
    f.write(yaml_content)

# Generate Verilog
subprocess.run(["fsmgen", "generate", "fsm.yaml", "-o", "output.v"])
```

No GUI clicks. No manual intervention. Just structured data in, synthesizable RTL out.

---

## 📁 Project Structure

```
fsmgen/
├── fsmgen/
│   ├── __init__.py
│   ├── cli.py          # Click-based CLI
│   ├── parser.py       # YAML FSM parser
│   ├── codegen.py      # Verilog code generator
│   └── testbench.py    # Testbench generator
├── examples/
│   ├── simple.yaml     # Basic 2-state FSM
│   ├── nested.yaml     # Nested states example
│   └── fork.yaml       # Forked decision tree example
├── pyproject.toml
└── README.md
```

---

## 🛠️ CLI Reference

```bash
# Generate Verilog from YAML
fsmgen generate <input.yaml> [-o output.v]

# Generate with testbench
fsmgen generate <input.yaml> --testbench [-o output.v]

# Show version
fsmgen --version
```

---

## 📜 License

MIT License — use it however you want.

---

## 🙏 Acknowledgments

- [**Fizzim**](https://github.com/zimmerdesignservices/fizzim) — The original FSM-to-Verilog tool that inspired this project
- The digital design community that keeps pushing for better tools

---

## 🚧 Roadmap

- [ ] SystemVerilog output option
- [ ] VHDL output
- [ ] Graphviz diagram generation
- [ ] FSM linting and validation
- [ ] Web playground

---

*Built in a weekend. Verified on silicon. Ready for production.*

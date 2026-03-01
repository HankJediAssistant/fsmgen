"""Generate 3-always-block Verilog from a parsed FSM."""

from .parser import FSM


def _fmt_val(value: int, width: int) -> str:
    """Format an integer as a sized Verilog literal."""
    return f"{width}'d{value}"


def generate_verilog(fsm: FSM) -> str:
    """Generate a complete Verilog module for the given FSM."""
    lines: list[str] = []

    # --- Module header ---
    ports = []
    ports.append(f"    input  wire {fsm.clock}")
    ports.append(f"    input  wire {fsm.reset}")
    for inp in fsm.inputs:
        ports.append(f"    input  wire {inp}")
    for i, (out_name, width) in enumerate(fsm.outputs.items()):
        if width > 1:
            ports.append(f"    output reg  [{width-1}:0] {out_name}")
        else:
            ports.append(f"    output reg  {out_name}")

    lines.append(f"module {fsm.name} (")
    lines.append(",\n".join(ports))
    lines.append(");")
    lines.append("")

    # --- State encoding ---
    for i, state in enumerate(fsm.flat_states):
        lines.append(f"localparam {state:<16s} = {_fmt_val(i, fsm.state_width)};")
    lines.append("")

    # --- State registers ---
    if fsm.state_width > 1:
        lines.append(f"reg [{fsm.state_width-1}:0] state, next_state;")
    else:
        lines.append("reg state, next_state;")
    lines.append("")

    # --- Parent-active wires (for nested states) ---
    for parent, substates in fsm.parent_groups.items():
        conds = " || ".join(f"(state == {s})" for s in substates)
        lines.append(f"wire {parent.lower()}_active = {conds};")
    if fsm.parent_groups:
        lines.append("")

    # --- Always block 1: state register ---
    lines.append("// State register")
    lines.append(f"always @(posedge {fsm.clock}) begin")
    lines.append(f"    if ({fsm.reset})")
    lines.append(f"        state <= {fsm.reset_state};")
    lines.append("    else")
    lines.append("        state <= next_state;")
    lines.append("end")
    lines.append("")

    # --- Always block 2: next-state logic ---
    lines.append("// Next-state logic")
    lines.append("always @(*) begin")
    lines.append("    next_state = state;")
    lines.append("    case (state)")

    for state in fsm.flat_states:
        transitions = fsm.state_transitions.get(state, [])
        forks = fsm.state_forks.get(state, [])

        if not transitions and not forks:
            lines.append(f"        {state}: ;")
            continue

        lines.append(f"        {state}: begin")
        first = True

        for t in transitions:
            kw = "if" if first else "else if"
            lines.append(f"            {kw} ({t.when})")
            lines.append(f"                next_state = {t.to};")
            first = False

        for f in forks:
            if f.when is not None:
                kw = "if" if first else "else if"
                lines.append(f"            {kw} ({f.when})")
                lines.append(f"                next_state = {f.to};")
                first = False
            else:
                lines.append(f"            else")
                lines.append(f"                next_state = {f.to};")

        lines.append("        end")

    lines.append("        default: ;")
    lines.append("    endcase")
    lines.append("end")
    lines.append("")

    # --- Always block 3: output logic ---
    lines.append("// Output logic")
    lines.append("always @(*) begin")

    for out_name, width in fsm.outputs.items():
        lines.append(f"    {out_name} = {_fmt_val(0, width)};")

    lines.append("    case (state)")

    for state in fsm.flat_states:
        outputs = fsm.state_outputs.get(state, {})
        if not outputs:
            lines.append(f"        {state}: ;")
            continue

        lines.append(f"        {state}: begin")
        for out_name, out_val in outputs.items():
            width = fsm.outputs[out_name]
            lines.append(f"            {out_name} = {_fmt_val(out_val, width)};")
        lines.append("        end")

    lines.append("        default: ;")
    lines.append("    endcase")
    lines.append("end")
    lines.append("")
    lines.append("endmodule")

    return "\n".join(lines) + "\n"

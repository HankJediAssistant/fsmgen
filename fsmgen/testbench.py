"""Generate a basic Verilog testbench for a parsed FSM."""

from .parser import FSM


def generate_testbench(fsm: FSM) -> str:
    """Generate a self-contained testbench with clock, reset, and VCD dump."""
    lines: list[str] = []

    lines.append("`timescale 1ns / 1ps")
    lines.append("")
    lines.append(f"module {fsm.name}_tb;")
    lines.append("")

    # --- Signal declarations ---
    lines.append(f"reg {fsm.clock};")
    lines.append(f"reg {fsm.reset};")
    for inp in fsm.inputs:
        lines.append(f"reg {inp};")
    for out_name, width in fsm.outputs.items():
        if width > 1:
            lines.append(f"wire [{width-1}:0] {out_name};")
        else:
            lines.append(f"wire {out_name};")
    lines.append("")

    # --- DUT instantiation ---
    lines.append(f"{fsm.name} dut (")
    ports = []
    ports.append(f"    .{fsm.clock}({fsm.clock})")
    ports.append(f"    .{fsm.reset}({fsm.reset})")
    for inp in fsm.inputs:
        ports.append(f"    .{inp}({inp})")
    for out_name in fsm.outputs:
        ports.append(f"    .{out_name}({out_name})")
    lines.append(",\n".join(ports))
    lines.append(");")
    lines.append("")

    # --- Clock: 10ns period ---
    lines.append(f"initial {fsm.clock} = 0;")
    lines.append(f"always #5 {fsm.clock} = ~{fsm.clock};")
    lines.append("")

    # --- Stimulus ---
    lines.append("initial begin")
    lines.append(f'    $dumpfile("{fsm.name}_tb.vcd");')
    lines.append(f"    $dumpvars(0, {fsm.name}_tb);")
    lines.append("")
    lines.append("    // Reset")
    lines.append(f"    {fsm.reset} = 1;")
    for inp in fsm.inputs:
        lines.append(f"    {inp} = 0;")
    lines.append("    #20;")
    lines.append(f"    {fsm.reset} = 0;")
    lines.append("")
    lines.append("    // TODO: Add test stimulus here")
    lines.append("    #200;")
    lines.append("")
    lines.append("    $display(\"Testbench complete.\");")
    lines.append("    $finish;")
    lines.append("end")
    lines.append("")
    lines.append("endmodule")

    return "\n".join(lines) + "\n"

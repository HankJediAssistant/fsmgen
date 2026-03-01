"""Click CLI for fsmgen."""

from pathlib import Path

import click

from . import __version__
from .codegen import generate_verilog
from .parser import parse_yaml
from .testbench import generate_testbench


@click.group()
@click.version_option(__version__)
def cli():
    """fsmgen - Generate Verilog state machines from YAML."""


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path),
              help="Output Verilog file (default: stdout)")
@click.option("--tb", is_flag=True, help="Also generate a testbench")
def generate(input_file: Path, output: Path | None, tb: bool):
    """Generate Verilog from a YAML FSM description."""
    fsm = parse_yaml(input_file)
    verilog = generate_verilog(fsm)

    if output:
        output.write_text(verilog)
        click.echo(f"Wrote {output}")
    else:
        click.echo(verilog, nl=False)

    if tb:
        tb_code = generate_testbench(fsm)
        if output:
            tb_path = output.with_name(output.stem + "_tb.v")
        else:
            tb_path = Path(f"{fsm.name}_tb.v")
        tb_path.write_text(tb_code)
        click.echo(f"Wrote testbench {tb_path}")

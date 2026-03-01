"""Parse YAML FSM descriptions into an intermediate representation."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Transition:
    to: str
    when: str


@dataclass
class ForkBranch:
    to: str
    when: str | None = None  # None = default branch


@dataclass
class FSM:
    name: str
    clock: str
    reset: str
    reset_state: str
    flat_states: list[str]
    state_outputs: dict[str, dict[str, int]]
    state_transitions: dict[str, list[Transition]]
    state_forks: dict[str, list[ForkBranch]]
    inputs: list[str]
    outputs: dict[str, int]  # output_name -> bit width
    parent_groups: dict[str, list[str]]  # parent -> [substates]
    entry_states: dict[str, str]  # parent -> first substate
    state_width: int


_VERILOG_KEYWORDS = {
    "and", "or", "not", "xor", "nand", "nor", "xnor",
    "begin", "end", "if", "else", "case", "endcase",
    "module", "endmodule", "input", "output", "wire", "reg",
}


def _extract_signals(condition: str) -> set[str]:
    """Extract signal names from a Verilog condition expression."""
    cleaned = re.sub(r"\d+'[bBhHdDoO][0-9a-fA-F_xXzZ]+", "", str(condition))
    tokens = re.findall(r"[a-zA-Z_]\w*", cleaned)
    return {t for t in tokens if t not in _VERILOG_KEYWORDS}


def parse_yaml(path: str | Path) -> FSM:
    """Parse a YAML file into an FSM intermediate representation."""
    with open(path) as f:
        data = yaml.safe_load(f)

    fsm_data = data["fsm"]
    name = fsm_data["name"]
    clock = fsm_data.get("clock", "clk")
    reset = fsm_data.get("reset", "rst")

    flat_states: list[str] = []
    state_outputs: dict[str, dict[str, int]] = {}
    state_transitions: dict[str, list[Transition]] = {}
    state_forks: dict[str, list[ForkBranch]] = {}
    parent_groups: dict[str, list[str]] = {}
    entry_states: dict[str, str] = {}
    parent_transitions: dict[str, list[Transition]] = {}
    all_output_maxvals: dict[str, int] = {}
    all_inputs: set[str] = set()
    reset_state: str | None = None

    def _track_output(out_name: str, out_val: int):
        if out_name not in all_output_maxvals:
            all_output_maxvals[out_name] = out_val
        else:
            all_output_maxvals[out_name] = max(all_output_maxvals[out_name], out_val)

    def _process_states(states_dict: dict, parent_name: str | None = None,
                        parent_outputs: dict | None = None) -> str:
        nonlocal reset_state
        first_state = None

        for state_name, state_data in states_dict.items():
            state_data = state_data or {}

            if first_state is None:
                first_state = state_name

            # Merge parent outputs with this state's outputs
            outputs = dict(parent_outputs) if parent_outputs else {}
            outputs.update(state_data.get("outputs", {}))
            for k, v in outputs.items():
                _track_output(k, v)

            has_substates = "substates" in state_data

            if has_substates:
                parent_groups[state_name] = []

                # Parent-level transitions apply from any substate
                if "transitions" in state_data:
                    parent_transitions[state_name] = []
                    for t in state_data["transitions"]:
                        parent_transitions[state_name].append(
                            Transition(to=t["to"], when=t["when"]))
                        all_inputs.update(_extract_signals(t["when"]))

                sub_first = _process_states(state_data["substates"], state_name, outputs)
                entry_states[state_name] = sub_first
            else:
                flat_states.append(state_name)
                state_outputs[state_name] = outputs

                if parent_name is not None:
                    parent_groups[parent_name].append(state_name)

                if reset_state is None and parent_name is None:
                    reset_state = state_name

                # Transitions
                transitions = []
                for t in state_data.get("transitions", []):
                    transitions.append(Transition(to=t["to"], when=t["when"]))
                    all_inputs.update(_extract_signals(t["when"]))
                state_transitions[state_name] = transitions

                # Fork branches
                if "fork" in state_data:
                    forks = []
                    for f in state_data["fork"]:
                        if "default" in f:
                            forks.append(ForkBranch(to=f["default"]))
                        else:
                            forks.append(ForkBranch(to=f["to"], when=f["when"]))
                            all_inputs.update(_extract_signals(f["when"]))
                    state_forks[state_name] = forks

        return first_state

    first_top = list(fsm_data["states"].keys())[0]
    _process_states(fsm_data["states"])

    # Default reset state: first top-level state (or its entry substate)
    if reset_state is None:
        reset_state = entry_states.get(first_top, first_top)

    def _resolve_target(target: str) -> str:
        return entry_states.get(target, target)

    # Apply parent transitions to all substates (lower priority = appended after)
    for parent_name, substates in parent_groups.items():
        if parent_name in parent_transitions:
            for sub in substates:
                resolved = [Transition(to=_resolve_target(t.to), when=t.when)
                            for t in parent_transitions[parent_name]]
                state_transitions[sub] = state_transitions.get(sub, []) + resolved

    # Resolve all targets that point to parent states -> entry substate
    for state_name in flat_states:
        state_transitions[state_name] = [
            Transition(to=_resolve_target(t.to), when=t.when)
            for t in state_transitions.get(state_name, [])
        ]
        if state_name in state_forks:
            state_forks[state_name] = [
                ForkBranch(to=_resolve_target(f.to), when=f.when)
                for f in state_forks[state_name]
            ]

    # Compute output bit widths
    output_widths = {}
    for out_name, max_val in all_output_maxvals.items():
        output_widths[out_name] = max(1, max_val.bit_length()) if max_val > 0 else 1

    # State encoding width
    n = len(flat_states)
    state_width = max(1, (n - 1).bit_length()) if n > 1 else 1

    # Inputs = all referenced signals minus clock, reset, and outputs
    reserved = {clock, reset} | set(output_widths.keys())
    inputs = sorted(all_inputs - reserved)

    return FSM(
        name=name,
        clock=clock,
        reset=reset,
        reset_state=reset_state,
        flat_states=flat_states,
        state_outputs=state_outputs,
        state_transitions=state_transitions,
        state_forks=state_forks,
        inputs=inputs,
        outputs=output_widths,
        parent_groups=parent_groups,
        entry_states=entry_states,
        state_width=state_width,
    )

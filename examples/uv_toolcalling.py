"""
Uv tool-calling example — running skill tools via ``uv run``.

This example shows how to call a skill's bundled calculator tools via
subprocess + ``uv run`` instead of dynamically importing code. This is
the **secure** approach: no arbitrary code execution, no ``importlib``
tricks — the skill script runs in an isolated ``uv`` environment and
communicates via JSON on stdout.

Flow:

1. Retrieve the ``q-range-basics`` skill to locate its directory.
2. Call ``uv run <skill>/scripts/q_range_tools.py <subcommand> ...``
   for each calculation needed.
3. Parse the JSON output.
4. Print a human-readable summary.

Usage::

    python examples/uv_toolcalling.py

    python examples/uv_toolcalling.py \\
        --two-theta-deg 0.5 --wavelength 6.0

Requirements:
- ``uv`` installed and on PATH (https://docs.astral.sh/uv/)
- ``pip install -e .`` (core package only, no extras needed)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from neutron_skills import retrieve


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_script(skill_directory: Path, script_name: str) -> Path:
    """Locate a script inside the skill's ``scripts/`` directory."""
    candidate = skill_directory / "scripts" / script_name
    if not candidate.exists():
        raise FileNotFoundError(
            f"Script '{script_name}' not found in {skill_directory / 'scripts'}. "
            "Check that the skill directory is correct."
        )
    return candidate


def _run_tool(script_path: Path, subcommand: str, args: list[str]) -> dict:
    """
    Run a subcommand of a PEP 723 tool script with ``uv run`` and return JSON.

    uv creates an isolated environment, installs the inline-declared
    dependencies, and executes the script.
    """
    cmd = ["uv", "run", str(script_path), subcommand, *args]
    print(f"  [uv] {' '.join(cmd)}", file=sys.stderr)

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=None,  # inherit — lets uv's progress show
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Tool exited with code {result.returncode}. "
            "See stderr output above for details."
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Tool output could not be parsed as JSON.\n"
            f"Raw output:\n{result.stdout[:500]}"
        ) from exc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


_DEFAULT_WAVELENGTH = 6.0
_DEFAULT_TWO_THETA = 0.5


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--wavelength",
        type=float,
        default=_DEFAULT_WAVELENGTH,
        metavar="AA",
        help=f"Neutron wavelength in Å (default: {_DEFAULT_WAVELENGTH})",
    )
    parser.add_argument(
        "--two-theta-deg",
        type=float,
        default=_DEFAULT_TWO_THETA,
        metavar="DEG",
        dest="two_theta_deg",
        help=f"Full scattering angle 2θ in degrees (default: {_DEFAULT_TWO_THETA})",
    )
    args = parser.parse_args(argv)

    # 1. Retrieve the skill to find its directory on disk
    print("Retrieving q-range-basics skill …")
    skills = retrieve("Q range planning wavelength scattering angle")
    skill = next((s for s in skills if s.name == "q-range-basics"), None)
    if skill is None:
        print(
            "Error: q-range-basics skill not found. "
            "Make sure the package is installed with 'pip install -e .'",
            file=sys.stderr,
        )
        return 1

    print(f"  skill directory: {skill.directory}")

    # 2. Locate the tool script
    script_path = _find_script(Path(skill.directory), "q_range_tools.py")
    print(f"  script         : {script_path.name}")

    # 3. Convert 2θ → θ
    print(f"\nStep 1: Convert 2θ = {args.two_theta_deg}° to θ")
    half = _run_tool(
        script_path, "half-angle",
        ["--two-theta-deg", str(args.two_theta_deg)],
    )
    theta = half["theta_deg"]
    print(f"  θ = {theta}°")

    # 4. Compute Q
    print(f"\nStep 2: Compute Q (θ = {theta}°, λ = {args.wavelength} Å)")
    q_result = _run_tool(
        script_path, "compute-q",
        ["--theta-deg", str(theta), "--wavelength", str(args.wavelength)],
    )
    q_val = q_result["Q"]
    print(f"  Q = {q_val:.6f} Å⁻¹")

    # 5. Compute d-spacing
    print(f"\nStep 3: Compute d-spacing (Q = {q_val:.6f} Å⁻¹)")
    d_result = _run_tool(
        script_path, "compute-d-spacing",
        ["--q", str(q_val)],
    )
    d_val = d_result["d_aa"]
    print(f"  d ≈ {d_val:.1f} Å")

    # 6. Summary
    print(f"\n{'=' * 50}")
    print(f"  λ = {args.wavelength} Å   2θ = {args.two_theta_deg}°")
    print(f"  Q = {q_val:.6f} Å⁻¹")
    print(f"  d ≈ {d_val:.1f} Å  (real-space length scale probed)")
    print(f"{'=' * 50}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///

"""
CLI calculator helpers for the ``q-range-basics`` skill.

Each subcommand performs one momentum-transfer calculation and prints
a JSON result to stdout. Designed to be called via ``uv run`` from
an agent or wrapper script.

Usage::

    uv run scripts/q_range_tools.py compute-q --theta-deg 0.25 --wavelength 6.0
    uv run scripts/q_range_tools.py compute-d-spacing --q 0.00456
    uv run scripts/q_range_tools.py half-angle --two-theta-deg 0.5
"""

from __future__ import annotations

import argparse
import json
import math
import sys


# ---------------------------------------------------------------------------
# Physics helpers
# ---------------------------------------------------------------------------


def compute_q(theta_deg: float, wavelength_aa: float) -> dict[str, float]:
    """
    Compute the momentum transfer Q for elastic scattering.

    Q = 4*pi/lambda * sin(theta), with theta = (scattering angle 2*theta) / 2.

    Args:
        theta_deg: HALF the scattering angle (i.e. theta, not 2*theta), in degrees.
        wavelength_aa: Neutron wavelength in angstroms.

    Returns:
        Dict with keys ``Q`` (1/Å), ``theta_deg``, ``wavelength_aa``.
    """
    theta_rad = math.radians(theta_deg)
    q = 4.0 * math.pi / wavelength_aa * math.sin(theta_rad)
    return {"Q": q, "theta_deg": theta_deg, "wavelength_aa": wavelength_aa}


def compute_d_spacing(q_inv_aa: float) -> dict[str, float]:
    """
    Compute the real-space length scale d ≈ 2*pi / Q probed by a given Q.

    Args:
        q_inv_aa: Momentum transfer in 1/Å.

    Returns:
        Dict with keys ``d_aa`` (length scale in Å) and ``Q`` (echo).
    """
    if q_inv_aa <= 0:
        raise ValueError(f"Q must be positive, got {q_inv_aa}")
    return {"d_aa": 2.0 * math.pi / q_inv_aa, "Q": q_inv_aa}


def half_angle(two_theta_deg: float) -> dict[str, float]:
    """
    Convert a scattering angle 2*theta (degrees) into theta (degrees).

    Useful when the user reports the full scattering angle but ``compute_q``
    expects theta.

    Args:
        two_theta_deg: Scattering angle 2*theta in degrees.

    Returns:
        Dict with keys ``theta_deg`` and ``two_theta_deg`` (echo).
    """
    return {"theta_deg": two_theta_deg / 2.0, "two_theta_deg": two_theta_deg}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="q_range_tools.py",
        description="Q-range calculator tools for neutron scattering.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- compute-q -----------------------------------------------------------
    p_q = sub.add_parser(
        "compute-q",
        help="Compute momentum transfer Q from theta and wavelength.",
    )
    p_q.add_argument(
        "--theta-deg",
        type=float,
        required=True,
        metavar="DEG",
        help="HALF the scattering angle (theta, not 2*theta), in degrees.",
    )
    p_q.add_argument(
        "--wavelength",
        type=float,
        required=True,
        metavar="AA",
        help="Neutron wavelength in angstroms.",
    )

    # -- compute-d-spacing ---------------------------------------------------
    p_d = sub.add_parser(
        "compute-d-spacing",
        help="Compute real-space d ≈ 2π/Q from a given Q value.",
    )
    p_d.add_argument(
        "--q",
        type=float,
        required=True,
        metavar="INV_AA",
        help="Momentum transfer Q in 1/Å (must be positive).",
    )

    # -- half-angle ----------------------------------------------------------
    p_h = sub.add_parser(
        "half-angle",
        help="Convert 2*theta to theta.",
    )
    p_h.add_argument(
        "--two-theta-deg",
        type=float,
        required=True,
        metavar="DEG",
        help="Full scattering angle 2*theta in degrees.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "compute-q":
            result = compute_q(args.theta_deg, args.wavelength)
        elif args.command == "compute-d-spacing":
            result = compute_d_spacing(args.q)
        elif args.command == "half-angle":
            result = half_angle(args.two_theta_deg)
        else:
            parser.print_help()
            return 2
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

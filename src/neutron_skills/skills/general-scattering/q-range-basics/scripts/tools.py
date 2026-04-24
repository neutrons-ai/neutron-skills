"""
Plain-Python calculator helpers for the ``q-range-basics`` skill.

These are framework-agnostic functions. Any agent runtime can wrap them
into its own tool format. See
``examples/langchain_ollama_toolcalling.py`` for a LangChain wrapper.

Convention used by the example loader:

- Every callable to be exposed as a tool is listed in module-level
  ``TOOLS = [callable, ...]``.
- The function's docstring describes its arguments and return value;
  runtimes that build JSON schemas (LangChain, OpenAI, Anthropic, …)
  derive descriptions from it.
- Type hints are used to derive parameter schemas.
- No third-party imports — only the standard library — so the file is
  portable across runtimes.
"""

from __future__ import annotations

import math


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


TOOLS = [compute_q, compute_d_spacing, half_angle]

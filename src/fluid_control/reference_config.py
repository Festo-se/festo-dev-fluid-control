# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT
# Provenance-ID: FLUID@8da843a2bf8f846e340913e72e5c03e696455e3b
"""Access the configurator package's canonical example instrument configuration.

This package delegates the reference-config API to ``festo-dev-configurator`` so
examples and callers share its canonical superset resource. The network
addresses in that resource are illustrative and must be checked before hardware use.
"""

from typing import Any

from configurator import load_consolidated_config


def load_example_config() -> dict[str, Any]:
    """Load the configurator-owned consolidated transition config.

    Returns:
        The parsed consolidated configuration mapping.
    """
    return load_consolidated_config()

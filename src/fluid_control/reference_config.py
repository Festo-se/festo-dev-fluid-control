# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT
# Provenance-ID: FLUID@8da843a2bf8f846e340913e72e5c03e696455e3b
"""Access the configurator package's canonical example instrument configuration.

This package delegates the reference-config API to ``festo-dev-configurator`` so
examples and callers share its canonical superset resource. The network
addresses in that resource are illustrative and must be checked before hardware use.
"""

import json
from importlib.resources import files
from typing import Any

_EXAMPLE_CONFIG_RESOURCE = "data/superset-config.json"


def example_config_path() -> Any:
    """Return a traversable path to the bundled example configuration JSON.

    Returns:
        Importable-resource path to the configurator's ``superset-config.json``.
    """
    return files("configurator").joinpath(_EXAMPLE_CONFIG_RESOURCE)


def load_example_config() -> dict[str, Any]:
    """Load and return the bundled example instrument configuration.

    Returns:
        The parsed example instrument configuration.
    """
    with example_config_path().open("r", encoding="utf-8") as fh:
        return json.load(fh)

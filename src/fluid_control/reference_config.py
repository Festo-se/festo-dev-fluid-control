# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT
# Provenance-ID: FLUID@8da843a2bf8f846e340913e72e5c03e696455e3b
# TODO: Make unnecessary and remove

"""Access to the bundled example instrument configuration.

Ships a small, valid reference configuration inside the installed package so that
docstring examples, the example scripts, and end users can obtain a working
configuration without a repository checkout. The configuration contains a
``micro-dispenser`` (dispenser) and a ``pipettor`` component; its network
addresses are placeholders and must be replaced before connecting to hardware.
"""

import json
from importlib.resources import files
from typing import Any

_EXAMPLE_CONFIG_RESOURCE = "data/example-config.json"

# TODO: Remove this and write a helper in the examples that pulls this from a single repository of configs; singular source of truth so config mods happen once and are propagated
#


def example_config_path() -> Any:
    """Return a traversable path to the bundled example configuration JSON.

    Returns:
        Importable-resource path to ``example-config.json``.
    """
    return files("fluid_control").joinpath(_EXAMPLE_CONFIG_RESOURCE)


def load_example_config() -> dict[str, Any]:
    """Load and return the bundled example instrument configuration.

    Returns:
        The parsed example instrument configuration.
    """
    with example_config_path().open("r", encoding="utf-8") as fh:
        return json.load(fh)

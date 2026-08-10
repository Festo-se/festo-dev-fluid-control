# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# TODO: Make unnecessary and remove
"""
Access to the bundled example instrument configuration.

Ships a small, valid reference configuration inside the installed package so that
docstring examples, the example scripts, and end users can obtain a working
configuration without a repository checkout. The configuration contains a
``micro-dispenser`` (dispenser) and a ``pipettor`` component; its network
addresses are placeholders and must be replaced before connecting to hardware.
"""

from importlib.resources import files
from typing import Any
import json

_EXAMPLE_CONFIG_RESOURCE = "data/example-config.json"

# TODO: Remove this and write a helper in the examples that pulls this from a single repository of configs; singular source of truth so config mods happen once and are propagated
#


def example_config_path() -> Any:
    """
    Return a traversable path to the bundled example configuration JSON.

    Returns:
        Traversable: Importable-resource path to ``example-config.json``. Use
        its ``.open()`` / ``.read_text()`` methods; it may not be a real
        filesystem path when the package is installed as a zip.

    Examples:
        >>> from fluid_control import example_config_path
        >>> example_config_path().name
        'example-config.json'

    """
    return files("fluid_control").joinpath(_EXAMPLE_CONFIG_RESOURCE)


def load_example_config() -> dict[str, Any]:
    """
        Load and return the bundled example instrument configuration as a dict.

        The returned mapping is the full instrument configuration and can be passed
        directly to a device constructor. Select a component with ``component_id``
        (``"micro-dispenser"`` or ``"pipettor"``).

    Returns:
        dict: The parsed example instrument configuration.

    Examples:
        >>> from fluid_control import Dispenser, load_example_config
        >>> config = load_example_config()
        >>> dispenser = Dispenser(config=config, component_id="micro-dispenser")

    """
    with example_config_path().open("r", encoding="utf-8") as fh:
        return json.load(fh)

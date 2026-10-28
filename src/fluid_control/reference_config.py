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

from configurator.reference_config import example_config_path, load_example_config  # noqa: F401


# TODO: Remove this and write a helper in the examples that pulls this from a single repository of configs; singular source of truth so config mods happen once and are propagated
#

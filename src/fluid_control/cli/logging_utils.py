# SPDX-FileCopyrightText: 2026 Festo SE & Co. KG
# SPDX-License-Identifier: MIT

"""Runtime logging helpers for fluid-control CLI entry points.

These helpers support startup configuration and interactive log-level changes
without restarting the process.
Entirely duplicated by the logging utils in applied_motion, and will be split out
into own library eventually. Just import for maintainability.
"""

from applied_motion.cli.logging_utils import (
    current_log_level_name,
    configure_logging,
    set_runtime_log_level,
    LOG_LEVEL_CHOICES,
    INHERITED_LOG_LEVEL_CHOICES,
)


__all__ = [
    "LOG_LEVEL_CHOICES",
    "INHERITED_LOG_LEVEL_CHOICES",
    "configure_logging",
    "current_log_level_name",
    "set_runtime_log_level",
]

# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
Centralized configuration for ai_nn_controller.

This module provides a global verbose flag that can be set at startup
and used throughout the package to control debug output.
"""


class AicConfig:
    """Global configuration for the AIC framework."""

    _verbose: bool = False

    @classmethod
    def set_verbose(cls, verbose: bool):
        """Set the global verbose flag."""
        cls._verbose = verbose

    @classmethod
    def is_verbose(cls) -> bool:
        """Check if verbose mode is enabled."""
        return cls._verbose


def vprint(*args, **kwargs):
    """
    Verbose print function.

    Only prints if verbose mode is enabled via AicConfig.
    Usage is identical to the built-in print() function.

    Example:
        vprint("[AicController] Starting up...")
    """
    if AicConfig.is_verbose():
        print(*args, **kwargs)

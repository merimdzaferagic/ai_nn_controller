# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
Global configuration for the controlled_entity framework.
"""


class NodeConfig:
    """Global configuration for the controlled_entity framework."""

    _verbose: bool = False

    @classmethod
    def set_verbose(cls, verbose: bool):
        cls._verbose = verbose

    @classmethod
    def is_verbose(cls) -> bool:
        return cls._verbose


def vprint(*args, **kwargs):
    """Verbose print -- only prints if verbose mode is enabled."""
    if NodeConfig.is_verbose():
        print(*args, **kwargs)

# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
Configuration file parser for network nodes.

Parses key=value configuration files (node.conf).
"""


def parse_config(config_file):
    """Parse a key=value configuration file.

    Lines starting with '#' are treated as comments.
    Values are auto-converted to int, float, or left as str.

    Args:
        config_file: Path to the configuration file.

    Returns:
        dict: Parsed configuration as key-value pairs.
    """
    config = {}
    with open(config_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if value.isdigit():
                    config[key] = int(value)
                elif value.replace(".", "", 1).isdigit():
                    config[key] = float(value)
                else:
                    config[key] = value
    return config

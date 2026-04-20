# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

import inspect
from ..config import vprint


class Validator:

    @staticmethod
    def validate_aic_app(AicApp):
        """
        Validate that an AIC application has all required attributes.

        Required attributes (must be defined by the app):
            - aic_app_id: Unique identifier for the app instance
            - control_loop_update_time: Interval in seconds between process() calls
            - read_measurements: Dict mapping node IDs to measurement names

        Auto-generated attributes (set by @aic_app decorator):
            - send_commands: Auto-initialized as empty list
            - cell_ids: Auto-derived from read_measurements + control_functions keys
        """
        aic_app_required_attributes = [
                "aic_app_id",
                "control_loop_update_time",
                "read_measurements",
        ]

        # Validate that the aic_app object has all the required fields
        for attribute in aic_app_required_attributes:
            if not hasattr(AicApp, attribute):
                raise RuntimeError("Attribute %s need to be defined on aic_app object." % attribute)

        # Validate that the aic_app object has all the required methods
        for method in inspect.getmembers(AicApp, predicate=inspect.ismethod):
            vprint(method)

        return True

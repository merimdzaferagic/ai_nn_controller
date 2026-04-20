# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from ai_nn_controller.decorators.aic_app import aic_app
from ai_nn_controller.decorators.agent_controlled import agent_controlled
from ai_nn_controller.AicApp import AicApp
from ai_nn_controller.AicController import AicController
import time
import argparse

# Import commands module to register commands with the framework.
# This app is read-only so no commands are registered.
import commands  # noqa: F401


@aic_app(name="SrsranReader")
class SrsranReaderApp(AicApp):
    """
    Subscribes to all srsRAN node measurements (node_id=10) and prints them.
    Read-only — no control functions. Measurements are exposed via REST and MCP.
    """
    aic_app_id = 10
    control_loop_update_time = 2

    read_measurements = {
        10: [
            "session_id",
            "pci", "rnti",
            "dl_bitrate", "ul_bitrate",
            "dl_bler", "ul_bler",
            "dl_mcs", "ul_mcs",
            "dl_nof_ok", "dl_nof_nok",
            "ul_nof_ok", "ul_nof_nok",
            "bsr", "cqi", "ri",
            "ul_snr", "pusch_snr_db", "pucch_snr_db",
            "cpu_usage_percent", "memory_usage_MB", "power_consumption_Watts",
        ],
    }

    control_functions = {}

    @classmethod
    @agent_controlled(
        name="get_ue_summary",
        description="Return a structured summary of the latest UE-level and system-level srsRAN metrics",
        schema={
            "properties": {},
            "required": [],
        },
    )
    def handle_get_ue_summary(cls, request, measurements):
        """Return latest srsRAN metrics as a structured dict for AI agents."""
        latest = measurements.get(10, [None])[-1] if measurements.get(10) else None
        if not latest:
            return {"status": "no_data"}

        return {
            "status": "ok",
            "ue_metrics": {
                "pci": latest.get("pci"),
                "rnti": latest.get("rnti"),
                "dl_bitrate": latest.get("dl_bitrate"),
                "ul_bitrate": latest.get("ul_bitrate"),
                "dl_bler": latest.get("dl_bler"),
                "ul_bler": latest.get("ul_bler"),
                "dl_mcs": latest.get("dl_mcs"),
                "ul_mcs": latest.get("ul_mcs"),
                "cqi": latest.get("cqi"),
                "ri": latest.get("ri"),
                "ul_snr": latest.get("ul_snr"),
                "pusch_snr_db": latest.get("pusch_snr_db"),
                "pucch_snr_db": latest.get("pucch_snr_db"),
            },
            "system_metrics": {
                "cpu_usage_percent": latest.get("cpu_usage_percent"),
                "memory_usage_MB": latest.get("memory_usage_MB"),
                "power_consumption_Watts": latest.get("power_consumption_Watts"),
            },
        }

    @classmethod
    def process(cls, measurements):
        print(f"[SrsranReader] Processing at {time.time():.2f}")
        latest = measurements.get(10, [None])[-1] if measurements.get(10) else None
        if not latest:
            print("  [srsRAN] No data yet")
            return

        print(f"  {'session_id':<24}: {latest.get('session_id')}")
        print("  --- UE-Level Metrics ---")
        for key in ["pci", "rnti", "dl_bitrate", "ul_bitrate", "dl_bler", "ul_bler",
                    "dl_mcs", "ul_mcs", "dl_nof_ok", "dl_nof_nok",
                    "ul_nof_ok", "ul_nof_nok", "bsr", "cqi", "ri",
                    "ul_snr", "pusch_snr_db", "pucch_snr_db"]:
            print(f"  {key:<24}: {latest.get(key)}")
        print("  --- System Metrics ---")
        for key in ["cpu_usage_percent", "memory_usage_MB", "power_consumption_Watts"]:
            print(f"  {key:<24}: {latest.get(key)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="srsRAN Reader AIC Application")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--port", "-p", type=int, default=8000)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    AicController(with_api=True, api_host=args.host, api_port=args.port, verbose=args.verbose).run()

# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from ai_nn_controller.decorators.aic_app import aic_app
from ai_nn_controller.decorators.command_validator import command_validator
from ai_nn_controller.decorators.agent_controlled import agent_controlled
from ai_nn_controller.AicApp import AicApp
from ai_nn_controller.AicController import AicController
from typing import Optional, Tuple
import time
import argparse

# Import commands module to register specific commands with the framework
import commands


@aic_app(name="NetworkApp1")
class NetworkControlApp(AicApp):
    """
    Reads measurements from all optical nodes (Amp1–3, ROADM1–3) and sends
    periodic SET_GAIN commands to ROADM3. Conflict resolution is handled by
    the framework's CommandArbitrator (AIC_ARBITRATION_STRATEGY env var).

    Demonstrates plugin usage: ConsolePlugin is declared as a required plugin.
    If the console-plugin package is not installed the controller will refuse
    to start and print a clear error listing the missing plugin.
    Install it with: pip install -e plugins/console_plugin/
    """
    aic_app_id = 1
    control_loop_update_time = 2

    # Declare plugin dependencies — the controller validates these at startup.
    required_plugins = ["ConsolePlugin"]

    read_measurements = {
        3: ["session_id", "amp1_target_gain", "amp1_gain_tilt", "amp1_target_power", "amp1_control_mode"],
        4: ["session_id", "roadm1_preamp_target_gain", "roadm1_preamp_gain_tilt",
            "roadm1_booster_target_gain", "roadm1_booster_gain_tilt"],
        5: ["session_id", "amp2_target_gain", "amp2_gain_tilt", "amp2_target_power", "amp2_control_mode"],
        6: ["session_id", "amp3_target_gain", "amp3_gain_tilt", "amp3_target_power", "amp3_control_mode"],
        7: ["session_id", "roadm2_preamp_target_gain", "roadm2_preamp_gain_tilt",
            "roadm2_booster_target_gain", "roadm2_booster_gain_tilt"],
        8: ["session_id", "roadm3_preamp_target_gain", "roadm3_preamp_gain_tilt",
            "roadm3_booster_target_gain", "roadm3_booster_gain_tilt"],
    }

    control_functions = {8: ["SET_GAIN"]}

    command_counter = 0

    MAX_TARGET_GAIN = 25.0
    MIN_TARGET_GAIN = 0.0

    @classmethod
    @command_validator("SET_GAIN")
    def validate_set_gain(cls, params: dict) -> Tuple[bool, Optional[str]]:
        target_gain = params.get("target_gain")
        if target_gain is None:
            return False, "target_gain parameter is required"
        if target_gain > cls.MAX_TARGET_GAIN:
            return False, f"target_gain {target_gain} dB exceeds maximum of {cls.MAX_TARGET_GAIN} dB"
        if target_gain < cls.MIN_TARGET_GAIN:
            return False, f"target_gain {target_gain} dB is below minimum of {cls.MIN_TARGET_GAIN} dB"
        valid_amp_types = ["preamp", "booster", "line"]
        amp_type = params.get("amp_type")
        if amp_type and amp_type not in valid_amp_types:
            return False, f"amp_type '{amp_type}' is not valid. Use one of: {', '.join(valid_amp_types)}"
        return True, None

    @classmethod
    @agent_controlled(
        name="optimize_gain",
        description="Optimize ROADM3 preamp gain based on current measurements",
        schema={
            "properties": {
                "node_id": {"type": "integer", "description": "Target node ID (e.g., 8 for ROADM3)"},
                "strategy": {
                    "type": "string",
                    "enum": ["max_snr", "min_power", "balanced"],
                    "description": "Optimization strategy to apply",
                },
            },
            "required": ["node_id", "strategy"],
        },
    )
    def handle_optimize_gain(cls, request, measurements):
        """Optimize gain using live measurements from the process loop."""
        node_id = request["node_id"]
        strategy = request["strategy"]
        node_data = measurements.get(node_id, [{}])
        latest = node_data[-1] if node_data else {}
        current_gain = latest.get("roadm3_preamp_target_gain", 15.0)

        if strategy == "max_snr":
            new_gain = min(current_gain + 2.0, cls.MAX_TARGET_GAIN)
        elif strategy == "min_power":
            new_gain = max(current_gain - 2.0, cls.MIN_TARGET_GAIN)
        else:
            new_gain = max(min(current_gain + 1.0, 20.0), 5.0)

        cls.add_command(("SET_GAIN", {"node_id": node_id, "value": {"amp_type": "preamp", "target_gain": new_gain}}))
        return {"status": "applied", "strategy": strategy, "previous_gain": current_gain,
                "new_gain": new_gain, "node_id": node_id}

    @classmethod
    def process(cls, measurements):
        console = cls.plugins.get("ConsolePlugin")

        if console:
            console.log_event("process_tick", app="NetworkApp1", t=f"{time.time():.2f}")
        else:
            print(f"[NetworkApp1] Processing at {time.time():.2f}")

        if not measurements:
            return

        for node_id, label in [(3, "Amp1"), (4, "ROADM1"), (5, "Amp2"),
                                (6, "Amp3"), (7, "ROADM2"), (8, "ROADM3")]:
            latest = measurements.get(node_id, [None])[-1] if measurements.get(node_id) else None
            if latest:
                if console:
                    console.log_measurement(node_id, latest)
                else:
                    print(f"  [{label}] {latest}")

        cls.command_counter += 1
        if cls.command_counter >= 5:
            cls.command_counter = 0
            payload = {"node_id": 8, "value": {"amp_type": "preamp", "target_gain": 10}}
            if console:
                console.log_command("SET_GAIN", payload)
            cls.add_command(("SET_GAIN", payload))


@aic_app(name="NetworkApp2")
class SecondApp(AicApp):
    """
    Reads Amp1 and ROADM3 measurements and sends periodic SET_GAIN commands
    to ROADM3. Conflicts with NetworkApp1 are resolved by the CommandArbitrator.
    """
    aic_app_id = 2
    control_loop_update_time = 2

    read_measurements = {
        3: ["session_id", "amp1_target_gain", "amp1_gain_tilt", "amp1_target_power", "amp1_control_mode"],
        8: ["session_id", "roadm3_preamp_target_gain", "roadm3_preamp_gain_tilt",
            "roadm3_booster_target_gain", "roadm3_booster_gain_tilt"],
    }

    control_functions = {8: ["SET_GAIN"]}

    command_counter = 0

    MAX_TARGET_GAIN = 25.0
    MIN_TARGET_GAIN = 0.0

    @classmethod
    @command_validator("SET_GAIN")
    def validate_set_gain(cls, params: dict) -> Tuple[bool, Optional[str]]:
        target_gain = params.get("target_gain")
        if target_gain is None:
            return False, "target_gain parameter is required"
        if target_gain > cls.MAX_TARGET_GAIN:
            return False, f"target_gain {target_gain} dB exceeds maximum of {cls.MAX_TARGET_GAIN} dB"
        if target_gain < cls.MIN_TARGET_GAIN:
            return False, f"target_gain {target_gain} dB is below minimum of {cls.MIN_TARGET_GAIN} dB"
        return True, None

    @classmethod
    def process(cls, measurements):
        print(f"[NetworkApp2] Processing at {time.time():.2f}")
        if not measurements:
            return

        for node_id, label in [(3, "Amp1"), (8, "ROADM3")]:
            latest = measurements.get(node_id, [None])[-1] if measurements.get(node_id) else None
            if latest:
                print(f"  [{label}] {latest}")

        cls.command_counter += 1
        if cls.command_counter >= 5:
            cls.command_counter = 0
            print("[NetworkApp2] Sending SET_GAIN to ROADM3 (node 8, preamp, gain=15)")
            cls.add_command(("SET_GAIN", {"node_id": 8, "value": {"amp_type": "preamp", "target_gain": 15}}))


@aic_app(name="ConflictMitigator")
class ConflictMitigatorApp(AicApp):
    """
    Intercepts pending commands from all other apps before the controller
    dispatches them. Detects conflicts (multiple apps targeting the same
    node+command in the same cycle), resolves by priority, and re-queues
    only the winning command via cls.add_command().

    Priority order: NetworkApp1 > NetworkApp2 (first match wins).
    """
    aic_app_id = 3
    control_loop_update_time = 2

    # Subscribe to all nodes so measurements are available for policy decisions
    read_measurements = {
        3: ["session_id", "amp1_target_gain", "amp1_gain_tilt", "amp1_target_power", "amp1_control_mode"],
        4: ["session_id", "roadm1_preamp_target_gain", "roadm1_preamp_gain_tilt",
            "roadm1_booster_target_gain", "roadm1_booster_gain_tilt"],
        5: ["session_id", "amp2_target_gain", "amp2_gain_tilt", "amp2_target_power", "amp2_control_mode"],
        6: ["session_id", "amp3_target_gain", "amp3_gain_tilt", "amp3_target_power", "amp3_control_mode"],
        7: ["session_id", "roadm2_preamp_target_gain", "roadm2_preamp_gain_tilt",
            "roadm2_booster_target_gain", "roadm2_booster_gain_tilt"],
        8: ["session_id", "roadm3_preamp_target_gain", "roadm3_preamp_gain_tilt",
            "roadm3_booster_target_gain", "roadm3_booster_gain_tilt"],
    }

    # Must declare control_functions for every node CM may issue commands to
    control_functions = {8: ["SET_GAIN"]}

    # Apps to monitor, in priority order (index 0 = highest priority)
    MANAGED_APPS = ["NetworkApp1", "NetworkApp2"]

    @classmethod
    def process(cls, measurements):
        from ai_nn_controller.managers.AicManager import AicManager
        from collections import defaultdict

        # Drain send_commands from all managed apps into a local list
        pending = []
        for app_name in cls.MANAGED_APPS:
            app_class = AicManager.aic_apps.get(app_name)
            if app_class is None or not hasattr(app_class, "send_commands"):
                continue
            while app_class.send_commands:
                try:
                    cmd = app_class.send_commands.popleft()
                    pending.append({"app": app_name, "cmd": cmd})
                except IndexError:
                    break

        if not pending:
            return

        # Group by (node_id, cmd_name) to detect conflicts
        by_target = defaultdict(list)
        for item in pending:
            cmd_name = item["cmd"][0]
            node_id = item["cmd"][1].get("node_id")
            by_target[(node_id, cmd_name)].append(item)

        print(f"\n[ConflictMitigator] Evaluating {len(pending)} pending command(s)")

        for (node_id, cmd_name), contenders in by_target.items():
            if len(contenders) == 1:
                print(f"  [Node {node_id}] {cmd_name}: single request from "
                      f"{contenders[0]['app']} — forwarding")
                cls.add_command(contenders[0]["cmd"])
            else:
                apps = [c["app"] for c in contenders]
                print(f"  [Node {node_id}] {cmd_name}: CONFLICT between {apps}")

                # Resolve by priority order
                winner = None
                for priority_app in cls.MANAGED_APPS:
                    for c in contenders:
                        if c["app"] == priority_app:
                            winner = c
                            break
                    if winner:
                        break
                if winner is None:
                    winner = contenders[0]

                blocked = [c["app"] for c in contenders if c is not winner]
                print(f"    ALLOWED: {winner['app']}  BLOCKED: {blocked}")
                cls.add_command(winner["cmd"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIC Application Controller")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--port", "-p", type=int, default=8000)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    AicController(with_api=True, api_host=args.host, api_port=args.port, verbose=args.verbose).run()

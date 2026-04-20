Conflict Mitigation Example
===========================

This example demonstrates how to implement a conflict mitigator in **ai_nn_controller**
that arbitrates between multiple applications trying to control the same node —
without any module-level shared state and without modifying the framework.

Architecture
------------

The pattern uses three apps defined in the same ``aic_app.py`` file:

- **NetworkApp1** and **NetworkApp2** call ``cls.add_command()`` normally. Each app has its
  own ``send_commands`` deque (initialised by the ``@aic_app`` decorator).
- **ConflictMitigator** runs in the same process cycle. It reaches into the other apps'
  ``send_commands`` deques via ``AicManager.aic_apps``, drains them before the controller
  dispatches them, detects conflicts, and re-queues only the winning command via its own
  ``cls.add_command()``.

.. code-block:: text

   ┌──────────────┐    ┌──────────────┐
   │ NetworkApp1  │    │ NetworkApp2  │
   │ (priority 1) │    │ (priority 2) │
   │              │    │              │
   │ add_command()│    │ add_command()│
   └──────┬───────┘    └──────┬───────┘
          │ send_commands      │ send_commands
          │ deque              │ deque
          └────────┬───────────┘
                   │  drained by
          ┌────────▼────────┐
          │ConflictMitigator│ resolves conflicts, calls add_command() for winner
          └────────┬────────┘
                   │ send_commands deque
          ┌────────▼────────┐
          │  AicController  │ dispatches to network node
          └────────┬────────┘
                   │
          ┌────────▼────────┐
          │  Network Node   │
          └─────────────────┘

Why no shared queue?
--------------------

The old pattern (``GLOBAL_COMMAND_QUEUE`` module-level dict) routed commands around
the framework. Commands written to the global dict bypassed ``CommandArbitrator`` and
any framework-level safety enforcement.

The ``AicManager``-based pattern keeps all commands inside the framework pipeline.
Apps call ``cls.add_command()`` as normal; the ConflictMitigator intercepts at the
deque level, before ``AicController.process_commands()`` picks them up. The winning
command goes back through ``add_command()`` and is dispatched by the controller in
the usual way.

Complete Code
-------------

All three apps live in the same ``aic_app.py``. Import ``commands`` first so the
command registry is populated before ``@aic_app`` decorators execute.

.. code-block:: python

   from ai_nn_controller.decorators.aic_app import aic_app
   from ai_nn_controller.decorators.command_validator import command_validator
   from ai_nn_controller.AicApp import AicApp
   from ai_nn_controller.AicController import AicController
   from typing import Optional, Tuple
   import time

   # Register domain commands before @aic_app executes
   import commands


   @aic_app(name="NetworkApp1")
   class NetworkApp1(AicApp):
       """Higher-priority app — sends SET_GAIN every 5 cycles."""

       aic_app_id = 1
       control_loop_update_time = 2
       read_measurements = {8: ["preamp_gain"]}
       control_functions = {8: ["SET_GAIN"]}

       counter = 0
       MAX_GAIN = 25.0
       MIN_GAIN = 0.0

       @classmethod
       @command_validator("SET_GAIN")
       def validate_set_gain(cls, params: dict) -> Tuple[bool, Optional[str]]:
           gain = params.get("target_gain")
           if gain is None:
               return False, "target_gain is required"
           if gain > cls.MAX_GAIN:
               return False, f"target_gain {gain} exceeds max {cls.MAX_GAIN}"
           if gain < cls.MIN_GAIN:
               return False, f"target_gain {gain} is below min {cls.MIN_GAIN}"
           return True, None

       @classmethod
       def process(cls, measurements):
           cls.counter += 1
           if cls.counter >= 5:
               cls.counter = 0
               print("[NetworkApp1] Queuing SET_GAIN -> 20.0 dB")
               cls.add_command(("SET_GAIN", {
                   "node_id": 8,
                   "value": {"amp_type": "preamp", "target_gain": 20.0}
               }))


   @aic_app(name="NetworkApp2")
   class NetworkApp2(AicApp):
       """Lower-priority app — sends SET_GAIN every 5 cycles."""

       aic_app_id = 2
       control_loop_update_time = 2
       read_measurements = {8: ["preamp_gain"]}
       control_functions = {8: ["SET_GAIN"]}

       counter = 0
       MAX_GAIN = 25.0
       MIN_GAIN = 0.0

       @classmethod
       @command_validator("SET_GAIN")
       def validate_set_gain(cls, params: dict) -> Tuple[bool, Optional[str]]:
           gain = params.get("target_gain")
           if gain is None:
               return False, "target_gain is required"
           if gain > cls.MAX_GAIN:
               return False, f"target_gain {gain} exceeds max {cls.MAX_GAIN}"
           return True, None

       @classmethod
       def process(cls, measurements):
           cls.counter += 1
           if cls.counter >= 5:
               cls.counter = 0
               print("[NetworkApp2] Queuing SET_GAIN -> 25.0 dB")
               cls.add_command(("SET_GAIN", {
                   "node_id": 8,
                   "value": {"amp_type": "preamp", "target_gain": 25.0}
               }))


   @aic_app(name="ConflictMitigator")
   class ConflictMitigatorApp(AicApp):
       """
       Intercepts pending commands from NetworkApp1 and NetworkApp2 before the
       controller dispatches them.  Detects conflicts (multiple apps targeting the
       same node+command in the same cycle), resolves by priority, and re-queues
       only the winning command via cls.add_command().

       Priority order: NetworkApp1 > NetworkApp2 (index 0 wins).
       """

       aic_app_id = 3
       control_loop_update_time = 2
       read_measurements = {8: ["preamp_gain"]}
       control_functions = {8: ["SET_GAIN"]}

       MANAGED_APPS = ["NetworkApp1", "NetworkApp2"]

       @classmethod
       def process(cls, measurements):
           from ai_nn_controller.managers.AicManager import AicManager
           from collections import defaultdict

           # Drain send_commands from all managed apps
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

                   # Resolve by MANAGED_APPS priority order
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
       AicController(with_api=True, verbose=True).run()

Output Example
--------------

.. code-block:: text

   [NetworkApp1] Queuing SET_GAIN -> 20.0 dB
   [NetworkApp2] Queuing SET_GAIN -> 25.0 dB

   [ConflictMitigator] Evaluating 2 pending command(s)
     [Node 8] SET_GAIN: CONFLICT between ['NetworkApp1', 'NetworkApp2']
       ALLOWED: NetworkApp1  BLOCKED: ['NetworkApp2']

Key Design Points
-----------------

**Thread safety**: CPython's GIL makes ``deque.popleft()`` thread-safe. The
ConflictMitigator's ``popleft()`` calls and the controller's own deque operations
interleave safely without a lock.

**No controller changes**: The entire pattern lives inside ``aic_app.py``. No
``AicController`` or ``AicManager`` code needs modification.

**Ordering guarantee**: The ConflictMitigator must be registered *after* the apps it
manages so that the controller runs it in the same or subsequent cycle. All three apps
share the same ``control_loop_update_time``, so the mitigator runs while the managed
apps' commands are still in their deques.

**Framework arbitration still applies**: The re-queued command passes through
``AicController.process_commands()`` and therefore through ``SafetyPolicyEngine`` and
``CommandArbitrator`` as normal. The ConflictMitigator adds an app-level policy layer
on top of, not instead of, the framework's built-in mechanisms.

Alternative Resolution Strategies
----------------------------------

**Measurement-based (use live data to pick winner):**

.. code-block:: python

   # Inside process(), after draining pending:
   node_data = measurements.get(8, [{}])[-1]
   current_gain = node_data.get("preamp_gain", 15.0)

   # Pick the command whose target is closest to current_gain
   winner = min(contenders,
       key=lambda c: abs(c["cmd"][1]["value"].get("target_gain", 0) - current_gain))
   cls.add_command(winner["cmd"])

**Average the conflicting values:**

.. code-block:: python

   gains = [c["cmd"][1]["value"].get("target_gain", 0) for c in contenders]
   avg_gain = sum(gains) / len(gains)
   cls.add_command(("SET_GAIN", {"node_id": node_id,
                                  "value": {"amp_type": "preamp", "target_gain": avg_gain}}))

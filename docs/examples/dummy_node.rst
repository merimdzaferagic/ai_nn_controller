Dummy Node Examples
====================

This walkthrough shows how to build network nodes using the ``controlled_entity``
package in **ai_nn_controller**, based on the dummy nodes in ``network_nodes/dummy_nodes/``.

Dummy nodes generate simulated (random) data and are useful for testing, development,
and as templates for real integrations.

Measurement-Only Node (Amplifier)
---------------------------------

The simplest node only publishes measurements. This is the complete code from
``network_nodes/dummy_nodes/amp1_node/node.py``:

.. code-block:: python

   from controlled_entity import ControlledEntity, node, NodeRunner
   import random
   import time

   @node(name="Amp1")
   class Amp1Node(ControlledEntity):
       available_measurements = [
           "session_id",
           "amp1_target_gain",
           "amp1_gain_tilt",
           "amp1_target_power",
           "amp1_control_mode",
       ]
       measurement_interval = 1.0

       def poll_measurements(self):
           return {
               "session_id": f"session_{self.config['node_id']}_{int(time.time())}",
               "amp1_target_gain": round(random.uniform(15.0, 25.0), 2),
               "amp1_gain_tilt": round(random.uniform(-2.0, 2.0), 2),
               "amp1_target_power": round(random.uniform(0.0, 5.0), 2),
               "amp1_control_mode": 3,
           }

   if __name__ == "__main__":
       NodeRunner().run()

**What happens when this runs:**

1. ``@node(name="Amp1")`` registers the class with the framework
2. ``NodeRunner().run()`` reads ``node.conf``, registers with ``aic_register``,
   and connects to the broker
3. Every 1 second, ``poll_measurements()`` is called and the returned dict is
   published as ``"3;{...}"`` on the message bus
4. Any control application subscribing to node ID 3 receives these measurements

**Configuration** (``node.conf``):

.. code-block:: ini

   ip_address = aic_register
   register_port = 5558
   node_id = 3
   pub_port = 5562

``pub_port`` is one of the recognized optional ``node.conf`` keys — see
:doc:`../getting_started/configuration` for the full list.

**Dockerfile**:

.. code-block:: dockerfile

   FROM python:3.9-slim

   COPY controller_components/controlled_entity/ /tmp/controlled_entity/
   RUN pip install --no-cache-dir /tmp/controlled_entity && rm -rf /tmp/controlled_entity

   WORKDIR /node

   COPY network_nodes/dummy_nodes/amp1_node/*.py ./
   COPY network_nodes/dummy_nodes/amp1_node/*.conf ./

   CMD ["python3", "node.py"]

Node with Command Handling (ROADM)
-----------------------------------

ROADM3 demonstrates a node that both publishes measurements **and** accepts
commands from control applications. From
``network_nodes/dummy_nodes/roadm3_with_command/node.py``:

.. code-block:: python

   from controlled_entity import ControlledEntity, node, NodeRunner
   import random
   import time

   @node(name="ROADM3")
   class ROADM3Node(ControlledEntity):
       available_measurements = [
           "session_id",
           "roadm3_preamp_target_gain",
           "roadm3_preamp_gain_tilt",
           "roadm3_booster_target_gain",
           "roadm3_booster_gain_tilt",
       ]
       available_controls = ["SET_GAIN", "SET_VOA", "SET_TILT"]
       measurement_interval = 5.0

       def poll_measurements(self):
           return {
               "session_id": f"session_{self.config['node_id']}_{int(time.time())}",
               "roadm3_preamp_target_gain": round(random.uniform(17.0, 21.0), 2),
               "roadm3_preamp_gain_tilt": round(random.uniform(-1.5, 1.5), 2),
               "roadm3_booster_target_gain": round(random.uniform(14.0, 19.0), 2),
               "roadm3_booster_gain_tilt": round(random.uniform(-2.0, 2.0), 2),
           }

       def handle_command(self, payload):
           """Process incoming commands from control applications."""
           print(f"[ROADM3] Processing command: {payload}")

           if "target_gain" in payload:
               print(f"[ROADM3] Setting target gain to: {payload['target_gain']}")

           if "preamp_gain" in payload:
               print(f"[ROADM3] Setting preamp gain to: {payload['preamp_gain']}")

           if "booster_gain" in payload:
               print(f"[ROADM3] Setting booster gain to: {payload['booster_gain']}")

           if "voa_mux" in payload:
               channel = payload.get("channel", "unknown")
               print(f"[ROADM3] Setting VOA MUX for channel {channel}: {payload['voa_mux']}")

           print(f"[ROADM3] Command processing complete")
           return True

   if __name__ == "__main__":
       NodeRunner().run()

**Key differences from the measurement-only node:**

- ``available_controls = ["SET_GAIN", "SET_VOA", "SET_TILT"]`` declares the commands
  this node can accept
- ``handle_command(self, payload)`` processes incoming commands
- ``measurement_interval = 5.0`` -- slower polling since this node is more complex

Running the Dummy Nodes
-----------------------

Start the full stack with Docker Compose:

.. code-block:: bash

   docker compose up -d

This starts the infrastructure (Redis, register, broker) and all dummy nodes. Verify
they registered:

.. code-block:: bash

   docker compose logs aic_register

You should see lines like:

.. code-block:: text

   REGISTER network_node node: 3
   Network Nodes sharing available PMs
   REGISTER network_node node: 8
   Network Nodes sharing available Control Functions

Connecting a Control App to a Dummy Node
-----------------------------------------

Once the dummy nodes are running, create a control application that reads their
measurements:

.. code-block:: python

   from ai_nn_controller.decorators.aic_app import aic_app
   from ai_nn_controller.AicApp import AicApp
   from ai_nn_controller.AicController import AicController

   @aic_app(name="DummyMonitor")
   class DummyMonitor(AicApp):
       aic_app_id = 100
       control_loop_update_time = 2

       # Read from Amp1 and ROADM3
       read_measurements = {
           3: ["amp1_target_gain", "amp1_gain_tilt"],
           8: ["roadm3_preamp_target_gain", "roadm3_booster_target_gain"],
       }

       # Can send commands to ROADM3
       control_functions = {
           8: ["SET_GAIN"]
       }

       @classmethod
       def process(cls, measurements):
           amp1 = measurements.get(3, [{}])[-1]
           roadm3 = measurements.get(8, [{}])[-1]

           gain = amp1.get("amp1_target_gain", "N/A")
           preamp = roadm3.get("roadm3_preamp_target_gain", "N/A")

           print(f"Amp1 gain: {gain}, ROADM3 preamp: {preamp}")

           # Send a command to ROADM3 if gain is too high
           if isinstance(gain, (int, float)) and gain > 23:
               cls.add_command(("SET_GAIN", {
                   "node_id": 8,
                   "value": {"target_gain": 20.0}
               }))

   if __name__ == "__main__":
       AicController(with_api=True).run()

Available Dummy Nodes
---------------------

.. list-table::
   :header-rows: 1
   :widths: 20 8 35 37

   * - Node
     - ID
     - Measurements
     - Controls
   * - amp1_node
     - 3
     - target_gain, gain_tilt, target_power, control_mode
     - --
   * - amp2_node
     - 5
     - target_gain, gain_tilt, target_power, control_mode
     - --
   * - amp3_node
     - 6
     - target_gain, gain_tilt, target_power, control_mode
     - --
   * - roadm1_node
     - 4
     - preamp_target_gain, preamp_gain_tilt, booster_target_gain, booster_gain_tilt
     - --
   * - roadm2_node
     - 7
     - preamp_target_gain, preamp_gain_tilt, booster_target_gain, booster_gain_tilt
     - --
   * - roadm3_with_command
     - 8
     - preamp_target_gain, preamp_gain_tilt, booster_target_gain, booster_gain_tilt
     - SET_GAIN, SET_VOA, SET_TILT

Creating Your Own Dummy Node
-----------------------------

To create a new dummy node:

1. Create a directory under ``network_nodes/dummy_nodes/``:

   .. code-block:: bash

      mkdir network_nodes/dummy_nodes/my_node/

2. Create ``node.py`` with your ``ControlledEntity`` subclass:

   .. code-block:: python

      from controlled_entity import ControlledEntity, node, NodeRunner
      import random
      import time

      @node(name="MyNode")
      class MyNode(ControlledEntity):
          available_measurements = ["temperature", "humidity", "pressure"]
          measurement_interval = 2.0

          def poll_measurements(self):
              return {
                  "temperature": round(random.uniform(20.0, 30.0), 1),
                  "humidity": round(random.uniform(40.0, 80.0), 1),
                  "pressure": round(random.uniform(1010.0, 1020.0), 1),
              }

      if __name__ == "__main__":
          NodeRunner().run()

3. Create ``node.conf`` with a unique ``node_id``:

   .. code-block:: ini

      ip_address = aic_register
      register_port = 5558
      node_id = 20

4. Create a ``Dockerfile``:

   .. code-block:: dockerfile

      FROM python:3.9-slim

      COPY controller_components/controlled_entity/ /tmp/controlled_entity/
      RUN pip install --no-cache-dir /tmp/controlled_entity && rm -rf /tmp/controlled_entity

      WORKDIR /node

      COPY network_nodes/dummy_nodes/my_node/*.py ./
      COPY network_nodes/dummy_nodes/my_node/*.conf ./

      CMD ["python3", "node.py"]

5. Add to ``docker-compose.yml`` and start.

Next Steps
----------

- :doc:`../user_guide/developing_nodes` - Full guide on the controlled_entity framework
- :doc:`basic_app` - Simple control application example
- :doc:`srsran_integration` - Real-world node integration with InfluxDB

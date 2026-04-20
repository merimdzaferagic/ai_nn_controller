REST API Reference
==================

The ai_nn_controller AIC Server exposes a REST API for managing applications and sending
commands.

Base URL
--------

Default: ``http://localhost:8000``

Global Endpoints
----------------

Health Check
~~~~~~~~~~~~

.. http:get:: /health

   Check if the server is running.

   **Response:**

   .. code-block:: json

      {
        "status": "healthy",
        "controller_initialized": true,
        "registered_apps": ["NetworkApp1"]
      }

List Applications
~~~~~~~~~~~~~~~~~

.. http:get:: /apps

   List all registered applications.

   **Response:**

   .. code-block:: json

      {
        "apps": [
          {
            "name": "NetworkApp1",
            "state": "stopped",
            "node_id": null,
            "cell_ids": [3, 4, 5, 6, 7, 8],
            "time_interval": null
          },
          {
            "name": "NetworkApp2",
            "state": "running",
            "node_id": null,
            "cell_ids": [3, 8],
            "time_interval": null
          }
        ],
        "total": 2
      }

Application Endpoints
---------------------

Get Application Info
~~~~~~~~~~~~~~~~~~~~

.. http:get:: /apps/{app_name}/info

   Get detailed information about an application.

   :param app_name: Name of the application

   **Response:**

   .. code-block:: json

      {
        "app_name": "NetworkControlApp",
        "aic_app_id": 1,
        "cell_ids": [3, 4, 5, 6, 7, 8],
        "control_loop_update_time": 2,
        "read_measurements": {
          "3": ["amp1_target_gain", "amp1_gain_tilt"],
          "8": ["roadm3_preamp_gain"]
        },
        "control_functions": {
          "8": ["SET_GAIN"]
        }
      }

Get Application State
~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /apps/{app_name}/state

   Get current state of an application.

   :param app_name: Name of the application

   **Response:**

   .. code-block:: json

      {
        "app": "NetworkControlApp",
        "state": "running"
      }

   States: ``running``, ``paused``, ``stopped``

Update Application State
~~~~~~~~~~~~~~~~~~~~~~~~

.. http:put:: /apps/{app_name}/state

   Update the state of an application.

   :param app_name: Name of the application

   **Request Body:**

   .. code-block:: json

      {
        "state": "running"
      }

   Valid states: ``running``, ``paused``, ``stopped``

   **Response:**

   .. code-block:: json

      {
        "app": "NetworkControlApp",
        "state": "running",
        "previous_state": "stopped"
      }

   **Error Response (400):**

   .. code-block:: json

      {
        "detail": "Invalid state 'invalid'. Use one of: running, paused, stopped"
      }

Get Measurements
~~~~~~~~~~~~~~~~

.. http:get:: /apps/{app_name}/measurements

   Get latest measurements for an application.

   :param app_name: Name of the application

   **Response:**

   .. code-block:: json

      {
        "app": "NetworkControlApp",
        "measurements": {
          "3": {
            "amp1_target_gain": 20.5,
            "amp1_gain_tilt": 1.2
          },
          "8": {
            "roadm3_preamp_gain": 15.0
          }
        }
      }

   Returns empty measurements if app is not running.

Send Manual Control
~~~~~~~~~~~~~~~~~~~

.. http:post:: /apps/{app_name}/control

   Send a manual control command via the application.

   :param app_name: Name of the application

   **Request Body:**

   .. code-block:: json

      {
        "node_id": 8,
        "command": "SET_GAIN",
        "payload": {
          "amp_type": "preamp",
          "target_gain": 15.0
        }
      }

   **Success Response:**

   .. code-block:: json

      {
        "app": "NetworkControlApp",
        "node_id": 8,
        "command": {
          "command": "SET_GAIN",
          "payload": {
            "amp_type": "preamp",
            "target_gain": 15.0
          }
        },
        "status": "sent"
      }

   **Rejected Response (Validation Failed):**

   If the application has a command validator that rejects the command:

   .. code-block:: json

      {
        "app": "NetworkControlApp",
        "node_id": 8,
        "command": {
          "command": "SET_GAIN",
          "payload": {
            "amp_type": "preamp",
            "target_gain": 30.0
          }
        },
        "status": "rejected",
        "reason": "target_gain 30.0 dB exceeds maximum of 25.0 dB"
      }

   .. note::

      Command validators are optional. If no validator is defined for a command,
      it passes through unchanged. See :doc:`../user_guide/developing_apps` for
      details on adding command validators.

   **Error Response (400):**

   .. code-block:: json

      {
        "detail": "Node 99 is not monitored by app 'NetworkControlApp'"
      }

Error Responses
---------------

.. list-table:: HTTP Status Codes
   :header-rows: 1
   :widths: 15 85

   * - Code
     - Description
   * - 200
     - Success
   * - 400
     - Bad request (invalid input)
   * - 404
     - Application not found
   * - 500
     - Internal server error

Example Usage
-------------

Using curl
~~~~~~~~~~

.. code-block:: bash

   # List all apps
   curl http://localhost:8000/apps

   # Start an app
   curl -X PUT http://localhost:8000/apps/NetworkControlApp/state \
     -H "Content-Type: application/json" \
     -d '{"state": "running"}'

   # Get measurements
   curl http://localhost:8000/apps/NetworkControlApp/measurements

   # Send command
   curl -X POST http://localhost:8000/apps/NetworkControlApp/control \
     -H "Content-Type: application/json" \
     -d '{
       "node_id": 8,
       "command": "SET_GAIN",
       "payload": {"amp_type": "preamp", "target_gain": 15.0}
     }'

Using Python
~~~~~~~~~~~~

.. code-block:: python

   import requests

   BASE_URL = "http://localhost:8000"

   # List apps
   response = requests.get(f"{BASE_URL}/apps")
   apps = response.json()

   # Start app
   response = requests.put(
       f"{BASE_URL}/apps/NetworkControlApp/state",
       json={"state": "running"}
   )

   # Get measurements
   response = requests.get(f"{BASE_URL}/apps/NetworkControlApp/measurements")
   measurements = response.json()

   # Send command
   response = requests.post(
       f"{BASE_URL}/apps/NetworkControlApp/control",
       json={
           "node_id": 8,
           "command": "SET_GAIN",
           "payload": {"amp_type": "preamp", "target_gain": 15.0}
       }
   )

API Documentation
-----------------

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Docker Deployment
=================

This guide covers deploying **ai_nn_controller** using Docker.

Docker Compose Setup
--------------------

The framework uses Docker Compose to orchestrate all services.

Starting Services
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Start all services in background
   docker compose up -d

   # View logs
   docker compose logs -f

   # Stop all services
   docker compose down

Other Compose Files
~~~~~~~~~~~~~~~~~~~

The repository ships three Compose files for different scenarios:

.. list-table:: Compose Files
   :header-rows: 1
   :widths: 30 70

   * - File
     - Purpose
   * - ``docker-compose.yml``
     - Primary workflow — 6 simulated optical nodes + ``aic_server`` running
       ``control_application_v2_example``. Use this for local development
       and the quickstart.
   * - ``docker-compose.srsran.yml``
     - srsRAN integration — swaps the 6 optical nodes for a single
       ``srsran_node`` (polls InfluxDB) and ``srsran_reader`` (a read-only
       control app). Requires an external ``docker_metrics`` network
       provided by a separately-running srsRAN + InfluxDB stack. See
       :doc:`../examples/srsran_integration`.
   * - ``deploy/compose/docker-compose.arch.yml``
     - An archived/reference variant of the root ``docker-compose.yml``,
       kept for reference. Not part of the primary workflow.

Services Overview
~~~~~~~~~~~~~~~~~

.. list-table:: Docker Services
   :header-rows: 1
   :widths: 20 20 15 45

   * - Service
     - Container
     - Port
     - Description
   * - redis
     - redis
     - 6379
     - State storage
   * - aic_register
     - aic_register
     - 5558
     - Registration service
   * - node_msg_broker
     - node_msg_broker
     - 5554-5557
     - Message routing
   * - aic_server
     - aic_server
     - 8000
     - FastAPI + MCP
   * - amp1_node
     - amp1_node
     - -
     - Simulated amplifier (node_id 3)
   * - roadm1_node
     - roadm1_node
     - -
     - Simulated ROADM (node_id 4)
   * - amp2_node
     - amp2_node
     - -
     - Simulated amplifier (node_id 5)
   * - amp3_node
     - amp3_node
     - -
     - Simulated amplifier (node_id 6)
   * - roadm2_node
     - roadm2_node
     - -
     - Simulated ROADM (node_id 7)
   * - roadm3_node
     - roadm3_node
     - -
     - Simulated ROADM with commands (node_id 8)
   * - fastapi_client
     - fastapi_client
     - -
     - CLI client container

docker-compose.yml Example
--------------------------

This is a trimmed version of the actual root ``docker-compose.yml`` (one dummy
node shown instead of all six). Note that the ``aic_network`` network is
*created* here with ``driver: bridge`` — a standalone app compose file (see
:doc:`developing_apps`) instead treats it as ``external: true`` and joins it.

.. code-block:: yaml

   services:
     redis:
       container_name: redis
       image: redis:7-alpine
       ports:
         - "6379:6379"
       networks:
         - aic_network
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 5s
         timeout: 3s
         retries: 5

     aic_register:
       container_name: aic_register
       build:
         context: ./controller_components/register/
         dockerfile: Dockerfile
       volumes:
         - ./controller_components/register/:/register
         - ./control_applications/:/control_applications
         - ./:/workspace
       command: python3 register.py
       depends_on:
         redis:
           condition: service_healthy
       networks:
         - aic_network
       ports:
         - "5558:5558"
       environment:
         - PYTHONUNBUFFERED=1

     node_msg_broker:
       container_name: node_msg_broker
       build:
         context: ./controller_components/node_msg_broker/
         dockerfile: Dockerfile
       depends_on:
         - aic_register
       networks:
         - aic_network
       ports:
         - "5554:5554"
         - "5555:5555"
         - "5557:5557"
       environment:
         - PYTHONUNBUFFERED=1

     # ... amp1_node / roadm1_node / amp2_node / amp3_node / roadm2_node /
     # roadm3_node all follow the same pattern:
     amp1_node:
       container_name: amp1_node
       build:
         context: ./
         dockerfile: network_nodes/dummy_nodes/amp1_node/Dockerfile
       volumes:
         - ./network_nodes/dummy_nodes/amp1_node/:/node
       depends_on:
         - aic_register
         - node_msg_broker
       networks:
         - aic_network
       command: >
         sh -c "sleep 5 && python3 node.py"
       environment:
         - PYTHONUNBUFFERED=1

     # Runs aic_app.py, which starts the controller with API via with_api=True.
     # Plugin installation order: framework -> plugins -> app. Plugins are
     # Python packages loaded inside this process, not separate containers.
     aic_server:
       container_name: aic_server
       build:
         context: ./
         dockerfile: control_applications/control_application_v2_example/Dockerfile
       volumes:
         - ./control_applications/control_application_v2_example/:/app
         - ./controller_components/ai_nn_controller/:/ai_nn_controller
         - ./plugins/console_plugin/:/console_plugin
       ports:
         - "8000:8000"
       networks:
         - aic_network
       environment:
         - PYTHONUNBUFFERED=1
       command: >
         sh -c "sleep 25
         && pip install --no-cache-dir /ai_nn_controller
         && pip install --no-cache-dir /console_plugin
         && pip install --no-cache-dir /app
         && python3 aic_app.py --verbose"

     fastapi_client:
       container_name: fastapi_client
       build:
         context: ./fastapi_client/
         dockerfile: Dockerfile
       volumes:
         - ./fastapi_client/:/app
       networks:
         - aic_network
       depends_on:
         - aic_server
       tty: true
       stdin_open: true
       environment:
         - PYTHONUNBUFFERED=1
       command: "/bin/bash"  # Interactive shell

   networks:
     aic_network:
       driver: bridge

Creating Dockerfiles
--------------------

Application Dockerfile
~~~~~~~~~~~~~~~~~~~~~~

This is the actual Dockerfile used by
``control_applications/control_application_v2_example/Dockerfile``. It shows
the required install order: **framework → plugins → app**. Installing the app
as a package (rather than just copying files) registers its
``ai_nn_controller.app_init`` entry point, which is what triggers
``register_specific_commands()`` automatically at startup.

.. code-block:: dockerfile

   FROM python:3.11-slim

   WORKDIR /app

   # Install system dependencies
   RUN apt-get update && apt-get install -y net-tools procps curl

   # Copy and install ai_nn_controller framework first
   COPY controller_components/ai_nn_controller/ /ai_nn_controller/
   RUN pip install /ai_nn_controller

   # Copy and install plugins (must come after framework, before the app)
   COPY plugins/console_plugin/ /console_plugin/
   RUN pip install --no-cache-dir /console_plugin

   # Copy requirements file and install app-specific dependencies
   COPY control_applications/control_application_v2_example/requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy and install the control app as a package so its entry points are
   # registered (ai_nn_controller.app_init -> bootstrap_application_bundle).
   # This is what makes register_specific_commands() get called automatically.
   COPY control_applications/control_application_v2_example/pyproject.toml /app_pkg/
   COPY control_applications/control_application_v2_example/aic_app.py /app_pkg/
   COPY control_applications/control_application_v2_example/commands.py /app_pkg/
   RUN pip install --no-cache-dir /app_pkg

   # Copy runtime files to WORKDIR (conf file + editable copies for docker
   # compose volume-mount dev workflow)
   COPY control_applications/control_application_v2_example/aic_app.py .
   COPY control_applications/control_application_v2_example/aic_app.conf .
   COPY control_applications/control_application_v2_example/commands.py .

   # Set environment variables
   ENV PYTHONUNBUFFERED=1

   # Expose FastAPI port
   EXPOSE 8000

   # Run the AIC app directly - it starts the FastAPI server via with_api=True
   CMD ["python3", "aic_app.py"]

See :doc:`developing_plugins` for how the plugin install step works.

Node Dockerfile
~~~~~~~~~~~~~~~

.. code-block:: dockerfile

   FROM python:3.9-slim

   WORKDIR /app

   RUN pip install --no-cache-dir pyzmq requests

   COPY my_node/ /app/

   CMD ["python", "node.py"]

Adding Your App to Compose
--------------------------

Add your application to ``docker-compose.yml``:

.. code-block:: yaml

   my_control_app:
     container_name: my_control_app
     build:
       context: ./
       dockerfile: control_applications/my_app/Dockerfile
     volumes:
       - ./control_applications/my_app/:/app
       - ./controller_components/ai_nn_controller/:/ai_nn_controller
     ports:
       - "8001:8000"  # Use different port if running multiple apps
     networks:
       - aic_network
     depends_on:
       - aic_register
       - node_msg_broker
     environment:
       - AIC_VERBOSE=true

Running Multiple Apps
---------------------

To run multiple AIC applications:

.. code-block:: yaml

   # First app on port 8000
   app_one:
     container_name: app_one
     build:
       context: ./
       dockerfile: control_applications/app_one/Dockerfile
     ports:
       - "8000:8000"
     networks:
       - aic_network
     depends_on:
       - aic_register
       - node_msg_broker

   # Second app on port 8001
   app_two:
     container_name: app_two
     build:
       context: ./
       dockerfile: control_applications/app_two/Dockerfile
     ports:
       - "8001:8000"
     networks:
       - aic_network
     depends_on:
       - aic_register
       - node_msg_broker

Development with Volumes
------------------------

Use volumes for live code reloading during development:

.. code-block:: yaml

   aic_server:
     volumes:
       # Mount app code for live editing
       - ./control_applications/control_application_v2_example/:/app
       # Mount framework for development
       - ./controller_components/ai_nn_controller/:/ai_nn_controller
     environment:
       - AIC_VERBOSE=true

Useful Commands
---------------

.. code-block:: bash

   # Build without cache
   docker compose build --no-cache

   # Start specific service
   docker compose up -d aic_server

   # View logs for specific service
   docker compose logs -f aic_server

   # Execute command in running container
   docker compose exec aic_server python -c "print('hello')"

   # Restart a service
   docker compose restart aic_server

   # Remove all containers and volumes
   docker compose down -v

Health Checks
-------------

Add health checks to ensure services are ready:

.. code-block:: yaml

   aic_server:
     healthcheck:
       test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
       interval: 10s
       timeout: 5s
       retries: 5
       start_period: 30s

Production Considerations
-------------------------

1. **Use specific image tags** instead of ``:latest``
2. **Set resource limits**:

   .. code-block:: yaml

      deploy:
        resources:
          limits:
            cpus: '0.5'
            memory: 512M

3. **Use secrets for sensitive data**
4. **Configure logging**:

   .. code-block:: yaml

      logging:
        driver: "json-file"
        options:
          max-size: "10m"
          max-file: "3"

5. **Set restart policies**:

   .. code-block:: yaml

      restart: unless-stopped

Troubleshooting
---------------

Container Won't Start
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check logs
   docker compose logs aic_server

   # Check if dependencies are running
   docker compose ps

Network Issues
~~~~~~~~~~~~~~

.. code-block:: bash

   # Inspect network
   docker network inspect ai_nn_controller_aic_network

   # Test connectivity from container
   docker compose exec aic_server ping aic_register

Port Conflicts
~~~~~~~~~~~~~~

If ports are in use:

.. code-block:: bash

   # Find process using port
   lsof -i :8000

   # Or change port in docker-compose.yml
   ports:
     - "8080:8000"  # Use 8080 instead

Next Steps
----------

- :doc:`../api/rest_api` - REST API reference
- :doc:`../examples/multi_node_monitoring` - Multi-node example

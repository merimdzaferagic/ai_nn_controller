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
   docker-compose up -d

   # View logs
   docker-compose logs -f

   # Stop all services
   docker-compose down

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

.. code-block:: yaml

   version: '3.8'

   services:
     redis:
       image: redis:alpine
       container_name: redis
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
       ports:
         - "5558:5558"
       networks:
         - aic_network
       depends_on:
         redis:
           condition: service_healthy

     node_msg_broker:
       container_name: node_msg_broker
       build:
         context: ./controller_components/node_msg_broker/
         dockerfile: Dockerfile
       ports:
         - "5554:5554"
         - "5555:5555"
         - "5556:5556"
         - "5557:5557"
       networks:
         - aic_network

     aic_server:
       container_name: aic_server
       build:
         context: ./
         dockerfile: control_applications/control_application_v2_example/Dockerfile
       volumes:
         - ./control_applications/control_application_v2_example/:/app
         - ./controller_components/ai_nn_controller/:/ai_nn_controller
       ports:
         - "8000:8000"
       networks:
         - aic_network
       depends_on:
         - aic_register
         - node_msg_broker

     amp1_node:
       container_name: amp1_node
       build:
         context: ./network_nodes/dummy_nodes/amp1_node/
         dockerfile: Dockerfile
       networks:
         - aic_network
       depends_on:
         - aic_register
         - node_msg_broker

   networks:
     aic_network:
       driver: bridge

Creating Dockerfiles
--------------------

Application Dockerfile
~~~~~~~~~~~~~~~~~~~~~~

Create a Dockerfile for your application:

.. code-block:: dockerfile

   FROM python:3.9-slim

   WORKDIR /app

   # Install system dependencies
   RUN apt-get update && apt-get install -y --no-install-recommends \
       gcc \
       && rm -rf /var/lib/apt/lists/*

   # Install Python dependencies
   RUN pip install --no-cache-dir \
       pyzmq \
       fastapi \
       uvicorn \
       pydantic \
       redis \
       requests \
       sse-starlette

   # Copy the framework package
   COPY controller_components/ai_nn_controller/ /ai_nn_controller/
   RUN pip install /ai_nn_controller

   # Copy application files
   COPY control_applications/my_app/ /app/

   # Set environment variables
   ENV PYTHONUNBUFFERED=1

   # Run the application
   CMD ["python", "aic_app.py", "--verbose"]

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
   docker-compose build --no-cache

   # Start specific service
   docker-compose up -d aic_server

   # View logs for specific service
   docker-compose logs -f aic_server

   # Execute command in running container
   docker-compose exec aic_server python -c "print('hello')"

   # Restart a service
   docker-compose restart aic_server

   # Remove all containers and volumes
   docker-compose down -v

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
   docker-compose logs aic_server

   # Check if dependencies are running
   docker-compose ps

Network Issues
~~~~~~~~~~~~~~

.. code-block:: bash

   # Inspect network
   docker network inspect ai_nn_controller_aic_network

   # Test connectivity from container
   docker-compose exec aic_server ping aic_register

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

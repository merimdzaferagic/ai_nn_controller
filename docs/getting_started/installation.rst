Installation
============

This guide covers how to install and set up **ai_nn_controller**.

Prerequisites
-------------

Before installing, ensure you have:

- **Python 3.9+**: The framework requires Python 3.9 or newer
- **Docker and Docker Compose**: For running the distributed services
- **Git**: For cloning the repository

System Requirements
~~~~~~~~~~~~~~~~~~~

- Operating System: Linux, macOS, or Windows (with WSL2 for Docker)
- Memory: Minimum 4 GB RAM recommended
- Disk Space: At least 2 GB for Docker images

Installation Methods
--------------------

Method 1: Docker Compose (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The easiest way to run the complete framework is using Docker Compose:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/merimdzaferagic/ai_nn_controller.git
   cd ai_nn_controller

   # Start all services
   docker-compose up -d

   # Verify services are running
   docker-compose ps

This starts:

- **Redis** (port 6379): State storage
- **aic_register** (port 5558): Registration service
- **node_msg_broker** (ports 5554-5557): Message routing
- **aic_server** (port 8000): FastAPI + MCP server
- **Network nodes**: Simulated optical devices

Method 2: Local Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For local development without Docker:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/merimdzaferagic/ai_nn_controller.git
   cd ai_nn_controller

   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install the core framework (editable)
   cd controller_components/ai_nn_controller
   pip install -e .

   # Install additional dependencies
   pip install pyzmq fastapi uvicorn pydantic redis requests sse-starlette

Verifying Installation
----------------------

After installation, verify everything works:

.. code-block:: bash

   # Check Python package
   python -c "from ai_nn_controller import AicApp, AicController; print('OK')"

   # If using Docker, check services
   curl http://localhost:8000/health
   curl http://localhost:8000/apps

You should see a health check response and a list of registered applications.

Dependencies
------------

Core Dependencies
~~~~~~~~~~~~~~~~~

- ``pyzmq>=25.0.0`` — ZeroMQ messaging
- ``fastapi>=0.100.0`` — REST API framework
- ``uvicorn[standard]>=0.23.0`` — ASGI server
- ``pydantic>=2.0.0`` — Data validation
- ``redis>=4.5.0`` — State storage
- ``requests>=2.28.0`` — HTTP client
- ``sse-starlette>=1.6.0`` — Server-Sent Events

Development Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~

- ``pytest`` — Testing framework
- ``pytest-asyncio`` — Async test support
- ``black`` — Code formatting
- ``isort`` — Import sorting
- ``mypy`` — Type checking

Next Steps
----------

Once installed, proceed to:

- :doc:`quickstart` — Run your first application
- :doc:`configuration` — Configure the framework
- :doc:`../user_guide/developing_apps` — Build custom control applications

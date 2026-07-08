Development Setup
=================

This guide covers setting up a development environment for **ai_nn_controller**.

Prerequisites
-------------

- Python 3.9 or newer
- Docker and Docker Compose
- Git

Setting Up
----------

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/merimdzaferagic/ai_nn_controller.git
      cd ai_nn_controller

2. Create and activate a virtual environment:

   .. code-block:: bash

      python -m venv venv
      source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install the framework in development mode:

   .. code-block:: bash

      cd controller_components/ai_nn_controller
      pip install -e ".[dev]"

4. Install additional dependencies:

   .. code-block:: bash

      pip install pyzmq fastapi uvicorn pydantic redis requests sse-starlette

Running Services
----------------

Start infrastructure services:

.. code-block:: bash

   docker compose up -d redis aic_register node_msg_broker

Run the example application locally:

.. code-block:: bash

   cd control_applications/control_application_v2_example
   python aic_app.py --verbose

Project Structure
-----------------

.. code-block:: text

   .
   ├── control_applications/
   │   └── control_application_v2_example/  # Reference control application
   ├── network_nodes/
   │   ├── dummy_nodes/        # Simulated test nodes
   │   ├── srsran_node/        # srsRAN 5G RAN integration (InfluxDB bridge)
   │   └── twilight_nodes/     # Twilight optical network bridge nodes
   ├── fastapi_client/         # Python client for the AIC REST API
   └── controller_components/
       ├── ai_nn_controller/   # Core framework (editable install)
       │   ├── AicApp.py
       │   ├── AicController.py
       │   ├── decorators/
       │   ├── managers/
       │   ├── mcp/
       │   ├── protocol/
       │   └── ...
       ├── controlled_entity/  # Node-side framework
       ├── register/           # Registration service
       └── node_msg_broker/    # Message broker

Development Workflow
--------------------

1. **Make changes** to framework code in ``ai_nn_controller/``
2. **Test locally** with a simple application
3. **Run tests** with pytest
4. **Format code** with black and isort
5. **Build Docker images** if needed
6. **Test with Docker Compose**

Running Tests
-------------

.. code-block:: bash

   # Run all tests
   pytest controller_components/

   # Run with coverage
   pytest --cov=ai_nn_controller controller_components/

   # Run specific test file
   pytest controller_components/tests/test_registry.py

Code Formatting
---------------

.. code-block:: bash

   # Format code
   black controller_components/

   # Sort imports
   isort controller_components/

   # Type checking
   mypy controller_components/ai_nn_controller/

Building Documentation
----------------------

.. code-block:: bash

   cd docs
   pip install -r requirements.txt
   make html

   # Live preview
   make livehtml

View documentation at ``docs/_build/html/index.html``

Debugging
---------

Enable verbose logging:

.. code-block:: python

   AicController(with_api=True, verbose=True).run()

Or via command line:

.. code-block:: bash

   python aic_app.py --verbose

View Docker logs:

.. code-block:: bash

   docker compose logs -f aic_server
   docker compose logs -f node_msg_broker

Common Issues
-------------

**ZMQ Connection Errors**

Ensure infrastructure is running:

.. code-block:: bash

   docker compose ps

**Import Errors**

Install the framework:

.. code-block:: bash

   cd controller_components/ai_nn_controller
   pip install -e .

**Port Conflicts**

Check for processes using required ports:

.. code-block:: bash

   lsof -i :8000
   lsof -i :5558

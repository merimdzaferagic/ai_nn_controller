ai_nn_controller Documentation
======================

Welcome to the documentation for **ai_nn_controller** — an open-source, AI-native network
controller framework for building intelligent control applications across heterogeneous
network domains.

.. image:: https://img.shields.io/badge/python-3.9+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python Version

.. image:: https://img.shields.io/badge/license-AGPL--3.0-green.svg
   :alt: License

Overview
--------

ai_nn_controller is a domain-agnostic framework for building AI-powered control applications
that manage network equipment across any domain — optical, wireless, RAN, core network,
and more. Key features:

- **Declarative App Definition**: Define control apps with simple Python decorators
- **Automatic API Generation**: FastAPI REST endpoints auto-generated for each app
- **MCP Tool Generation**: AI agents (like Claude) can control apps via auto-generated MCP tools
- **Plugin System**: Reusable, installable plugins give control apps typed access to external services (storage, model registries, monitoring)
- **Distributed Architecture**: Nodes, register, and message broker communicate via ZeroMQ
- **Dynamic Discovery**: Nodes and apps only need to know the register address

Quick Example
-------------

.. code-block:: python

   from ai_nn_controller.decorators.aic_app import aic_app
   from ai_nn_controller.AicApp import AicApp
   from ai_nn_controller.AicController import AicController

   @aic_app(name="MyControlApp")
   class MyControlApp(AicApp):
       aic_app_id = 1
       control_loop_update_time = 2
       read_measurements = {3: ["gain", "power"]}
       control_functions = {3: ["SET_GAIN"]}
       # cell_ids auto-generated: [3]

       @classmethod
       def process(cls, measurements):
           gain = measurements.get(3, [{}])[-1].get("gain", 0)
           if gain > 25:
               cls.add_command(("SET_GAIN", {"node_id": 3, "value": {"target_gain": 20}}))

   if __name__ == "__main__":
       AicController(with_api=True).run()

Getting Started
---------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting_started/installation
   getting_started/quickstart
   getting_started/configuration

User Guide
----------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/architecture
   user_guide/developing_apps
   user_guide/developing_nodes
   user_guide/developing_plugins
   user_guide/commands
   user_guide/docker

API Reference
-------------

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/ai_nn_controller
   api/plugin_framework
   api/plugins
   api/register
   api/broker
   api/rest_api
   api/mcp

Examples
--------

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/basic_app
   examples/dummy_node
   examples/multi_node_monitoring
   examples/conflict_mitigation
   examples/plugin_example
   examples/srsran_integration

Contributing
------------

.. toctree::
   :maxdepth: 1
   :caption: Contributing

   contributing/guidelines
   contributing/development

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

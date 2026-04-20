Contributing Guidelines
=======================

Thank you for your interest in contributing to **ai_nn_controller**!

Getting Started
---------------

1. Fork the repository
2. Clone your fork:

   .. code-block:: bash

      git clone https://github.com/YOUR_USERNAME/ai_nn_controller.git
      cd ai_nn_controller

3. Set up the development environment:

   .. code-block:: bash

      python -m venv venv
      source venv/bin/activate
      pip install -e controller_components/ai_nn_controller[dev]

4. Create a branch for your changes:

   .. code-block:: bash

      git checkout -b feature/my-feature

Code Style
----------

We follow these coding standards:

- **PEP 8** for Python code style
- **Black** for code formatting
- **isort** for import sorting
- **Type hints** for function signatures

Run formatters before committing:

.. code-block:: bash

   black controller_components/
   isort controller_components/

Documentation
-------------

- All public functions and classes should have docstrings
- Use Google-style docstrings:

  .. code-block:: python

     def my_function(param1: int, param2: str) -> bool:
         """
         Brief description.

         Longer description if needed.

         Args:
             param1: Description of param1
             param2: Description of param2

         Returns:
             Description of return value

         Raises:
             ValueError: When something is wrong
         """

- Update documentation when changing functionality
- Add examples for new features

Testing
-------

- Write tests for new features
- Ensure existing tests pass:

  .. code-block:: bash

     pytest controller_components/

- Test with Docker:

  .. code-block:: bash

     docker-compose up -d
     # Run your tests
     docker-compose down

Pull Request Process
--------------------

1. Update documentation for any changed functionality
2. Add tests for new features
3. Ensure all tests pass
4. Update the CHANGELOG if applicable
5. Create a pull request with a clear description

Commit Messages
---------------

Use clear, descriptive commit messages:

- Start with a verb (Add, Fix, Update, Remove)
- Keep the first line under 50 characters
- Add details in the body if needed

Good examples:

.. code-block:: text

   Add SET_TILT command handler

   Fix measurement routing for multi-node apps

   Update documentation for MCP integration

Reporting Issues
----------------

When reporting issues, include:

- Python version
- Docker version (if applicable)
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output

Feature Requests
----------------

For feature requests:

- Describe the use case
- Explain the proposed solution
- Consider alternatives

Questions
---------

- Check existing documentation first
- Search existing issues
- Open a new issue with the "question" label

FROM python:3.11-slim

WORKDIR /plugin

# Install the framework first (plugins depend on it)
COPY controller_components/ai_nn_controller/ /ai_nn_controller/
RUN pip install --no-cache-dir /ai_nn_controller

# Install the plugin package so its entry point is registered
COPY plugins/console_plugin/ /plugin/
RUN pip install --no-cache-dir /plugin

ENV PYTHONUNBUFFERED=1

# Verify the plugin registers correctly and its API works
CMD ["python3", "-c", "\
from aic_plugin import ConsolePlugin; \
ConsolePlugin.connect(); \
ConsolePlugin.log('ConsolePlugin image is healthy'); \
ConsolePlugin.log_event('docker_healthcheck', status='ok'); \
ConsolePlugin.disconnect() \
"]

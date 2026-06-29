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

# Copy runtime files to WORKDIR (conf file + editable copies for docker-compose
# volume-mount dev workflow)
COPY control_applications/control_application_v2_example/aic_app.py .
COPY control_applications/control_application_v2_example/aic_app.conf .
COPY control_applications/control_application_v2_example/commands.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose FastAPI port
EXPOSE 8000

# Run the AIC app directly - it starts the FastAPI server via with_api=True
CMD ["python3", "aic_app.py"]

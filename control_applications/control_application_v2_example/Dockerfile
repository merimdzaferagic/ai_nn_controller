FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y net-tools procps curl

# Copy and install ai_nn_controller framework first
COPY controller_components/ai_nn_controller/ /ai_nn_controller/
RUN pip install /ai_nn_controller

# Copy requirements file and install app-specific dependencies
COPY control_applications/control_application_v2_example/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY control_applications/control_application_v2_example/aic_app.py .
COPY control_applications/control_application_v2_example/aic_app.conf .
COPY control_applications/control_application_v2_example/commands.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose FastAPI port
EXPOSE 8000

# Run the AIC app directly - it starts the FastAPI server via with_api=True
CMD ["python3", "aic_app.py"]

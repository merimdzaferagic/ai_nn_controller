FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y net-tools procps curl

# Copy and install ai_nn_controller framework first
COPY controller_components/ai_nn_controller/ /ai_nn_controller/
RUN pip install /ai_nn_controller

# Copy requirements file and install app-specific dependencies
COPY control_applications/srsran_read_measurements/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY control_applications/srsran_read_measurements/aic_app.py .
COPY control_applications/srsran_read_measurements/aic_app.conf .
COPY control_applications/srsran_read_measurements/commands.py .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python3", "aic_app.py"]

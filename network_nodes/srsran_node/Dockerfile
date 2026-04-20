FROM python:3.9-slim

COPY controller_components/controlled_entity/ /tmp/controlled_entity/
RUN pip install --no-cache-dir /tmp/controlled_entity && rm -rf /tmp/controlled_entity

RUN pip install "influxdb-client<2"

WORKDIR /node

COPY network_nodes/srsran_node/*.py ./
COPY network_nodes/srsran_node/*.conf ./

CMD ["python3", "node.py"]

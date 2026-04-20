FROM python:3.9-slim

COPY controller_components/controlled_entity/ /tmp/controlled_entity/
RUN pip install --no-cache-dir /tmp/controlled_entity && rm -rf /tmp/controlled_entity

WORKDIR /node

COPY network_nodes/dummy_nodes/amp2_node/*.py ./
COPY network_nodes/dummy_nodes/amp2_node/*.conf ./

CMD ["python3", "node.py"]

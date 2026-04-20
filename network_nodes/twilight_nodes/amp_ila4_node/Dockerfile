FROM python:3.9-slim

RUN pip install requests

WORKDIR /node

# Build context should be twilight_nodes/
COPY twilight_client.py ./
COPY amp_ila4_node/node.py ./
COPY amp_ila4_node/node.conf ./

CMD ["python3", "node.py"]

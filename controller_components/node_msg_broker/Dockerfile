FROM python:3.8

WORKDIR /node_msg_broker

RUN pip install pyzmq

COPY * ./

CMD ["python3", "node_msg_broker.py"]

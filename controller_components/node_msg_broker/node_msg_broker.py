# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

#!/usr/bin/env python3
"""
ZMQ-based message broker for measurements and commands.
Nodes PUSH measurements to the broker on port 5555.
Broker PUBLISHes all measurements on port 5554 for aic_apps to subscribe.
Each message format: "topic;{json_payload}" where topic is the node_id.
"""
import zmq
import time
import threading
import sys


class UnifiedMeasurementBroker:
    """
    Broker that receives measurements from nodes (PULL) and publishes them
    on a single PUB socket (port 5554) for aic_apps to subscribe to.

    Pattern: Nodes PUSH -> Broker PULL -> Broker PUB -> aic_apps SUB

    Nodes connect to the broker's PULL socket and push messages.
    The broker doesn't need to know which nodes exist - they self-register.
    """

    def __init__(self, context, recv_port=5555, send_port=5554):
        """
        Args:
            context: ZMQ context
            recv_port: Port to receive measurements from nodes (PULL socket)
            send_port: Port to publish all measurements on (PUB socket)
        """
        self.context = context
        self.recv_port = recv_port
        self.send_port = send_port

        # Create PULL socket to receive from all nodes
        self.recv_socket = self.context.socket(zmq.PULL)
        recv_addr = f"tcp://0.0.0.0:{self.recv_port}"
        print(f"[MEAS-BROKER] Binding PULL to: {recv_addr}")
        sys.stdout.flush()
        self.recv_socket.bind(recv_addr)

        # Create PUB socket to publish to all aic_apps
        self.send_socket = self.context.socket(zmq.PUB)
        send_addr = f"tcp://0.0.0.0:{self.send_port}"
        print(f"[MEAS-BROKER] Binding PUB to: {send_addr}")
        sys.stdout.flush()
        self.send_socket.bind(send_addr)

        # Give time for binds to complete
        time.sleep(1)
        print(f"[MEAS-BROKER] Ready - receiving on port {recv_port}, publishing on port {send_port}")
        sys.stdout.flush()

    def run(self):
        """Receive messages from nodes and forward to aic_apps."""
        print(f"[MEAS-BROKER] Starting message forwarding...")
        sys.stdout.flush()
        msg_count = 0

        while True:
            try:
                # Receive from any node (blocking)
                msg = self.recv_socket.recv_string()
                msg_count += 1

                # Forward to aic_apps (preserves topic;payload format)
                self.send_socket.send_string(msg)

                # Log first 10 messages, then every 20th
                if msg_count <= 10 or msg_count % 20 == 0:
                    print(f"[MEAS-BROKER] Forwarded msg #{msg_count}: {msg[:80]}...")
                    sys.stdout.flush()

            except Exception as e:
                print(f"[MEAS-BROKER] Error forwarding: {e}")
                sys.stdout.flush()


class CommandBroker:
    """Broker for command messages: aic_app PUSH -> broker PULL -> broker PUB -> nodes SUB"""

    def __init__(self, context, recv_port=5556, send_port=5557):
        self.context = context
        self.recv_port = recv_port
        self.send_port = send_port

        # Create PULL socket to receive commands from aic_apps (same pattern as measurements)
        self.recv_socket = self.context.socket(zmq.PULL)
        recv_addr = f"tcp://0.0.0.0:{self.recv_port}"
        print(f"[CMD-BROKER] Binding PULL to: {recv_addr}")
        sys.stdout.flush()
        self.recv_socket.bind(recv_addr)

        # Create PUB socket to publish commands to nodes
        self.send_socket = self.context.socket(zmq.PUB)
        send_addr = f"tcp://0.0.0.0:{self.send_port}"
        print(f"[CMD-BROKER] Binding PUB to: {send_addr}")
        sys.stdout.flush()
        self.send_socket.bind(send_addr)

        # Give time for binds to complete
        time.sleep(1)
        print(f"[CMD-BROKER] Ready - receiving on port {recv_port}, publishing on port {send_port}")
        sys.stdout.flush()

    def run(self):
        """Forward commands from aic_app to nodes"""
        print("[CMD-BROKER] Starting command forwarding...")
        sys.stdout.flush()
        cmd_count = 0

        while True:
            try:
                # Receive from aic_app (blocking)
                msg = self.recv_socket.recv_string()
                cmd_count += 1
                
                print(f"[CMD-BROKER] Received command #{cmd_count}: {msg[:100]}")
                sys.stdout.flush()

                # Forward to nodes (preserves topic;payload format)
                self.send_socket.send_string(msg)
                print(f"[CMD-BROKER] Forwarded command #{cmd_count}")
                sys.stdout.flush()
            except Exception as e:
                print(f"[CMD-BROKER] Error: {e}")
                sys.stdout.flush()


def main():
    context = zmq.Context()
    print("[MAIN] ZMQ Broker starting...")
    sys.stdout.flush()

    # Create measurement broker:
    # - Nodes PUSH to port 5555
    # - Broker PUBLISHes on port 5554 for aic_apps
    # No need to know which nodes exist - they connect to us
    meas_broker = UnifiedMeasurementBroker(context, recv_port=5555, send_port=5554)

    # Command broker (same pattern as measurements):
    # - aic_apps PUSH to port 5556
    # - Broker PUBLISHes on port 5557 for nodes
    cmd_broker = CommandBroker(context, recv_port=5556, send_port=5557)

    # Start measurement broker in separate thread
    meas_thread = threading.Thread(target=meas_broker.run, daemon=True)
    meas_thread.start()

    # Start command broker in separate thread
    cmd_thread = threading.Thread(target=cmd_broker.run, daemon=True)
    cmd_thread.start()

    print("[MAIN] Broker running. Press Ctrl+C to stop.")
    print("[MAIN] Nodes PUSH measurements to port 5555")
    print("[MAIN] Broker PUBLISHes measurements on port 5554 for aic_apps")
    print("[MAIN] aic_apps PUSH commands to port 5556")
    print("[MAIN] Broker PUBLISHes commands on port 5557 for nodes")
    sys.stdout.flush()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[MAIN] Shutting down...")
        sys.stdout.flush()
        context.term()
        sys.exit(0)


if __name__ == "__main__":
    main()

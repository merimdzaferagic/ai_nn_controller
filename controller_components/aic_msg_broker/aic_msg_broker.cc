// to compile g++ zmq_broker.cpp -o th_zmq_broker -lzmq -pthread
#include "parse_config.h"
#include <thread>
#include <chrono>
#include <zmq.h>

void expose_measurements(void *shared_context, std::string ip_address,
                         std::string recv_measurements_port,
                         std::string pub_measurements_port) {
  std::cerr << "Measurements exposure broker started\n";
  // Use shared context passed as parameter
  //  Socket to listen to enbs
  void *sub_BS = zmq_socket(shared_context, ZMQ_PULL);
  std::string sub_socket = "tcp://" + ip_address + ":" + recv_measurements_port;
  zmq_bind(sub_BS, sub_socket.c_str());
  //  Socket to share with xApps
  std::string pub_socket = "tcp://" + ip_address + ":" + pub_measurements_port;
  void *pub_xapps = zmq_socket(shared_context, ZMQ_PUB);
  zmq_bind(pub_xapps, pub_socket.c_str());

  zmq_proxy(sub_BS, pub_xapps, NULL);
}

void expose_commands(void *shared_context, std::string ip_address, std::string recv_commands_port,
                     std::string pub_commands_port) {
  std::cerr << "Commands exposure broker started\n";
  // Use shared context passed as parameter
  //  Socket to listen to xApps
  void *sub_xapps = zmq_socket(shared_context, ZMQ_SUB);
  std::string sub_socket = "tcp://" + ip_address + ":" + recv_commands_port;
  zmq_connect(sub_xapps, sub_socket.c_str());
  zmq_setsockopt(sub_xapps, ZMQ_SUBSCRIBE, "", 0);
  //  Socket to share with enbs
  void *pub_BS = zmq_socket(shared_context, ZMQ_PUB);
  std::string pub_socket = "tcp://" + ip_address + ":" + pub_commands_port;
  zmq_bind(pub_BS, pub_socket.c_str());

  zmq_proxy(sub_xapps, pub_BS, NULL);
}

int main() {
  std::map<std::string, std::string> config =
      read_config("aic_msg_broker.conf");

  std::string ip_address = config["ip_address"];

  std::string recv_measurements_port = config["recv_measurements"];
  std::string pub_measurements_port = config["pub_measurements"];

  std::string recv_commands_port = config["recv_commands"];
  std::string pub_commands_port = config["pub_commands"];

  std::cerr << "Creating shared context...\n";
  std::cerr.flush();
  void *shared_context = zmq_ctx_new();

  std::thread th_expose_measurements(expose_measurements, shared_context, ip_address,
                                     recv_measurements_port,
                                     pub_measurements_port);
  std::thread th_expose_commands(expose_commands, shared_context, ip_address,
                                 recv_commands_port, pub_commands_port);

  th_expose_measurements.detach();
  th_expose_commands.detach();

  // Keep main thread alive
  while (true) {
    std::this_thread::sleep_for(std::chrono::seconds(1));
  }

  return 0;
}

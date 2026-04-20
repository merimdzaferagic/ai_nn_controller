#g++ zmq_broker.cpp -o th_zmq_broker -lzmq -pthread
CXX= g++
LIBS= -lzmq -pthread

SRC_FILES= aic_msg_broker.cc parse_config.cc
OBJ_FILES= aic_msg_broker.o parse_config.o

all: $(OBJ_FILES) 
	$(CXX) $(OBJ_FILES) -o aic_msg_broker $(LIBS)

%.o : %.cc 
	$(CXX) -c $< -o $@

clean: 
	rm -f $(OBJ_FILES) aic_msg_broker

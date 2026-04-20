FROM ubuntu:focal as base

RUN apt-get update #
RUN apt-get upgrade -y

RUN DEBIAN_FRONTEND=noninteractive apt install -y \
     build-essential \
     cmake libfftw3-dev \
     libmbedtls-dev \
     libboost-program-options-dev \
     libconfig++-dev \
     libsctp-dev \
     curl \
     iputils-ping \
     iproute2 \
     iptables \
     unzip \
     git \
     libtool

RUN rm -rf /var/lib/apt/lists/*


WORKDIR /zmq

RUN git clone https://github.com/zeromq/libzmq.git ./
RUN ./autogen.sh
RUN ./configure
RUN make
RUN make install
RUN ldconfig


WORKDIR /czmq
RUN git clone https://github.com/zeromq/czmq.git ./
RUN ./autogen.sh
RUN ./configure
RUN make
RUN make install
RUN ldconfig

WORKDIR /aic_msg_broker
COPY * ./
RUN make


#to run it run the following command:
# sudo docker build -t container-test .
# sudo docker run -p 172.16.25.20:5554:5554 -p 172.16.25.20:5555:5555 -p 172.16.25.20:5556:5556 -p 172.16.25.20:5557:5557 container-test ./databus`

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
     libtool \
     python3.9 \
     python3.9-dev \
     python3-pip

RUN rm -rf /var/lib/apt/lists/*


#WORKDIR /zmq

#RUN git clone https://github.com/zeromq/libzmq.git ./
#RUN ./autogen.sh
#RUN ./configure
#RUN make
#RUN make install
#RUN ldconfig


#WORKDIR /czmq
#RUN git clone https://github.com/zeromq/czmq.git ./
#RUN ./autogen.sh
#RUN ./configure
#RUN make
#RUN make install
#RUN ldconfig

RUN pip install pyzmq
RUN pip install redis

WORKDIR /register
COPY *.py ./
COPY *.conf ./
COPY register_utils ./register_utils

CMD ["python3", "register.py"]

#!/bin/bash
echo "Setting up the dummy port for the databus"
sudo modprobe dummy
sudo lsmod | grep dummy
sudo ip link add eth11 type dummy
ip link show eth11
sudo ip addr add 192.168.53.11/24 brd + dev eth11
ifconfig -a

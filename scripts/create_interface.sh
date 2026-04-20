#!/bin/bash
echo "Setting up the dummy port for the caddy server"
sudo modprobe dummy
sudo lsmod | grep dummy
sudo ip link add eth10 type dummy
ip link show eth10
sudo ip addr add 192.168.52.11/24 brd + dev eth10
ifconfig -a

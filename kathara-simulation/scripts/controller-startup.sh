#!/bin/bash

# Inside controller-startup.sh
ip addr add $CONTROLLER_ADDRESS/16 dev eth0
ip link set eth0 up

sed -i '/127.0.1.1/d' /etc/hosts

# Start Ryu
# ryu-manager /controller/main.py

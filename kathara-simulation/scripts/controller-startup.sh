#!/bin/bash

# Inside controller-startup.sh
ip addr add $CONTROLLER_ADDRESS/16 dev eth0
ip link set eth0 up

# Start Ryu
# ryu-manager /controller/main.py

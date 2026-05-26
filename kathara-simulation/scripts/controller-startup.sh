#!/bin/bash

# Inside controller-startup.sh
ip addr add $CONTROLLER_ADDRESS/16 dev eth0
ip link set eth0 up

# Start Ryu
# ryu-manager --ofp-tcp-listen-port 6653 /controller/main.py

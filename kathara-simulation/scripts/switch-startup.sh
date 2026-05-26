#!/bin/bash

/usr/share/openvswitch/scripts/ovs-ctl --system-id=random start
ovs-vsctl add-br s1

for PAIR in $DEVICE_INTERFACES; do
    IFS="=" read -r IFACE IP <<< "$PAIR"
    ip addr add $IP/16 dev $IFACE
    ip link set $IFACE up
    ovs-vsctl add-port s1 $IFACE
done

ovs-vsctl set bridge s1 protocols=[OpenFlow13]

ovs-vsctl set-fail-mode s1 secure

ovs-vsctl set-controller s1 tcp:$CONTROLLER_ADDRESS

# ip towards controller
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=100, in_port=2, ip, nw_dst=$CONTROLLER_ADDRESS, actions=output:1"
# and back
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=100, in_port=1, ip, nw_src=$CONTROLLER_ADDRESS, actions=output:2"

# ARP towards the controller
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=100, in_port=2, arp, arp_tpa=$CONTROLLER_ADDRESS, actions=output:1"
# and back
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=100, in_port=1, arp, arp_spa=$CONTROLLER_ADDRESS, actions=output:2"

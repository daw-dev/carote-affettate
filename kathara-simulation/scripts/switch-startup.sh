#!/bin/bash

/usr/share/openvswitch/scripts/ovs-ctl --system-id=random start
ovs-vsctl add-br s1

for DEV_PATH in /sys/class/net/eth*; do
    IFACE=$(basename $DEV_PATH)
    
    if [ "$IFACE" == "eth0" ]; then
        continue
    fi

    ip link set $IFACE up
    
    ovs-vsctl add-port s1 $IFACE
done

ip addr add $DEVICE_ADDRESS/16 dev s1
ip link set s1 up

ip addr add $HIDDEN_IP/16 dev eth0
ip link set eth0 up

DPID=$(printf "%016x" $SWITCH_ID)

ovs-vsctl set bridge s1 other-config:datapath-id=$DPID protocols=[OpenFlow13]

ovs-vsctl set-fail-mode s1 secure

ovs-vsctl set-controller s1 tcp:$CONTROLLER_ADDRESS

# ---------------------------------------------------------
# OUTBOUND: Towards the controller (from ANY port, including LOCAL)
# ---------------------------------------------------------
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=100, ip, nw_dst=$CONTROLLER_ADDRESS, actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=100, arp, arp_tpa=$CONTROLLER_ADDRESS, actions=output:1"

# ---------------------------------------------------------
# INBOUND: From the controller (Forward back to port 2)
# ---------------------------------------------------------
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=100, in_port=1, ip, nw_src=$CONTROLLER_ADDRESS, actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=100, in_port=1, arp, arp_spa=$CONTROLLER_ADDRESS, actions=output:2"

# ---------------------------------------------------------
# INTERCEPT: Traffic meant for the switch itself
# ---------------------------------------------------------
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=110, ip, nw_dst=$DEVICE_ADDRESS, actions=LOCAL"
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=110, arp, arp_tpa=$DEVICE_ADDRESS, actions=LOCAL"

# cat /proc/sys/net/ipv4/ip_forward
#
# BANDWIDTH MASSIMA NELLA REGOLA

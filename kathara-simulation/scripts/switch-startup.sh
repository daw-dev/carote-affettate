#!/bin/bash

shopt -s expand_aliases

alias ovs-ofctl="ovs-ofctl -O OpenFlow13"

/usr/share/openvswitch/scripts/ovs-ctl --system-id=random start
ovs-vsctl add-br br0

for DEV_PATH in /sys/class/net/eth*; do
    IFACE=$(basename $DEV_PATH)
    
    ip link set $IFACE up

    if [ "$IFACE" == "eth0" ]; then
        continue
    fi
    
    ovs-vsctl add-port br0 $IFACE
done

ip link set br0 up

ip addr add $DEVICE_ADDRESS/16 dev br0

ip addr add $HIDDEN_IP/16 dev eth0

DPID=$(printf "%016x" $SWITCH_ID)

ovs-vsctl set bridge br0 other-config:datapath-id=$DPID protocols=[OpenFlow13]

ovs-vsctl set-fail-mode br0 secure

ovs-vsctl set-controller br0 tcp:$CONTROLLER_ADDRESS

iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

ovs-ofctl add-flow br0 "priority=100, arp, in_port=1, actions=LOCAL"

ovs-ofctl add-flow br0 "priority=100, ip, in_port=1, nw_dst=$CONTROLLER_ADDRESS, actions=LOCAL"

ovs-ofctl add-flow br0 "priority=100, in_port=LOCAL, actions=output:1"

echo 'alias ovs-ofctl="ovs-ofctl -O OpenFlow13"' >> /root/.bashrc

#
# cat /proc/sys/net/ipv4/ip_forward
#
# BANDWIDTH MASSIMA NELLA REGOLA

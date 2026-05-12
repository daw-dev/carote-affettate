#!/bin/bash

for PAIR in $DEVICE_INTERFACES; do
    IFS="=" read -r IFACE IP <<< "$PAIR"
    
    ip addr add $IP dev $IFACE
    ip link set $IFACE up
done

# tc $CAPACITY

/usr/share/openvswitch/scripts/ovs-ctl --system-id=random start
ovs-vsctl add-br s1
# fail mode means: what if I don't find a controller?
# standalone (default) means learn and install flows automatically (behave like a normal switch)
# secure means do not learn, and do not install flows if there is no controller
# ovs-vsctl set-fail-mode s1 standalone
ovs-vsctl set-fail-mode s1 secure
ovs-vsctl add-port s1 eth1
ovs-vsctl add-port s1 eth2
ovs-vsctl add-port s1 eth3

ovs-vsctl set bridge s1 protocols=[OpenFlow13]
ovs-vsctl set-controller s1 tcp:$CONTROLLER_ADDRESS

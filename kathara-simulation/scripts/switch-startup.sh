#!/bin/bash

# ==========================================
# 1. CONTROL PLANE (Management Interface)
# ==========================================
for PAIR in $DEVICE_INTERFACES; do
    IFS="=" read -r IFACE IP <<< "$PAIR"
    ip addr add $IP/16 dev $IFACE
    ip link set $IFACE up
done

# ==========================================
# 3. OVS CONFIGURATION
# ==========================================
/usr/share/openvswitch/scripts/ovs-ctl --system-id=random start
ovs-vsctl add-br s1

# Add data ports to the bridge
ovs-vsctl add-port s1 eth1
ovs-vsctl add-port s1 eth2
ovs-vsctl add-port s1 eth3
ovs-vsctl add-port s1 eth4

# Enforce OpenFlow 1.3
ovs-vsctl set bridge s1 protocols=[OpenFlow13]

# ==========================================
# 4. THE "DARK NETWORK" SECRET
# ==========================================
# 'secure' mode means: if I have no rules, I drop everything.
ovs-vsctl set-fail-mode s1 secure

# Connect to the Ryu Controller
ovs-vsctl set-controller s1 tcp:$CONTROLLER_ADDRESS

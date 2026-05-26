for PAIR in $DEVICE_INTERFACES; do
    IFS="=" read -r IFACE IP <<< "$PAIR"
    
    ip addr add $IP/16 dev $IFACE
    ip link set $IFACE up
done

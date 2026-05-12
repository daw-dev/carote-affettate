for PAIR in $DEVICE_INTERFACES; do
    IFS="=" read -r IFACE IP <<< "$PAIR"
    
    ip addr add $IP dev $IFACE
    ip link set $IFACE up
done

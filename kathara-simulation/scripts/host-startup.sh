ip addr add $DEVICE_ADDRESS/16 dev eth0
ip link set eth0 up

ip route add default via $DEFAULT_GATEWAY dev eth0

echo "nameserver $CONTROLLER_ADDRESS" > /etc/resolv.conf

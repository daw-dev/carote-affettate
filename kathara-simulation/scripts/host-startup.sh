ip addr add $DEVICE_ADDRESS/16 dev eth0
ip link set eth0 up

# TODO: aggiungere come default gateway lo switch connesso
#
# log iperf in un file fuori

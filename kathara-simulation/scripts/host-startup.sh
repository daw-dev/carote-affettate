ip addr add $DEVICE_ADDRESS/16 dev eth0
ip link set eth0 up

ip route add default via $DEFAULT_GATEWAY dev eth0

echo "nameserver $CONTROLLER_ADDRESS" > /etc/resolv.conf

echo "source /host/slice.sh" >> /root/.bashrc
echo 'alias run-iperf="python3 /host/run-iperf.py"' >> /root/.bashrc

# Starting listener for incoming iperf3 tests
python3 /host/listening-agent.py

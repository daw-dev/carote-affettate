FROM kathara/pox

RUN apt-get update
RUN apt-get install -y dnsmasq

# install dependencies
RUN python3.9 -m pip install "setuptools<59"
RUN python3.9 -m pip install ryu
RUN python3.9 -m pip install "eventlet==0.30.2"
RUN python3.9 -m pip install "networkx"

# cleanup
RUN apt clean && rm -rf /tmp/* /var/lib/apt/lists/* /var/tmp/*

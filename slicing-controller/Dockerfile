FROM kathara/pox

# install dependencies
RUN python3.9 -m pip install "setuptools<59"
RUN python3.9 -m pip install ryu
RUN python3.9 -m pip install "eventlet==0.30.2"

# cleanup
RUN apt clean && rm -rf /tmp/* /var/lib/apt/lists/* /var/tmp/*

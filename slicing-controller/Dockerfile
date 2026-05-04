FROM kathara/pox

ARG DEBIAN_FRONTEND="noninteractive"
RUN pip3.9 --no-input install ryu
RUN pip3.9 --no-input install eventlet==0.30.2

RUN apt clean && rm -rf /tmp/* /var/lib/apt/lists/* /var/tmp/*

FROM ubuntu:latest

# Install general tools and networking utilities
RUN apt update && apt install -y \
    tshark jq iputils-ping dnsutils net-tools iperf tcpdump \
    netcat-traditional curl iproute2 ethtool iptables nftables

# Enable IP forwarding
RUN echo 'net.ipv4.ip_forward=0' >> /etc/sysctl.conf && sysctl -p

# Install Python 3 and pip
RUN apt update && apt install -y python3 python3-pip build-essential cmake libpcap-dev vim python3-pycryptodome python3-scapy libffi-dev libssl-dev net-tools iproute2 tcpdump && apt clean

# Optional: set working directory
WORKDIR /code/sec

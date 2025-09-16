#!/bin/bash
# Jay M 2025
#
# Setup on a fresh RPi:
# Add the following to /etc/hosts/interfaces:
#
# auto can0
# iface can0 can static
#       bitrate [pick a number, 125000 works]
#
# Run the commands to update network configs:
# sudo ip addr flush can0 && sudo systemctl restart networking
#
# CAN-related commands should work now :3

if [ $# -eq 0 ]; then
    echo "No args provided"
    exit 1
fi

delay=0.1

if [ $# -gt 2 ]; then
    delay=$2
fi

for ((i=0;i<$1;i++)); do
    cansend can0 123#DEADBEEF
    sleep $delay
done

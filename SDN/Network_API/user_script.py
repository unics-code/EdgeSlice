# Instructions:
# Run the commands below to install all of the necessary modules:
        # sudo pip3 install --upgrade pip
        # sudo -H pip3 install --upgrade pip
        # sudo apt-get install python3-pip python3-dev
        # sudo pip3 install matplotlib
        # sudo pip3 install psutil
        # sudo apt-get install python3-pandas
        # sudo pip3 install numpy

# Purpose: This code will send data to the server to graph the Tx and Rx rates

import time
import os
import sys
import ctypes
import threading
import socket
import connector
import csv
import pickle
import subprocess
import random, time
from itertools import count
import pandas as pandas
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

#socket connection parameters
buffer_size = 256
server_ip_add = '155.0.0.1'
server_port = 10555
user_socket_con = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
user_socket_con.connect((server_ip_add, server_port))


def get_bytes(t, iface='eno1'):
    with open('/sys/class/net/' + iface + '/statistics/' + t + '_bytes', 'r') as f:
        data = f.read()
        return float(data)

while True:
    time.sleep(1)
    temp_tx=str(get_bytes('tx'))
    temp_rx=str(get_bytes('rx'))
    message = temp_tx+","+temp_rx+","
    print ("Message Tx = "+message)
    user_socket_con.sendall(message.encode())




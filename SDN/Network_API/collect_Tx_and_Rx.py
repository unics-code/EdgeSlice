# sudo pip3 install --upgrade pip
# sudo -H pip3 install --upgrade pip
# sudo apt-get install python3-pip python3-dev
# sudo pip3 install matplotlib
# sudo pip3 install psutil
# sudo apt-get install python3-pandas
# sudo pip3 install numpy

import time, os, sys, ctypes, threading, socket, connector, csv, pickle, subprocess, random, time
from itertools import count
import pandas as pandas
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


time_duration=300 #<== TODO:Change this value
org1_users = []
org2_users = []
org1_start_ip_add=35
org2_start_ip_add=65

# Creatig the list of potential users that will transmit data
i=0
while i < 20:#int(sys.argv[1]):
  org1_users.append('155.0.0.'+str(org1_start_ip_add+i))
  i=i+1
i=0
while i < 20:#int(sys.argv[2]):
  org2_users.append('155.0.0.'+str(org2_start_ip_add+i))
  i=i+1

#socket connection parameters
HOST='155.0.0.1'
PORT=10555
BUFFER_SIZE = 256

server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(len(org1_users)+len(org2_users)) # 10 indicates we can connect up to 10 users




#creates an queue incase a Node sends B2B (back to back) transactions
queue_param=['']
x_vals =  [x for x in range(time_duration)]
Tx_vals_org1 =[[0 for x in range(len(org1_users))] for y in range(time_duration)]
Rx_vals_org1 =[[0 for x in range(len(org1_users))] for y in range(time_duration)]
Tx_vals_org2 =[[0 for x in range(len(org1_users))] for y in range(time_duration)]
Rx_vals_org2 =[[0 for x in range(len(org1_users))] for y in range(time_duration)]

#indicates whether to output all debug commands
debug='ON'


    

def process_parameters(*args):
  # args[0]= 155.0.0.35 #users ip address
  # args[1]= socket_thread #users stream for data transmission
  global Tx_vals_org1, Rx_vals_org1, Tx_vals_org2, Rx_vals_org2
  print ('collect_parameters Thread -----------------started 4 '+str(args[0]))
  
  while (True):
    param1 = str(args[1].recv(BUFFER_SIZE))
    param =[]
    if len(param1)==3 :
      print ('collect_parameters Thread -----------------ended 4 '+str(args[0]))
      print ("================================= PROBLEM: Client was disconnected =================================")
      break
    else:

      print ("DEBUGGING INFO#1: "+param1) #<== format is TX_byte_count, RX_byte_count

      # This will determine which device is sending the data and store the data in the correct 
      # slot of the Tx and Rx arrays.
      temp_ip_add = args[0][args[0].find("155.0.0.")+8:]
      while param1.find(",")!=(-1):
        if debug =="ON":
          print ("Recieved PARAM1: "+str(param1))
        
        # Determine the TX_byte_count
        eod=param1.find(",")
        temp_tx = param1[2:eod]

        # Determine the RX_byte_count
        param1 = param1[eod+1:]
        eod=param1.find(",")
        temp_rx = param1[:eod]
        param1=""
        
        print ("\n temp_ip_add = 155.0.0."+str(temp_ip_add))
        print ("\n temp_tx = "+str(temp_tx))
        print ("\n temp_rx = "+str(temp_rx))

        if int(temp_ip_add)<org2_start_ip_add and int(temp_ip_add)>org1_start_ip_add:
          lock.acquire()
          # store TX_byte_count
          Tx_vals_org1 = Tx_vals_org1[:time_duration-1]
          Tx_vals_org1[int(temp_ip_add)-org1_start_ip_add].append(temp_tx)
          
          # store RX_byte_count
          Rx_vals_org1 = Tx_vals_org1[:time_duration-1]
          Rx_vals_org1[int(temp_ip_add)-org1_start_ip_add].append(temp_rx)
          lock.release()
        elif int(temp_ip_add)>=org2_start_ip_add and int(temp_ip_add)<=(org2_start_ip_add+len(org1_users):
          lock.acquire()
          # store TX_byte_count
          Tx_vals_org2 = Tx_vals_org2[:time_duration-1]
          Tx_vals_org2[int(temp_ip_add)-org2_start_ip_add].append(temp_tx)
          
          # store RX_byte_count
          Rx_vals_org2 = Tx_vals_org2[:time_duration-1]
          Rx_vals_org2[int(temp_ip_add)-org2_start_ip_add].append(temp_rx)
          lock.release()
        
  print ('collect_parameters Thread -----------------finished')








# Establish connections with users
user_threads = []
lock = threading.RLock()
while True:
  print ('\nController Socket is now listening for a user to connect')
  controller, ctl_addr = server.accept()
  print ("\nctl_addr = "+str(ctl_addr))
  user_threads.append(threading.Thread(target=process_parameters(str(ctl_addr[0]), controller)))
  user_threads[len(user_threads)-1].daemon = True
  user_threads[len(user_threads)-1].start()
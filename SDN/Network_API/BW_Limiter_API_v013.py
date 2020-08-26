import requests
import time
import os
import flow_v005 as flow
#import flow_v004 as flow # for debuging flow_v003
import numpy as np
import sys
import ctypes
import threading
import socket
import connector
import csv


#Instructions:
#STEP 1: Run this cli command in a seperate terminal 'sudo /home/lab/Downloads/distribution-karaf-0.5.3-Boron-SR3/bin/karaf start'
#STEP 2: Clear all default flow entries on the ruckus switches
#STEP 3:Run this file using sudo (eg. sudo python BW_Limiter_api_v001.py)

#contains an array of the ruckus switch openflow id #'s'
switch = [106225813884652,106225813882690,106225813884292,106225813882258,106225813899736]

b1_u=[
'172.16.0.2',
'172.16.0.4',
'10.0.0.101'
]

b2_u=[
'172.16.0.6',
'172.16.0.8',
'10.0.0.102'
]

#number of users
nou=len(b2_u)+len(b1_u)

#default bandwidth in Megabytes for users
d_bw=40

#number of topologies
num_t=2

#meter list
max_num_meters=int(1024/nou)
m_l = np.zeros((num_t,nou,len(switch), max_num_meters)) #1024 is the maximum # of  meter entries on a layer 2 switch
#             switch # by meter # for each user
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X

#flow list
f_l = np.empty([num_t,nou,len(switch),int(512/nou),7], dtype=object) #512 is the maximum # of  flow entries on a layer 2 switch
#             switch # by flow # for each user
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X

#clear all preliminary/default flows and meters on each switch
for n in range(0,len(switch)):
  flow.clear(switch[n])

#add a meter on each switch for each user in each Topology
for e in range(0,num_t):
  for u in range(0,nou): #add a meter per user starting with base station 1's users
    for s in range(0,len(switch)): #goes through all of the switches
      m_l[e][u][s][0] = flow.add_meter(switch[s],d_bw)

#print(m_l) #debuging code

#create network topolgy
f_num = np.zeros((2,len(switch))) #keeps track of the # of flows in each topology

print("\n\nSDN Topology #1-----------------------------\n\n")
top_num=0
f_l[top_num]=flow.create_topology(b1_u,b2_u,f_l[top_num],switch,m_l[top_num])
#print("\n\nSDN Topology #2-----------------------------\n\n")
#top_num=1
#f_l[top_num]=flow.create_topology(b1_u,b2_u,f_l[top_num],switch,m_l[top_num])

#infinite loop to change the BW as the user desires
print('Lets change the users bandwidth using their ip address (eg. 192.168.1.2 20):\n')
print('192.168.1.2 is the user\n')
print('20 is a BW limit of 20 MegaBytes for user 0\n\n')

print('Potential Users:\n')
i=0
while(i<len(b1_u)):
  print(b1_u[i])
  i=i+1
i=0
while(i<len(b2_u)):
  print(b2_u[i])
  i=i+1
param=[0]*2

#socket connection
HOST='155.0.0.8'
PORT=10000
BUFFER_SIZE = 256
QUATO = np.zeros(2*4, dtype=np.double) #this is the data being sent from the AI to modify the BW for each user

ctl = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
ctl.bind((HOST, PORT))
ctl.listen(10) # 10 indicates we can connect up t0 10 users
print('Controller Socket now listening')
test_bw=320
param = ['2',str(test_bw),'4',str(test_bw),'6',str(test_bw),'8',str(test_bw),'10.0.0.101','200','10.0.0.102','200'] #debuging code


#BW limit is .008 to 5000 MegaBytes
#infinite loop to change the BW as the user desires
top_num=0

flow.output_flow(b1_u,b2_u,nou,switch,f_l,top_num)
 
while(True):
  #time.sleep(10) #debuging code
  #test_bw=test_bw-5 # debuging code
  param = connector.connect_controller(ctl,param)
  #param = ['2',str(test_bw),'4',str(test_bw),'6',str(test_bw),'8',str(test_bw),'10.0.0.101',str(test_bw),'10.0.0.102',str(test_bw)] #debuging code
  if(top_num==0):
    print("\n\nSDN Topology #2 Creation-----------------------------\n\n")
    top_num=1
    for u in range(0,nou): #add a meter per user starting with base station 1's users
      for s in range(0,len(switch)): #goes through all of the switches
        h_count=u*2
        #determines the location of the ip address based on both base stations arrays for each user
        i=0
        check=-1#check is the ip address input argument in terms of the m_l index
        while((i<len(b1_u)) and (check==-1)):
          if (b1_u[i] == str(param[h_count])):
            check=i
            i=i+1
          i=0
          if (check==-1):
            while((i<len(b2_u)) and (check==-1)):
              if (b2_u[i] == str(param[h_count])):
                check=len(b1_u)+i
              i=i+1
        if(check<>-1):
					flow.modify_meter(switch[s],int(m_l[top_num][u][s][0]),param[h_count+1])
					flow.modify_f_l(f_l[top_num],int(m_l[top_num][u][s][0]))
		#TODO need to update the create_topology to reflect 'flow.create_topology(b1_u,b2_u,f_l[top_num],switch,m_l[top_num])'
    f_l[top_num]=flow.create_topology(b1_u,b2_u,f_l[top_num],switch,m_l[top_num],top_num,f_num[top_num])
    top_num=0
  else:
    print("\n\nSDN Topology #1 Creation-----------------------------\n\n")
    top_num=0
    for u in range(0,nou): #add a meter per user starting with base station 1's users
      for s in range(0,len(switch)): #goes through all of the switches
        h_count=u*2
        #determines the location of the ip address based on both base stations arrays for each user
        i=0
        check=-1
        while((i<len(b1_u)) and (check==-1)):
          if (b1_u[i] == str(param[h_count])):
            check=i
            i=i+1
          i=0
          if (check==-1):
            while((i<len(b2_u)) and (check==-1)):
              if (b2_u[i] == str(param[h_count])):
                check=len(b1_u)+i
              i=i+1
        if(check<>-1):
          flow.modify_meter(switch[s],int(m_l[top_num][u][s][0]),param[h_count+1])
          flow.modify_f_l(f_l[top_num],int(m_l[top_num][u][s][0]))
    f_l[top_num]=flow.create_topology(b1_u,b2_u,f_l[top_num],switch,m_l[top_num],top_num,f_num[top_num])
    top_num=1
  
  h=0
  h_count=0
  #determines the location of the ip address based on both base stations arrays for each user
  #then modifies the meters while the backup sdn network is being utilized
  while(h_count<len(param)):
    i=0
    check=-1
    #print('Looking for '+str('155.0.0.'+param[h_count])) #debuging code
    while((i<len(b1_u)) and (check==-1)):
      if (b1_u[i] == str(param[h_count])):
        check=i
      i=i+1
    i=0
    if (check==-1):
      while((i<len(b2_u)) and (check==-1)):
        if (b2_u[i] == str(param[h_count])):
          check=len(b1_u)+i
        i=i+1
    h_count=h_count+2

    if (check==-1):
      print('BAD ip: '+str(param[h_count]))
      print('ERROR:The users ip address is invalid!\n')
    else:
      s=0
      while((s<len(switch))): #goes through all of the switches and changes the meter bandwidths
        #print('ccccc') #debuging code		
        ender=0 #stops the next while loop from running forever
        temp_counter=0
        while((ender==0) and (temp_counter<max_num_meters)): #sanity check prevents this loop from going forever
          #print('ababab') #debuging code
          #this section is kind of hard code since I know their is only 1 meter per user
          if((temp_counter==0) and (int(m_l[top_num][check][s][temp_counter])<>0)):
            #print('aaaaa') #debuging code
            flow.modify_meter(switch[s],int(m_l[top_num][check][s][temp_counter]),param[1])
            flow.modify_f_l(f_l[top_num],int(m_l[top_num][u][s][0]))
            ender=ender+1
          else:
            print('ERROR: HERE#2') #debuging code	
          temp_counter=temp_counter+1
        s=s+1
    #test_bw=test_bw-2
  if(top_num==0):
    top_num=1
  else:
    top_num=0  
  
  #Note:
  #param[0] = 192.168.1.2 #user ip address
  #param[1] = 20 #BW in MegaBytes

  #print('you entered: '+str(param[0])+' '+str(param[1])) #debuging code


  print(param)

import requests
import time
import os
import flow_v003 as flow
import numpy as np
import sys


#Instructions:
#STEP 1: Run this cli command in a seperate terminal 'sudo /home/lab/Downloads/distribution-karaf-0.5.3-Boron-SR3/bin/karaf start'
#STEP 2: Clear all default flow entries on the ruckus switches
#STEP 3:Run this file using sudo (eg. sudo python BW_Limiter_api_v001.py)

#contains an array of the ruckus switch openflow id #'s'
switch = [106225813884652,106225813882690,106225813884292,106225813882258,106225813899736]

b1_u=[
'155.0.0.23',
]

b2_u=[
'155.0.0.29',
'155.0.0.22'
]

#number of users
nou=len(b2_u)+len(b1_u)

#default bandwidth in Megabytes for users
d_bw=20

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
f_l = np.zeros((num_t,nou,len(switch), int(512/nou))) #512 is the maximum # of  flow entries on a layer 2 switch
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

#print(m_l) #debugging code

#create network topolgy
f_num = np.zeros((2,len(switch)) #keeps track of the # of flows in each topology

f_l[0]=flow.create_topology(b1_u,b2_u,f_l[0],switch,m_l[0],0)

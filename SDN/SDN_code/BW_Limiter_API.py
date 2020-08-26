import requests
import time
import os
import flow_v005 as flow
import numpy as np
import sys
import ctypes
import threading
import socket
import connector
import csv

#v13
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

nou=len(b2_u)+len(b1_u)

d_bw=40

num_t=2

max_num_meters=int(1024/nou)
m_l = np.zeros((num_t,nou,len(switch), max_num_meters)) 

f_l = np.empty([num_t,nou,len(switch),int(512/nou),7], dtype=object) 

for n in range(0,len(switch)):
  flow.clear(switch[n])

for e in range(0,num_t):
  for u in range(0,nou): 
    for s in range(0,len(switch)): 
      m_l[e][u][s][0] = flow.add_meter(switch[s],d_bw)

f_num = np.zeros((2,len(switch)))

top_num=0
f_l[top_num]=flow.create_topology(b1_u,b2_u,f_l[top_num],switch,m_l[top_num])

i=0
while(i<len(b1_u)):
  print(b1_u[i])
  i=i+1
i=0
while(i<len(b2_u)):
  print(b2_u[i])
  i=i+1
param=[0]*2

HOST='155.0.0.8'
PORT=10000
BUFFER_SIZE = 256
QUATO = np.zeros(2*4, dtype=np.double)

ctl = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
ctl.bind((HOST, PORT))
ctl.listen(10)

test_bw=320
param = ['2',str(test_bw),'4',str(test_bw),'6',str(test_bw),'8',str(test_bw),'10.0.0.101','200','10.0.0.102','200'] #debuging code


top_num=0

flow.output_flow(b1_u,b2_u,nou,switch,f_l,top_num)
 
while(True):

  param = connector.connect_controller(ctl,param)
  if(top_num==0):
    print("\n\nSDN Topology #2 Creation-----------------------------\n\n")
    top_num=1
    for u in range(0,nou): 
      for s in range(0,len(switch)): 
        h_count=u*2
       
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
    top_num=0
  else:
    print("\n\nSDN Topology #1 Creation-----------------------------\n\n")
    top_num=0
    for u in range(0,nou): 
      for s in range(0,len(switch)):
        h_count=u*2
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
      while((s<len(switch))):
        temp_counter=0
        while((ender==0) and (temp_counter<max_num_meters)): 
          if((temp_counter==0) and (int(m_l[top_num][check][s][temp_counter])<>0)):
            #print('aaaaa') #debuging code
            flow.modify_meter(switch[s],int(m_l[top_num][check][s][temp_counter]),param[1])
            flow.modify_f_l(f_l[top_num],int(m_l[top_num][u][s][0]))
            ender=ender+1
          else:
          temp_counter=temp_counter+1
        s=s+1
    #test_bw=test_bw-2
  if(top_num==0):
    top_num=1
  else:
    top_num=0  
  


  print(param)

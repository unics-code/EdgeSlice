import requests
import os
import flow_v011_SDNB as flow #to get two base stations to work
import numpy as np
import sys
import ctypes
import threading, time, socket, subprocess
import connector
import csv
import pickle

#l=0 #debuging code
#while (l<len(sys.argv)):
#  print(sys.argv[l]) #debuging code
#  l=l+1 #debuging code

#Purpose: To get two base stations to work

#Instructions:
#STEP 1: Run this cli command in a seperate terminal 'sudo /home/lab/Downloads/distribution-karaf-0.5.3-Boron-SR3/bin/karaf start'
#STEP 2: Clear all default flow entries on each ruckus switch
#STEP 3:Run this file using sudo (eg. sudo python BW_Limiter_api_v001.py)

#contains an array of the ruckus switch openflow id #'s'
with open('objs.pkl', 'rb') as f:
  m_l, f_l, top_num, error, delta, param, b1_u, b2_u, switch = pickle.load(f)

# testing_var=0
# while(testing_var==0):
start_time=time.time()
#param = ['2',str(test_bw+1),'4',str(test_bw+3),'6',str(test_bw+2),'8',str(test_bw+5),'10.0.0.101','199','10.0.0.102','200'] #debuging code

b1_u_mod=[]
b2_u_mod=[]
i=0
while i<len(b1_u):
  b1_u_mod.append('none')
  i=i+1
i=0
while i<len(b2_u):
  b2_u_mod.append('none')
  i=i+1


# #creates backup SDN network
# if(top_num==0):
#   top_num=1
#   # contains the meter numbers that need to be modify

#   for p in range(0,len(param)/2): #add a meter per user starting with base station 1's users #goes through all of the param
#     h_count=p*2
#     #determines the location of the ip address based on both base stations arrays for each user
#     ii=0
#     check=-1#check will be  the ip address input argument in terms of the m_l index
#     while((ii<len(b1_u)) and (check==-1)):
#       if b1_u[ii] == str(param[h_count]):
#         check=ii
#         b1_u_mod[ii]=b1_u[ii]          
#       ii=ii+1
#     i=0
#     if (check==-1):
#       while((i<len(b2_u)) and (check==-1)):
#         if b2_u[i] == str(param[h_count]):
#           check=len(b1_u)+i
#           b2_u_mod[i]=b2_u[i] 
#         i=i+1
#     if(check<>-1):
#       for s in range(0,len(switch)): #goes through all of the switches
#         flow.modify_meter(switch[s],int(m_l[top_num][check][s][0]),param[h_count+1])#deletes the meter and inadvertently all the flows connected to it and then recreates the meter using the correct bandwidth using the backup network
#         flow.modify_f_l(f_l[top_num],int(m_l[top_num][check][s][0]))#delete all flows within my database"
#         # catch flow errors
#         i=0
#         e_temp = flow.get_E()
#         while i<len(e_temp):
#           error.append(e_temp[i])
#           i=i+1
#         flow.clear_E()

#     else:
#       print('BAD ip: '+str(param[h_count]))
#       print('ERROR:The users ip address is invalid!\n')
#   #time.sleep(10)
#   f_l[top_num]=flow.create_topology(b1_u_mod,b2_u_mod,f_l[top_num],switch,m_l[top_num])#creates tbe topology again and readds all of the flows
#   # catch flow errors
#   i=0
#   e_temp = flow.get_E()
#   while i<len(e_temp):
#     error.append(e_temp[i])
#     i=i+1
#   flow.clear_E()

#   print("\n\n-----------------------------SDN Topology #1 Created-----------------------------\n\n")
#   top_num=0
# else:
#   top_num=0

def modify_METER_thread(*args):
  # args[0] = switch[s]
  # args[1] = int(m_l[u_index][top_num[u_index]][s][0])
  # args[2] = param[h_count+1]
  flow.modify_meter(args[0],args[1],args[2])

# def modify_FLOWs_in_the_switch_thread(*args):
#   # args[0] = f_l
#   # args[1] = int(m_l[u_index][top_num[u_index]][s][0])
#   # args[2] = int(top_num[u_index])
#   flow.modify_f_l(args[0],args[1],args[2])

mod_metersT=time.time()
thread2=[]
for p in range(0,len(param)/2): #add a meter per user starting with base station 1's users
  
  h_count=p*2
  #determines the location of the ip address based on both base stations arrays for each user
  ii=0
  check=-1
  while((ii<len(b1_u)) and (check==-1)):
    if b1_u[ii] == str(param[h_count]):
      check=ii
      ii=ii-1
      b1_u_mod[ii]=b1_u[ii]
    ii=ii+1

  i=0
  if (check==-1):
    while((i<len(b2_u)) and (check==-1)):
      if b2_u[i] == str(param[h_count]):
        check=len(b1_u)+i
        i=i-1
        b2_u_mod[i]=b2_u[i] 
      i=i+1

  if(check<>-1):
    u_index=ii+i
    print "\n\nU_INDEX VALUE = "+str(u_index)
    print "BEFORE TOP_NUM="+str(top_num)
    #change the top_num for this user
    if top_num[u_index] == 1:
      top_num[u_index]=0
    else:
      top_num[u_index]=1
    print "AFTER TOP_NUM="+str(top_num)
    swl=[] # contains all of the switches with a meter for this user
    s=0
    while s<len(switch):
      if m_l[u_index][top_num[u_index]][s][0] >0:
        swl.append(s)
      s=s+1
    
    thread_index=len(thread2)
    for s in swl: #goes through all of the switches with meters for this user
      # flow.modify_meter(switch[s],int(m_l[top_num][check][s][0]),param[h_count+1])#deletes the meter and inadvertently all the flows connected to it and then recreates the meter using the correct bandwidth using the backup network
      # flow.modify_f_l(f_l[top_num],int(m_l[top_num][check][s][0]))#delete all flows within my database"
      
      # Deletes the meter and inadvertently all the flows connected to it and then recreates the meter using the correct bandwidth using the backup network
      thread2.append(threading.Thread(target=modify_METER_thread(switch[s],int(m_l[u_index][top_num[u_index]][s][0]),param[h_count+1])))

      # delete all flows within my database
      # thread2.append(threading.Thread(target=modify_FLOWs_in_the_switch_thread(f_l,int(m_l[u_index][top_num[u_index]][s][0]),int(top_num[u_index]))))
      # modify_FLOWs_in_the_switch_thread(f_l,int(m_l[u_index][top_num[u_index]][s][0]),int(top_num[u_index]))

      f_l[u_index][top_num] = flow.modify_f_l(f_l[u_index][top_num],int(m_l[u_index][top_num][check][s][0]))
    i=thread_index
    while i<len(thread2):
      # kills all threads if this python code is killed
      thread2[i].daemon = True
      # Starts the thread
      thread2[i].start()
      i=i+1

      # # catch flow errors
      # i=0
      # e_temp = flow.get_E()
      # while i<len(e_temp):
      #   error.append(e_temp[i])
      #   i=i+1
      # flow.clear_E()
    # starts the first 2 threads
    


    # modify_meter_TT=time.time()

    # print "\nf\nf\nf\nf\nf\nf\nf\nf\nFINISHED EM"
  else:
    print('BAD ip: '+str(param[h_count]))
    print('ERROR:The users ip address is invalid!\n')
    break

i=thread_index
while i<len(thread2):
  while thread2[i].is_alive():
    i=i
  print "modify meter......"+str(i)+"..."+str(time.time()-mod_metersT)
  i=i+1
print "ALL MODIFY METERS TOTAL TIME = "+str(time.time()-mod_metersT)

# print '\n\n '+str(b1_u_mod)
# print '\n\n '+str(b2_u_mod)
#This is used to see the current flow connections on all switches. #TODO update this function to add group flows as well
flow.output_flow(b1_u,b2_u,switch,f_l,top_num)
# time.sleep(10)
f_l=flow.create_topology(b1_u_mod,b2_u_mod,f_l,switch,m_l,top_num)

#This is used to see the current flow connections on all switches. #TODO update this function to add group flows as well
flow.output_flow(b1_u,b2_u,switch,f_l,top_num)

i=0
e_temp = flow.get_E()
while i<len(e_temp):
  error.append(e_temp[i])
  i=i+1
flow.clear_E()

print("\n\n-----------------------------SDN Topology "+str(top_num)+" Created-----------------------------\n\n")


delta_time=time.time()-start_time
delta.append(delta_time)
print(param)
print('end-time: '+str(time.ctime()))
print('delta-time: '+str(delta_time))
#time.sleep(20) #debuging code
#Note:
#param[0] = 192.168.1.2 #user ip address
#param[1] = 20 #BW in MegaBytes
#print('you entered: '+str(param[0])+' '+str(param[1])) #debuging code
with open('objs.pkl', 'wb') as f:
  pickle.dump([m_l, f_l, top_num, error, delta, param, b1_u, b2_u, switch], f)
# testing_var=1

print('SDN Network Setup Complete!\n\n')

import requests
import time
import os
import flow_v013 as flow #to get two base stations to work
import numpy as np
import sys
import ctypes
import threading
import socket
import connector
import csv
import pickle
import subprocess

#Purpose: To get two base stations to work quickly

#Instructions:
#STEP 1: Run this cli command in a seperate terminal 'sudo /home/lab/Downloads/distribution-karaf-0.5.3-Boron-SR3/bin/karaf start'
#STEP 2: Run this file using sudo (eg. sudo python init_network_v4.py)


switch = [106225813884292] #THIS IS QIANGS SWITCH

b1_u=[
'172.16.0.2',
'172.16.0.4',
'172.16.0.6',
'172.16.0.8',
'155.0.0.34',
'155.0.0.36'
]

# b2_u=[
# '172.16.0.6',
# '172.16.0.8',
# '155.0.0.35'
# ]

# b1_u=[]
b2_u=[]
i=0


#number of users # we add 1 for the arp 
nou=len(b2_u)+len(b1_u)+1

#default bandwidth in MegaBytes for users
d_bw=10

#number of topologies
num_t=2

# stores the errors found throughout each execution
error = []

#meter list
# max_num_meters=int(1024/nou)
max_num_meters=int(1024/(2*nou)) #EM change
# m_l = np.zeros((num_t,nou,len(switch), max_num_meters)) #1024 is the maximum # of  meter entries on a layer 2 switch
m_l = np.zeros((nou,num_t,len(switch), max_num_meters)) #EM change #1024 is the maximum # of  meter entries on a layer 2 switch
#             switch # by meter # for each user
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X

#flow list
# f_l = np.empty([num_t,nou,len(switch),int(512/nou),7], dtype=object) #512 is the maximum # of  flow entries on a layer 2 switch
f_l = np.empty([nou,num_t,len(switch),int(512/(2*nou)),7], dtype=object) #EM change #512 is the maximum # of  flow entries on a layer 2 switch
#             switch # by flow # for each user
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X
#                    X  X  X  X  X  X

#clear all preliminary/default flows, meters, and groups on each switch
clear_t=time.time()
thread_clear=[]
for n in range(0,len(switch)):
  # flow.clear(switch[n])
  thread_clear.append(threading.Thread(target=flow.clear(switch[n])))
#starts all threads
i=0
while i<len(thread_clear):
    #kills are threads if this python script is killed
    thread_clear[i].daemon = True
    thread_clear[i].start()
    i=i+1
i=0
while i<len(thread_clear):
  while thread_clear[i].is_alive():
    i=i
    # thread_clear[i].join()
  i=i+1

print "+++++++++++++++Clear Switches Total Time= "+str(time.time()-clear_t)

# store the errors in create the initial 
# # i=0
# e_temp = flow.get_E()
# while i<len(e_temp):
#   error.append(e_temp[i])
#   i=i+1
# flow.clear_E()

# The below code will kill this script if it is not able to clear all switches without errors. 
# Being able to clear all the switches will indicate that it can also communicate with opendaylight.
if len(error)>0:
  print error
  exit()

#add a meter on each switch for each user in each Topology
# for e in range(0,num_t):
#   for u in range(0,nou): #add a meter per user starting with base station 1's users
#     for s in range(0,len(switch)): #goes through all of the switches
#       m_l[e][u][s][0] = flow.add_meter(switch[s],d_bw)

#EM change # add a meter on each switch for each user in each Topology
for e in range(0,len(b1_u)+len(b2_u)+1):
  for u in range(0,num_t): #add a meter per user starting with base station 1's users
    for s in range(0,len(switch)): #goes through all of the switches #TODO change this to the switches being used in the topology
      #TODO go to the flow script and do the same thing
      m_l[e][u][s][0] = flow.add_meter(switch[s],d_bw)





# store the errors in create the initial network
i=0
e_temp = flow.get_E()
while i<len(e_temp):
  error.append(e_temp[i])
  i=i+1
flow.clear_E()

#print(m_l) #debuging code

# top_num=0
# f_l[top_num] = flow.create_topology(b1_u,b2_u,f_l[top_num],switch,m_l[top_num])

top_num=[]
i=0
while i<nou:
  top_num.append(0)
  i=i+1
f_l = flow.create_topology(b1_u,b2_u,f_l,switch,m_l,top_num)

# store the errors in create the initial network
i=0
e_temp = flow.get_E()
while i<len(e_temp):
  error.append(e_temp[i])
  i=i+1
flow.clear_E()
print("\n\n-----------------------------SDN Topology "+str(top_num)+" Created-----------------------------\n\n")

#This is used to see the current flow connections on all switches. #TODO update this function to add group flows as well
flow.output_flow(b1_u,b2_u,switch,f_l,top_num)

#infinite loop to change the BW as the user desires
#print('Lets change the users bandwidth using their ip address (eg. 192.168.1.2 20):\n')
#print('192.168.1.2 is the user\n')
#print('20 is a BW limit of 20 MegaBytes for user 0\n\n')

print('Potential Users:\n')
i=0
while(i<len(b1_u)):
  print(b1_u[i])
  i=i+1
i=0
while(i<len(b2_u)):
  print(b2_u[i])
  i=i+1

param = []
# test_bw=.05
#param = ['2',str(test_bw+1),'4',str(test_bw+3),'6',str(test_bw+2),'8',str(test_bw+5),'10.0.0.101','199','10.0.0.102','200'] #debuging code
#R_ses = requests.Session() #TODO get this working to make requests faster
# R_ses=''


delta=[]

#writes the data in a file for use	
with open('objs.pkl', 'wb') as f:
    pickle.dump([m_l, f_l, top_num, error, delta, param, b1_u, b2_u, switch], f)


#socket connection parameters
HOST='192.168.1.147'
PORT=10500
BUFFER_SIZE = 256
#QUATO = np.zeros(2*(nou-2), dtype=np.double) #this is the data being sent from the AI to modify the BW for each user
QUATO= np.zeros(2,dtype=np.double)

server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(10) # 10 indicates we can connect up to 10 users
controller, ctl_addr = server.accept()




#creates an queue incase a Node sends B2B (back to back) transactions
queue_param=['']

#this is used when the same variable may be written at the same time by different threads
lock=threading.RLock()

#indicates whether to output all debug commands
debug='ON'

def collect_parameters():
  global controller, queue_param
  print 'collect_parameters Thread -----------------started'
  
  while (True):
    print 'Controller Socket is now listening'
    param1 = str(controller.recv(4096))
    param =[]
    if len(param1)==0 :
      print "================================= PROBLEM: Client was disconnected ================================="
      controller, ctl_addr = server.accept()
    else:
      if param1.find("155.0.") != (-1) or param1.find("172.16.") != (-1): #change for EM SDN-B
      # if param1.find("172.16.") != (-1): #change for Qiang Network Slicing
        print "DEBUGGING INFO#1: "+param1
        i=0
        while param1.find(",")!=(-1):
          if debug =="ON":
            print "Before PARAM1: "+str(param1)
          eod=param1.find(",")
          
          if i%2 == 0:
            param.append(param1[0:eod])
          else:
            param.append(float(param1[0:eod]))

          param1 = param1[eod+1:]
          i=i+1
          if debug =="ON":
            print "After PARAM1: "+str(param1)
        
        if len(param1)>0:
          param.append(float(param1))
          param1 = ""

        try:	
          print 'Recieved: '+str(param)
          lock.acquire()
          queue_param.append(param)
          lock.release()
          print 'Queued parameters.'
        except:
          print "Check how many parameters you are sending! (Only "+str(nou*2)+" is allowed)"

  print 'collect_parameters Thread -----------------finished'

def process_parameters(*args):
  #TODO is this function still being used???
  global queue_param, nou
  print 'process_parameters -----------------started'
  # print 'DEBUGGING INFO: '+str(args)
  param1 = str(args).split(",")
  param = []
  # print "data recieved: "+param1
  #parse the data sent from the client.# must be in format "155.0.0.36,10,155.0.0.36,20" with all the Nodes bandwidth allocated
  i=0
  eod=0#end of data	
  while i<(nou*2):
    if debug=='ON':
      print "before: "+param1[i]+"\n"
    if i%2 ==0:
      param[i]=str(param1[i])
    else:
      param[i]=float(param1[i])
    if debug=='ON':
      print "after: "+param1[i]+"\n"
    i=i+1

    # try:	
    #   print 'Recieved: '+str(param)
    #   lock.acquire()
    #   queue_param.append(param)
    #   lock.release()
    #   print 'Queued parameters.'
    # except:
    #   print "Check how many parameters you are sending! (Only "+str(nou*2)+" is allowed)"

  print 'process_parameters -----------------finished'

def execute_queued_params():
  global controller, queue_param, debug
  print 'execute_queued_params Thread -----------------started'	
  proc1 = 'SDN Topology'	
  # check if their are queued parameters that need to be executed and if the last execution has completed
  while (True):
    while len(queue_param)>0:
      #gets the current SDN data
      with open('objs.pkl', 'rb') as f:
        m_l, f_l, top_num, error, delta, param, b1_u, b2_u, switch = pickle.load(f)
        
        #guards from the initial NULL array stored in queue_param
        if str(queue_param[0]).find('155.0.0')>=0 or str(queue_param[0]).find('172.16.0')>=0:
          #writes the updated parameters in a file
          with open('objs.pkl', 'wb') as f:
            pickle.dump([m_l, f_l, top_num, error, delta, queue_param[0], b1_u, b2_u, switch], f)
        
          if debug == 'ON':
            print 'OUTPUT 4'
            print str(queue_param[0])

          # executes SDN configuration parameters	
          proc1 = subprocess.Popen(["python multiple_switch_test_v006.py"], stdout= subprocess.PIPE, shell=True, universal_newlines=True)

          time.sleep(0.001)
          # sob=proc1.stdout.read() #<-- sob should contain all of the output from 1 configuration if everything worked correctly
          # #waits until the execution of multiple_switch_test_v005 is completed			      
          # while sob.find('ERROR') == (-1) and sob.find('SDN Topology') == (-1) and sob.find('Complete!') == (-1):
            
          sob_test = proc1.stdout.readline()

          while sob_test.find('ERROR') < 0 and sob_test.find('Complete!') < 0:
          # while sob_test.find('ERROR') < 0 and sob_test.find('SDN Topology') < 0:
            sob_test = proc1.stdout.readline()
            if sob_test != '':
              print sob_test
          sob = sob_test

          i=0
          total_response=""
          while i < len(queue_param[0]):
            if i+1 != len(queue_param[0]):
              total_response = total_response + str(queue_param[0][i])+","
            else:
              total_response = total_response + str(queue_param[0][i])
            i=i+1
          # queue_param[0]=[queue_param[0][0],str(queue_param[0][1]),queue_param[0][2],str(queue_param[0][3])]

          #sends execution is completed to SDN DApp
          if sob.find('ERROR') >= 0:
            print '______2'
            controller.sendall('ERROR:'+total_response)
          elif sob.find('Complete!') >= 0:
            print '______3'
            # print 'COMPLETE:'+str(queue_param[0])
            # controller.sendall('COMPLETE:'+str(queue_param[0]))
            controller.sendall('COMPLETE:'+total_response)
          else:
            print '______5'				
            controller.sendall('PROBLEM:'+total_response)

        # remove executed configuration parameter from the queue_param list
        lock.acquire()	
        queue_param = queue_param[1:]
        lock.release()
        if debug == 'ON':
          print 'OUTPUT 1'
          print queue_param
  print 'execute_queued_params Thread -----------------finished'
            

thread = []

# identifies which function to run
thread.append(threading.Thread(target=collect_parameters))

# identifies which function to run
thread.append(threading.Thread(target=execute_queued_params))

#starts all threads
i=0
while i<len(thread):
    #kills are threads if this python script is killed
    thread[i].daemon = True
    thread[i].start()
    i=i+1

while thread[0].is_alive():
    time.sleep(60)


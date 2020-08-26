#PURPOSE: This code is intended to allow Nodes to send transactions using blockchain. 

#Instructions

#NOTE good threading link: https://stackoverflow.com/questions/1191374/using-module-subprocess-with-timeout
# You may have to install sudo apt install expect

import subprocess, threading, time, socket
from decimal import Decimal

#intializing variables
current_task = ""
SDN_STATUS = 'READY'
f= open("bandwidth_log.txt","a+")
query_trigger = 0
debug="ON"
nou=2
buffer_size = 256
server_ip_add = '155.0.0.1'
server_port = 11000
SDN_socket_con = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
SDN_socket_con.connect((server_ip_add, server_port))
#this is used when the same variable may be written at the same time by different threads
lock=threading.RLock()

def continuous_couchDB_query_trigger():
    global query_trigger
    print 'continuous_couchDB_query_trigger Thread ---------started'
    proc1 = subprocess.Popen(["unbuffer","curl","-X","GET","http://155.0.0.6:11007/mychannel_mycc2/_changes?feed=continuous&timeout=1&heartbeat=60000"], bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=False, close_fds=True, universal_newlines=True)
    time.sleep(1)

    # frou stands for FIRST ROUND OF UPDATES. It counts the first 3 couchdb updates because they redundant updates to indicate
    # that the query and execution transaction lists has been created as well as the initial configurations needed to configure
    # the base network.
    frou = 0 #
    
    # when executing a configureation the query and execution list are modified meaning 2 updates from couchdb
    # will be recieved when in reality only one configuration has been command. arch_flag accounts for this 
    # so that unneccessary queries are not executed
    arch_flag=0

    while (f.read()).find("yes")==(-1):
        proc1_line = str(proc1.stdout.readline())
        if proc1_line.find('None') == (-1) and len(proc1_line)>10:
            try:	
                print 'Recieved: '+str(proc1_line)
                couchDB_updates=proc1_line
                while i<len(couchDB_updates):
                    if str(proc1_line).find("archived_transaction_list")>0 and arch_flag==0:
                        # print "A"
                        if frou <3:
                            frou=frou+1
                            # print "B"
                        else:
                            # print "C"
                            arch_flag=1
                            lock.acquire()
                            query_trigger = query_trigger+1
                            lock.release()
                            print 'Queued parameters.'
                    elif str(proc1_line).find("queued_transaction_list")>0 and arch_flag==0:
                        if frou <3:
                            print "A"
                            frou=frou+1
                        else:
                            lock.acquire()
                            query_trigger = query_trigger+1
                            lock.release()
                            print 'Queued parameters.'
                    elif str(proc1_line).find("queued_transaction_list")>0 and arch_flag==1:
                        print "P"
                        arch_flag=0
                    elif str(proc1_line).find("required_switch_updates")>0:
                        print "D"
                        frou=frou+1                  
                    else:
                        print (proc1_line)
                        print "\n\n\n\n\n\n\n\n\nPROBLEM "+str(arch_flag)+": couchDB has made a change that is not exspected\n\n\n\n"
                        time.sleep(20)
                        lock.acquire()
                        query_trigger = query_trigger+1
                        lock.release()
                        print 'Queued parameters.'
                    i=i+!
            except:
                print "PROBLEM IN QUEUEING"

    print 'continuous_couchDB_query_trigger Thread---------finished'

def SDN_query():
    global query_trigger
    while (f.read()).find("yes")==(-1):
        if query_trigger > 0:
            print 'SDN_query ---------started'

            print "before query: waiting 20 seconds"
            time.sleep(20)

            proc1 = subprocess.Popen("curl -X POST -H \"Content-Type: application/json\" http://155.0.0.6:5555/containers/cli/exec -d '{ \"AttachStdin\":false,\"AttachStdout\":true,\"AttachStderr\":true, \"Tty\":false, \"Cmd\":[\"scripts/mycc2_query.sh\",\"2 1\"]}'", bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=True, close_fds=True, universal_newlines=True)
            exec_id = proc1.stdout.read()
            exec_id = exec_id[exec_id.find(":""")+2:len(exec_id)-3] #<-- removes the json formating
            print "EXEC ID: "+exec_id
            
            proc1 = subprocess.Popen("curl -X POST -H \"Content-Type: application/json\" http://155.0.0.6:5555/exec/"+str(exec_id)+"/start -d '{ \"Detach\":false,\"Tty\":false}'", bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=True, close_fds=True, universal_newlines=True)
            next_task = proc1.stdout.read()
            print "Original Next Task: "+str(next_task)
            next_task = next_task[next_task.find("Next Task:")+10:next_task.find("===EM END===")] #<-- removes the json formating
            print "After Trimming Next Task: "+next_task

            if next_task.find("155.0.")!=(-1):
                param =[]
                i=0
                while next_task.find(",")!=(-1):
                    if debug =="ON":
                        print "Before NEXT_TASK: "+str(next_task)
                    
                    eod=next_task.find(",")
                    
                    if eod == (-1):
                        eod = len(next_task)

                    if i%2 == 0:
                        param.append(next_task[0:eod])
                    else:
                        param.append(float(next_task[0:eod]))

                    next_task = next_task[eod+1:]
                    i=i+1
                    if debug =="ON":
                        print "After PARAM1: "+str(next_task)
                
                if len(next_task)>0:
                    ttt = str(next_task).splitlines()
                    # print ".."+ttt[0]+"..."
                    param.append(float(ttt[0]))
                    next_task = ""

                print "MESSAGE RECIEVED: "+str(param)
                time.sleep(30)
                cont_config_SDN(param)

            elif next_task.find("No Task Available")==(-1):
                # our system has been attacked because the current_task configurations do not match the SDN_SYSTEMS current task assigned
                print "PROBLEM: SDN 2 BC completion respones"

            print 'SDN_query ---------finished'
            query_trigger = query_trigger -1

def cont_config_SDN(*args):


 
def configure_SDN(*args):

def SDN_complete():

def eformat(f, prec, exp_digits):
    s = "%.*E"%(prec, float(f))
    mantissa, exp = s.split('E')
    return "%sE%+0*d"%(mantissa, exp_digits+1, int(exp))

def convert_num(data):
    i=0
    total=0
    while i<len(data):
        if data[i] == '1':
            total = total + 2^(i)
        i=i+1
    return total

thread = []

# identifies which function to run
thread.append(threading.Thread(target=init_couchDB_trigger))

# identifies which function to run
thread.append(threading.Thread(target=continuous_couchDB_query_trigger))

# identifies which function to run
thread.append(threading.Thread(target=SDN_query))

# # starts the first 2 threads
i=0
while i < 2:
    # kills all threads if this python code is killed
    thread[i].daemon = True
    thread[i].start()
    i=i+1


while thread[0].is_alive():
    time.sleep(10)
    print ("waiting for init_couchDB_trigger to finish......")

thread[2].daemon = True
thread[2].start()

while thread[2].is_alive():
    time.sleep(10)
    print ("waiting for continuous couchDB......"+str(query_trigger))


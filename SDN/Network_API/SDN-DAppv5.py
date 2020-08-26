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

    while (f.read()).find("yes")==(-1):
        proc1_line = str(proc1.stdout.readline())
        if proc1_line.find('None') == (-1) and len(proc1_line)>10:
            try:	
                print 'Recieved: '+str(proc1_line)
                lock.acquire()
                query_trigger = query_trigger+1
                lock.release()
                print 'Queued parameters.'
            except:
                print "PROBLEM IN QUEUEING"

    print 'continuous_couchDB_query_trigger Thread---------finished'

def SDN_query():
    global query_trigger
    while (f.read()).find("yes")==(-1):
        if query_trigger > 0:
            print 'SDN_query ---------started'

            proc1 = subprocess.Popen("curl -X POST -H \"Content-Type: application/json\" http://155.0.0.6:5555/containers/cli/exec -d '{ \"AttachStdin\":false,\"AttachStdout\":true,\"AttachStderr\":true, \"Tty\":false, \"Cmd\":[\"scripts/mycc2_query.sh\",\"2 1\"]}'", bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=True, close_fds=True, universal_newlines=True)
            exec_id = proc1.stdout.read()
            exec_id = exec_id[exec_id.find(":""")+2:len(exec_id)-3] #<-- removes the json formating
            print "EXEC ID: "+exec_id
            
            proc1 = subprocess.Popen("curl -X POST -H \"Content-Type: application/json\" http://155.0.0.6:5555/exec/"+str(exec_id)+"/start -d '{ \"Detach\":false,\"Tty\":false}'", bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=True, close_fds=True, universal_newlines=True)
            next_task = proc1.stdout.read()
            next_task = next_task[next_task.find("Next Task:")+10:next_task.find("=======")] #<-- removes the json formating
            print "NEXT TASK: "+next_task

            if next_task.find("155.0.")!=(-1):
                param =[]
                i=0
                while next_task.find(",")!=(-1):
                    if debug =="ON":
                        print "Before NEXT_TASK: "+str(next_task)
                    eod=next_task.find(",")
                    
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

                cont_config_SDN(param)

            elif next_task.find("No Task Available")==(-1):
                # our system has been attacked because the current_task configurations do not match the SDN_SYSTEMS current task assigned
                print "PROBLEM: SDN 2 BC completion respones"

            print 'SDN_query ---------finished'
            query_trigger = query_trigger -1

def cont_config_SDN(*args):
    global current_task, SDN_STATUS, debug, nou
    print 'cont_config_SDN ---------started'
    
    data_output = args[0]
    if len(data_output) > 0:

        # splits the data
        print "DATA_OUTPUT: "+str(data_output)

        if str(data_output).find("155.0.") != (-1): #this is a redundant confirmation
           

            # clear current_task
            current_task = []
            if debug == "ON":
                print "DEBUGGIN INFO: "+str(len(data_output))
            s=0
             
            while s<(nou*2) and str(data_output[s]).find("155.0.") != (-1):
                if debug == "ON":
                    print str(s)+"\n\n"
                current_task.append(str(data_output[s]))
                current_task.append(str(float(data_output[s+1])))
                s=s+2
            
            if SDN_STATUS == 'READY':
                SDN_STATUS='IN PROGRESS'
                print (current_task)
                print ("message: "+str(current_task[0])+","+str(float(current_task[1]))+","+str(current_task[2])+","+str(float(current_task[3])))
                SDN_socket_con.sendall(str(current_task[0])+","+str(float(current_task[1]))+","+str(current_task[2])+","+str(float(current_task[3])))
                # return response to blockchain that their were or weren't any errors
                SDN_complete()
                SDN_STATUS = 'READY'
        else:
            print "No INITIAL network configurations found"

    print 'cont_config_SDN ---------finished'

def init_couchDB_trigger():
    print 'INIT_couchDB_trigger Thread ---------started'
    proc1 = subprocess.Popen(["unbuffer","curl","-X","GET","http://155.0.0.6:11007/mychannel_mycc/_changes?feed=continuous&timeout=1&heartbeat=60000"], bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=False, close_fds=True, universal_newlines=True)
    time.sleep(1)
    checkers= []

    while (f.read()).find("yes")==(-1) and convert_num(checkers) == 0:
        proc1_line = proc1.stdout.readline()
        if str(proc1_line).find('None') == (-1):
            # print "EM----"+str(proc1_line)
            # time.sleep(1)
            # Their are changes to the CC
            if proc1_line.find('required_switch_updates') != (-1):
                checkers.append('1')
                print proc1_line #<-- used to determine if the configuration was caught by this thread
                configure_SDN(proc1_line)

    print 'INIT_couchDB_Trigger Thread---------finished'
 
def configure_SDN(*args):
    global current_task, SDN_STATUS
    print 'configure_SDN ---------started'
    while (f.read()).find("yes")==(-1):
        data_output = args[0]
        if len(data_output) > 0:

            # splits the data
            # {"seq":"1-g1AAAAFreJzLYWBg4MhgTmHgzcvPy09JdcjLz8gvLskBCjMlMiTJ____PyuDOZEhFyjAbpCYZm5kYpbCwFmal5KalpmXmoJDa5ICkEyyh-pmBOu2TE5KMjM2QFePywQHkAnxIBMSGXCpSQCpqcerJo8FSDI0ACmgsvmE1C2AqNtPSN0BiLr7hNQ9gKgDuS8LAP1DcmY",
            # "id":"\u0000required_switch_updates\u00002019-11-22 12:50:08.399909688 +0000 UTC\u00002019-11-22 12:50:26.366229686 +0000 UTC\u0000155.0.0.35\u00001.25E+02\u0000155.0.0.36\u00001.25E+02\u0000",
            # "changes":[{"rev":"1-e92fa9c4dbdf9b12f2fc1a73c5329eea"}]}
            # print "Ephraim DEBUG 1"
            data = data_output.split("\u0000")
            checkers= []
            if data_output.find("required_switch_updates") != (-1): #this is a redundant confirmation
                s=0
                while data[s].find("155.0.0.")==(-1) and s<=len(data):
                    if data[s].find("required_switch_updates")>=0:
                        checkers.append('1')
                    s=s+1
                if convert_num(checkers)>=1:

                    # clear current_task
                    current_task = []
                    data = data[s].split(",") #this will split a string like 155.0.0.35,2.5E+01,155.0.0.36,2.5E+01,155.0.0.37,2.5E+01,155.0.0.38,2.5E+01,155.0.0.65,2.5E+01,155.0.0.66,2.5E+01,155.0.0.67,2.5E+01,155.0.0.68,2.5E+01 into an array
                    s=0
                    sendall_command=""
                    while data[s].find("155.0.0.") != (-1):
                        print str(len(data))+'\n'
                        print str(s)
                        # print data[s]
                        # print '............DATA\n'
                        # print data[s+1]
                        # print '............DATA\n'
                        if s!=len(data)-2:
                            sendall_command = sendall_command + str(data[s]) + "," + str(float(data[s+1])) + ","
                            s=s+1
                        else:
                            sendall_command = sendall_command + str(data[s]) + "," + str(float(data[s+1]))
                            s=s+2
                    
                    if SDN_STATUS == 'READY':
                        SDN_STATUS='IN PROGRESS'
                        print (current_task)
                        # print ("message: "+str(current_task[0])+","+str(float(current_task[1]))+","+str(current_task[2])+","+str(float(current_task[3])))
                        SDN_socket_con.sendall(sendall_command)
                        # return response to blockchain that their were or weren't any errors
                        SDN_complete()
                        SDN_STATUS = 'READY'
                        break
            else:
                print "No INITIAL network configurations found"
                break

    print 'configure_SDN ---------finished'

def SDN_complete():
    global query_trigger
    print 'SDN_complete ---------started'

    task = str(current_task[0])+","+str(float(current_task[1]))+","+str(current_task[2])+","+str(float(current_task[3]))
    response = SDN_socket_con.recv(4096)
    eod = response.find(':')
    if response.find(task)!=(-1):
        if response[0:eod] == 'COMPLETE':
            print "CONFIGURATIONS: "+str(current_task[0])+" "+str(eformat(current_task[1],2,2))+" "+str(current_task[2])+" "+str(eformat(current_task[3],2,2))
                                                # curl -X POST -H "Content-Type: application/json" http://155.0.0.6:5555/containers/cli/exec -d '{ "AttachStdin":false,"AttachStdout":true,"AttachStderr":true, "Tty":false, "Cmd":["scripts/mycc_invoke.sh","2 1 3 2 invoke 155.0.0.35 155.0.0.36 10"]}'
            proc1 = subprocess.Popen("curl -X POST -H \"Content-Type: application/json\" http://155.0.0.6:5555/containers/cli/exec -d '{ \"AttachStdin\":false,\"AttachStdout\":true,\"AttachStderr\":true, \"Tty\":false, \"Cmd\":[\"scripts/mycc2_complete.sh\",\"2 1 3 2 completed_task "+str(current_task[0])+" "+str(eformat(current_task[1],2,2))+" "+str(current_task[2])+" "+str(eformat(current_task[3],2,2))+"\"]}'", bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=True, close_fds=True, universal_newlines=True)
            exec_id = proc1.stdout.read()
            exec_id = exec_id[exec_id.find(":""")+2:len(exec_id)-3] #<-- removes the json formating
            print "EXEC ID: "+exec_id
            
            proc1 = subprocess.Popen("curl -X POST -H \"Content-Type: application/json\" http://155.0.0.6:5555/exec/"+str(exec_id)+"/start -d '{ \"Detach\":false,\"Tty\":false}'", bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=True, close_fds=True, universal_newlines=True)
            time.sleep(0.1)
            complete_response = proc1.stdout.read()
            print complete_response
            if complete_response.find("Chaincode invoke successful. result: status:200")!=(-1):
                print 'SDN_complete ---------finished'
                if query_trigger ==1:
                    query_trigger = query_trigger+1
                    print 'Queued parameters in SDN_complete'
            else:
                print "PROBLEM: SDN 2 BC completion respones"
        else:
            print response[0:eod]
    else:
        # our system has been attacked because the current_task configurations do not match the SDN_SYSTEMS current task assigned
        print "PROBLEM with commanded configurations"

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

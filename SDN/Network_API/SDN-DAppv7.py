#PURPOSE: This code is intended to allow Nodes to send transactions using blockchain. 

#Instructions

#NOTE good threading link: https://stackoverflow.com/questions/1191374/using-module-subprocess-with-timeout
# You may have to install sudo apt install expect

import subprocess, threading, time, socket, datetime
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
server_port = 10500
SDN_socket_con = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
SDN_socket_con.connect((server_ip_add, server_port))
#this is used when the same variable may be written at the same time by different threads
lock=threading.RLock()

# 1st function
def init_couchDB_trigger():
    global query_trigger
    print '\nSTEP#1: INIT_couchDB_trigger Thread ---------started'
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
                print '\nSTEP#1.1: '+proc1_line #<-- used to determine if the configuration was caught by this thread
                configure_SDN(proc1_line)
    lock.acquire()
    query_trigger=query_trigger+1
    lock.release()
    print '\nSTEP#1.2: INIT_couchDB_Trigger Thread---------finished'

# 2nd function
def configure_SDN(*args):
    global current_task, SDN_STATUS, outtext
    print 'STEP#2: '+'configure_SDN ---------started'
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
            print "STEP#2.1: "+"If "+str(data_output.find("required_switch_updates"))+">=0 Then this is good"
            if data_output.find("required_switch_updates") != (-1): #this is a redundant confirmation
                s=0
                while data[s].find("155.0.0.")==(-1) and s<=len(data):
                    if data[s].find("required_switch_updates")>=0:
                        checkers.append('1')
                    s=s+1
                if convert_num(checkers)>=1:

                    # clear current_task
                    current_task = ""
                    data = data[s].split(",") #this will split a string like 155.0.0.35,2.5E+01,155.0.0.36,2.5E+01,155.0.0.37,2.5E+01,155.0.0.38,2.5E+01,155.0.0.65,2.5E+01,155.0.0.66,2.5E+01,155.0.0.67,2.5E+01,155.0.0.68,2.5E+01 into an array
                    s=0
                    while data[s].find("155.0.0.") != (-1):
                        # print data[s]
                        # print '............DATA\n'
                        # print data[s+1]
                        # print '............DATA\n'
                        if s==len(data)-2:
                            current_task = current_task + str(data[s]) + "," + str(float(data[s+1]))
                            s=s+1
                        else:
                            current_task = current_task + str(data[s]) + "," + str(float(data[s+1])) + ","
                            s=s+2
                    
                    if SDN_STATUS == 'READY':
                        SDN_STATUS='IN PROGRESS'
                        SDN_socket_con.sendall(current_task)
                        # return response to blockchain that their were or weren't any errors
                        
                        if len(data[s])==2: # this reduces the redundant SDN_complete that occurs due to the init setup configuration for the whole SDN network
                            SDN_complete()
                        else:
                            response = SDN_socket_con.recv(4096)
                            if response.find("COMPLETE")==(-1) or response.find(current_task)==(-1):
                                print "STEP#2.4: Problem with INITIAL network configurations found"
                        SDN_STATUS = 'READY'
                        break
            else:
                print "STEP#2.3: No INITIAL network configurations found"
                break

    print 'STEP#2.2: '+'configure_SDN ---------finished'

def continuous_couchDB_query_trigger():
    global query_trigger
    print 'continuous_couchDB_query_trigger Thread ---------started'
    proc1 = subprocess.Popen(["unbuffer","curl","-X","GET","http://155.0.0.6:11007/mychannel_mycc2/_changes?feed=continuous&timeout=1&heartbeat=60000"], bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=False, close_fds=True, universal_newlines=True)
    time.sleep(1)

    # frou stands for FIRST ROUND OF UPDATES. It counts the first two couchdb updates because 
    # they are redundant updates that notify listerners that the queue and execution 
    # transactions have been created.
    frou = 0 #
    
    # when executing a configureation the query and execution list are modified meaning 2 updates from couchdb
    # will be recieved when in reality only one configuration has been command. arch_flag accounts for this 
    # so that unneccessary queries are not executed
    arch_flag=0
    frou_wait_time=time.time()
    while (f.read()).find("yes")==(-1):
        proc1_line = str(proc1.stdout.readline())
        if time.time()-frou_wait_time > 5:
            frou=2
        if proc1_line.find('None') == (-1) and len(proc1_line)>10:
            try:	
                print 'Recieved: '+str(proc1_line)+'\n'
                couchDB_updates=proc1_line.splitlines()
                i=0
                while i<len(couchDB_updates):
                    if str(couchDB_updates[i]).find("archived_transaction_list")>0 and arch_flag==0:
                        if frou <2:
                            frou=frou+1
                            # print "B"
                        else:
                            
                            lock.acquire()
                            query_trigger = query_trigger+1
                            lock.release()
                            print 'Queued parameters.\n'
                    elif str(couchDB_updates[i]).find("queued_transaction_list")>0 and arch_flag==0:
                        if frou <2:
                            # print "A"
                            frou=frou+1
                        else:
                            arch_flag=1
                            lock.acquire()
                            query_trigger = query_trigger+1
                            lock.release()
                            print 'Queued parameters.\n'
                    elif str(couchDB_updates[i]).find("queued_transaction_list")>0 and arch_flag==1:
                        # This statement will be true when 
                            arch_flag=1
                            lock.acquire()
                            query_trigger = query_trigger+1
                            lock.release()
                            print 'Queued parameters.\n'
                    elif str(couchDB_updates[i]).find("archived_transaction_list")>0 and arch_flag==1:
                        # print "P"
                        arch_flag=0                 
                    else:
                        print (couchDB_updates[i])
                        print "\n\n\n\n\n\n\n\n\nPROBLEM "+str(arch_flag)+": couchDB has made a change that is not expected\n\n\n\n"
                        # time.sleep(20)
                        lock.acquire()
                        query_trigger = query_trigger+1
                        lock.release()
                        print 'Queued parameters.\n'
                    i=i+1
            except:
                print "PROBLEM IN QUEUEING\n"

    print 'continuous_couchDB_query_trigger Thread---------finished\n'


# 4th function
def SDN_query():
    global query_trigger, outtext
    while (f.read()).find("yes")==(-1):
        if query_trigger > 0:
            print '\nSTEP#4: SDN_query ---------started'

            # print "before query: waiting 20 seconds"
            # time.sleep(20)
            proc1 = subprocess.Popen("curl -X POST -H \"Content-Type: application/json\" http://155.0.0.6:5555/containers/cli/exec -d '{ \"AttachStdin\":false,\"AttachStdout\":true,\"AttachStderr\":true, \"Tty\":false, \"Cmd\":[\"scripts/mycc2_query.sh\",\"2 1 2 2\"]}'", bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=True, close_fds=True, universal_newlines=True)
            exec_id = proc1.stdout.read()
            exec_id = exec_id[exec_id.find(":""")+2:len(exec_id)-3] #<-- removes the json formating
            print "\nSTEP#4.1: EXEC ID: "+exec_id
            
            proc1 = subprocess.Popen("curl -X POST -H \"Content-Type: application/json\" http://155.0.0.6:5555/exec/"+str(exec_id)+"/start -d '{ \"Detach\":false,\"Tty\":false}'", bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=True, close_fds=True, universal_newlines=True)
            next_task = proc1.stdout.read()
            print "\nSTEP#4.2: Original Next Task: "+str(next_task)

            # Sometimes for an unknown reason the payload will not output, resulting in the next transaction not being executed.
            # Adding this if will prevent the program from crashing and push for another query.
            if next_task.find("===EM END===") >=0:
                
                next_task = next_task[next_task.find("Next Task:")+10:next_task.find("===EM END===")] #<-- removes the json formating
                print "\nSTEP#4.3: After Trimming Next Task: "+next_task

                if next_task.find("155.0.")!=(-1):
                    param =[]
                    i=0
                    while next_task.find(",")!=(-1):
                        if debug =="ON":
                            print "\nSTEP#4.4: Before NEXT_TASK: "+str(next_task)
                        
                        eod=next_task.find(",")
                        
                        if eod == (-1):
                            eod = len(next_task)

                        if i%2 == 0:
                            param.append(next_task[0:eod])
                        else:
                            try:
                                param.append(float(next_task[0:eod]))
                            except:
                                print "\n\n\n There was a problem \n.."
                                print '\nSTEP#4.9: Next Task'+str(next_task)+'..\n'
                                lock.acquire()
                                query_trigger=1
                                lock.release()

                        next_task = next_task[eod+1:]
                        i=i+1
                        if debug =="ON":
                            print "\nSTEP#4.5: After PARAM1: "+str(next_task)
                    
                    if len(next_task)>0:
                        ttt = str(next_task).splitlines()
                        # print ".."+ttt[0]+"..."
                        param.append(float(ttt[0]))
                        next_task = ""
                    outtext.write("Query\t"+str(time.time())+"\t "+str(param)+"\n")
                    print "\nSTEP#4.6: MESSAGE RECIEVED: "+str(param)
                    # time.sleep(30)
                    cont_config_SDN(param)
                elif next_task.find("No Task Available")>=0:
                    # This case will prevent from redundantly quering BC when their are no more task.
                    # This case is normally met when there are back to back configurations executed by the
                    #    
                    if query_trigger > 1:
                        lock.acquire()
                        query_trigger=1
                        lock.release()
                    outtext.write("Query\t"+str(time.time())+"\t No Task Available\n")
                elif next_task.find("No Task Available")==(-1):
                    # our system has been attacked because the current_task configurations do not match the SDN_SYSTEMS current task assigned
                    print "\nSTEP#4.8: PROBLEM: SDN 2 BC completion respone"
                    outtext.write("Query\t"+str(time.time())+"\t STEP#4.8 with the Query (No task recieved from the Query Transaction).\n")
                    time.sleep(20)

                print '\nSTEP#4.7: SDN_query ---------finished'
                lock.acquire()
                query_trigger = query_trigger - 1
                lock.release() 
            else:
                # if next_task.find("===EM END2===") <0:
                #     break
                print "\nSTEP#4.9: PROBLEM: SDN 2 BC completion respone"
                outtext.write("Query\t"+str(time.time())+"\t STEP#4.9 with the Query (No task recieved from the Query Transaction).\n")
                time.sleep(20)

# 5th function
def cont_config_SDN(*args):
    global current_task, SDN_STATUS, debug, nou, outtext, SDN_socket_con
    print '\nSTEP#5.1: cont_config_SDN ---------started'
    
    data_output = args[0]
    if len(data_output) > 0:

        # splits the data
        print "\nSTEP#5.2: DATA_OUTPUT: "+str(data_output)

        if str(data_output).find("155.0.") != (-1): #this is a redundant confirmation
           

            # clear current_task
            current_task = []
            if debug == "ON":
                print "\nSTEP#5.3: If "+str(len(data_output))+"=4 Then this is good"
            s=0
             
            while s<(nou*2) and str(data_output[s]).find("155.0.") != (-1):
                if debug == "ON":
                    print "\nSTEP#5.4: "+str(s)+"\n\n"
                current_task.append(str(data_output[s]))
                current_task.append(str(float(data_output[s+1])))
                s=s+2
            
            if SDN_STATUS == 'READY':
                SDN_STATUS='IN PROGRESS'
                if debug == "ON":
                    print "\nSTEP#5.5: Current Task: "+str(current_task)
                    print "\nSTEP#5.6: Message: "+str(current_task[0])+","+str(float(current_task[1]))+","+str(current_task[2])+","+str(float(current_task[3]))
                outtext.write("cont_config_SDN\t"+str(time.time())+"\t "+str(current_task)+"\n")
                SDN_socket_con.sendall(str(current_task[0])+","+str(float(current_task[1]))+","+str(current_task[2])+","+str(float(current_task[3])))
                # return response to blockchain that their were or weren't any errors
                SDN_complete()
                SDN_STATUS = 'READY'
        else:
            print "\nSTEP#5.8: No INITIAL network configurations found"

    print '\nSTEP#5.7: cont_config_SDN ---------finished'


# 3rd function
def SDN_complete():
    global current_task, outtext, query_trigger
    print '\nSTEP#3: SDN_complete ---------started'
    
    # ======== This is will just use the current tasks formatting when it is the initial configuration, but when it is on
    #  the continuous configuration setup current tasks is array that need reformatting
    if str(current_task).find("[")!=(-1):
        print '\nSTEP#3.1: '
        task = ""
        s=0
        while s<len(current_task):
            if s+2>=len(current_task):
                task = task + str(current_task[s]) + "," + str(current_task[s+1])
            else:
                task = task + str(current_task[s]) + "," + str(current_task[s+1]) + ","
            s=s+2
    else:
        task = current_task
    print "\nSTEP#3.2: CURRENT TASK: "+str(task)
    # ==============================

    # This is the response from the vNO of the SDN Controller.
    print "\nbefore response\n"
    response = SDN_socket_con.recv(4096)
    print "\nafter response\n"
    eod = response.find(':')
    # print "RECIEVED RESPONSE: "+str(response)

    # This will confirm that the task execute to the vNO was completed 
    if response.find(task)!=(-1):
        if response[0:eod] == 'COMPLETE':
            
            # ======= This is meant to re-format the BW values into exponential form
            BC_task=""
            data=task.split(",")
            s=0
            while s<len(data):
                sig_num=1
                # data[s] is the ip address
                # data[s+1] is the BW allocation for said ip address
                temp_num = float(data[s+1])
                if temp_num < 100:
                    sig_num=1
                    if temp_num%10 == 0:
                        sig_num=sig_num-1
                elif temp_num < 1000:
                    sig_num=2
                    if temp_num%100 == 0:
                        sig_num=sig_num-2
                    elif temp_num%10 == 0:
                        sig_num=sig_num-1
                BC_task = BC_task + " " + str(data[s]) + " " + str(eformat(data[s+1],sig_num,2))
                s=s+2
            print "\nSTEP#3.3: CONFIGURATIONS: "+BC_task
            # ====================
            
            # This obtains the container in which we need to execute 
                                                # curl -X POST -H "Content-Type: application/json" http://155.0.0.6:5555/containers/cli/exec -d '{ "AttachStdin":false,"AttachStdout":true,"AttachStderr":true, "Tty":false, "Cmd":["scripts/mycc_invoke.sh","2 1 3 2 invoke 155.0.0.35 155.0.0.36 10"]}'
            proc1 = subprocess.Popen("curl -X POST -H \"Content-Type: application/json\" http://155.0.0.6:5555/containers/cli/exec -d '{ \"AttachStdin\":false,\"AttachStdout\":true,\"AttachStderr\":true, \"Tty\":false, \"Cmd\":[\"scripts/mycc2_complete.sh\",\"2 1 2 2 completed_task "+BC_task+"\"]}'", bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=True, close_fds=True, universal_newlines=True)
            exec_id = proc1.stdout.read()

            exec_id = exec_id[exec_id.find(":""")+2:len(exec_id)-3] #<-- removes the json formating
            # print "EXEC ID: "+exec_id # Meant for debugging
            
             # This executes the docker command to indicate the task assigned has been completed
            proc1 = subprocess.Popen("curl -X POST -H \"Content-Type: application/json\" http://155.0.0.6:5555/exec/"+str(exec_id)+"/start -d '{ \"Detach\":false,\"Tty\":false}'", bufsize=0, stdout=subprocess.PIPE, stderr=None, shell=True, close_fds=True, universal_newlines=True)
            time.sleep(0.1)
            complete_response = proc1.stdout.read()
            print complete_response
            
            # Confirms  mycc2_complete script executed properly 
            if complete_response.find("Chaincode invoke successful. result: status:200")!=(-1):
                print '\nSTEP#3.4: SDN_complete ---------finished\n'
                outtext.write("Complete\t"+str(time.time())+"\t "+str(BC_task)+"\n")
                lock.acquire()
                if complete_response.find(": No Task Available===EM END===")!=(-1):
                    query_trigger = 1
                current_task=""
                lock.release()
            else:
                if complete_response.find("did not match current task")!=(-1):
                    outtext.write("Complete\t"+str(time.time())+"\t Did not match current task\n")
                print "\nSTEP#3.5: PROBLEM: SDN 2 BC completion response\n"
        else:
            print response[0:eod]
    else:
        # our system has been attacked because the current_task configurations do not match the SDN_SYSTEMS current task assigned
        print "\nSTEP#3.6: PROBLEM with commanded configurations\n"
        print "\nSTEP#3.7: response:"+str(response)

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

# this file stores the tasks accomplished by DApp
x = datetime.datetime.now()
outtext = open("DAPPv7"+"_"+str(x.day)+"_"+str(x.month)+"_"+str(x.year)+"_"+str(int(time.time()))+".csv","w+")

outtext.write("Task Name:\tTime:\tTask Info:\n")

# identifies which function to run
thread.append(threading.Thread(target=init_couchDB_trigger))

# identifies which function to run
thread.append(threading.Thread(target=continuous_couchDB_query_trigger))

# identifies which function to run
thread.append(threading.Thread(target=SDN_query))

# # starts the first 2 threads
i=0
while i < 3:
    # kills all threads if this python code is killed
    thread[i].daemon = True
    thread[i].start()
    i=i+1

while thread[0].is_alive():
    time.sleep(5)
    print ("\nwaiting for init couchDB......Query #:"+str(query_trigger)+"\n")

while thread[1].is_alive() and thread[2].is_alive():
    time.sleep(10)
    print ("\nwaiting for continuous couchDB and sdn_query......Query #:"+str(query_trigger)+"\n")

outtext.close()

  
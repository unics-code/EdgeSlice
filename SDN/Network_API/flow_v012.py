import requests
import sys
import time
import numpy as np
import csv
import os

# s_nums = [[0,2,4],[0,1],[4,3,1]] #TODO figure out why path 3 is not working
s_nums = [[0,1],[4,3,1]] 
#        155.0.0.35<-->155.0.0.36     155.0.0.35<-->155.0.0.10      155.0.0.36<-->155.0.0.10
# ports = [[[[12,1]],[[1,7]],[[3,12]]], [[[12,3]],[[1,12]]]          ,[[[12,5]],[[1,3]],[[5,12]]]   ] #TODO change this to the path desired for your topology
#          155.0.0.35<-->155.0.0.10   155.0.0.36<-->155.0.0.10
ports = [ [[[12,3]],[[1,12]]]        ,[[[12,5]],[[1,3]],[[5,12]]]  ]
max_num_of_flows_per_user=0
i=0
while i<len(ports):
    p=0
    temp_count=0
    while p<len(ports[i]):
        x=0
        temp_count=temp_count+len(ports[i][p])
        p=p+1
    i=i+1

    if temp_count>max_num_of_flows_per_user:
            #TODO if ports has more than a point 2 point path on any switch this code needs to be changed
            max_num_of_flows_per_user=temp_count
max_num_of_flows_per_user=max_num_of_flows_per_user*2
print "Max # of FLows Per User = "+str(max_num_of_flows_per_user)+"\n"
    # Calculation example for 1 user
        # 2 flows for input to output, which contains 1 arp and 1 ip flow per switch
        # 2 flows for output to input, which contains 1 arp and 1 ip flow per switch
        # this brings the total # of flows to 4
        # we then multiply by 2 for alternate network topology
        # this brings our total to 8 flows per user for no failover with Dynamic BW control
        # but we only put 4 because the script handles the *2

num_of_static_flows=0
Qiang_ACK='TRUE' #when this is FALSE no acknowledgement is recieved by this script
headers = {
'Accept': "application/xml",
'Content-Type': "application/xml",
'Authorization': "Basic YWRtaW46YWRtaW4="
}

debug = 'OFF'
flow_error = []

#R_ses=requests.Session() # TODO need to get this work for delete
R_ses=''
    #STATUS CODES:
    #201 Created
    #200 OK
    #404 Not Found

def get_E():
    global flow_error
    return flow_error

def clear_E():
    global flow_error
    flow_error=[]

def clear(*args):
    global debug, error
    s_time = time.time()	
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 #the switch name

    url = "http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+str(args[0])+"/"
    #print(url) #debuging code

    payload = ""
    #response = R_ses.delete(url, data=payload, headers=headers)
    response = requests.request("DELETE", url, data=payload, headers=headers)
    
    # print(str(response.status_code)) #debuging code
    if (response.status_code==200) or (response.status_code==404):
        print('Switch '+str(args[0])+' was cleared\n')
    else:
        #print(str(response.text)) #debuging code
        print('ERROR:Unable to clear Switch '+str(args[0])+'\n')
        flow_error.append('1')
    if debug == 'ON':
        print 'Time;'+str(time.time()-s_time)+';Request_Type;DELETE;Switch_Num; ;Function_Name;clear'
    

def add_meter(*args):
    global debug, error, headers
    s_time = time.time()	
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 #the switch name
    #args[1] = 20 #BW rate in Megabytes per sec

    #meter counter
    meter_num=1
    print '\n\nStart add_meter'
    #the initial GET
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:meter/'+str(meter_num)
    #print(url)
    payload = ""
    #response = R_ses.get(url, data=payload, headers=headers)
    response = requests.request("GET", url, data=payload, headers=headers)
    #response.encoding = 'utf-8'
    #print(response.text) #debuging code
    #print(str(response.status_code)) #debuging code

    #determines the next available meter number to use
    while(response.status_code!=404):
        if debug == 'ON':
            print 'Time;'+str(time.time()-s_time)+';Request_Type;GET;Switch_Num;'+str(args[0])+';Function_Name;add_meter'		
        meter_num=meter_num+1
        url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:meter/'+str(meter_num)
        #response = R_ses.get(url, data=payload, headers=headers)
        s_time = time.time()
        response = requests.request("GET", url, data=payload, headers=headers)
    
    if debug == 'ON':
        print 'Time;'+str(time.time()-s_time)+';Request_Type;GET;Switch_Num;'+str(args[0])+';Function_Name;add_meter'	
    
    #print('final meter number '+str(meter_num)) #debuging code
    #convert the BW rate to kilobits per sec. from Megabytes/s
    #print('MBps='+str(sys.argv[1])) #debuging code
    kbps=int(float(args[1])*8*1000)
    print('kbps rate limit='+str(kbps)) #debuging code
    #print('kbps rate limit='+str(kbps)) #debuging code

    #print(url) #debuging code
    #xml code to add a meter
    payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<meter xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<meter-id>"+str(meter_num)+"</meter-id>\n\
\t<container-name>mymeter</container-name>\n\
\t<meter-name>mymeter</meter-name>\n\
\t<flags>meter-kbps</flags>\n\
\t<meter-band-headers>\n\
\t\t<meter-band-header>\n\
\t\t\t<band-id>0</band-id>\n\
\t\t\t<band-rate>"+str(kbps)+"</band-rate>\n\
\t\t\t<meter-band-types>\n\
\t\t\t\t<flags>ofpmbt-drop</flags>\n\
\t\t\t</meter-band-types>\n\
\t\t\t<band-burst-size>100</band-burst-size>\n\
\t\t\t<drop-rate>"+str(kbps)+"</drop-rate>\n\
\t\t\t<drop-burst-size>100</drop-burst-size>\n\
\t\t</meter-band-header>\n\
\t</meter-band-headers>\n\
</meter>"
    #print(payload) #debuging code
    #send http put request
    #response = R_ses.put(url, data=payload, headers=headers)
    s_time = time.time()
    response = requests.request("PUT", url, data=payload, headers=headers)
    #print('Status Code ='+str(response.status_code))#debuging code
    if (response.status_code==201):
        print('Meter '+str(meter_num)+' was added\n')
        if debug == 'ON':
            print 'Time;'+str(time.time()-s_time)+';Request_Type;PUT;Switch_Num;'+str(args[0])+';Function_Name;add_meter'			
        return(meter_num)
    else:
        flow_error.append('2')
        print(str(response.text)) #debuging code
        print('ERROR:Unable to add Meter '+str(meter_num)+'\n')
        if debug == 'ON':
            print 'Time;'+str(time.time()-s_time)+';Request_Type;PUT;Switch_Num;'+str(args[0])+';Function_Name;add_meter'	
        return(99999)
    
    return len(error)

def delete_meter(*args):
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 #the switch name
    #args[1] = 2 #meter #


    # url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:meter/'+str(args[1])
    # payload=''
    # response = requests.request("DELETE", url, data=payload, headers=headers)
    # if ((response.status_code==201) or (response.status_code==200) or (response.status_code==404)):
    #     print('Meter '+str(args[1])+' was deleted.\n')

    #deletes the flows belonging to the previous topology associated with args[1]
    
    #delete all of the flows in the config datastore associated with args[1]
    payload=''
    out_count=0
    cur_flow=1+max_num_of_flows_per_user*(int(args[1])-1)+num_of_static_flows
    print '\n\nStart delete_previous_meter_flows on meter'+str(int(args[1]))
    url = "http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+str(args[0])+"/flow-node-inventory:table/0/flow/"
    while(out_count<max_num_of_flows_per_user+1):
        s_time = time.time()
        print url+str(int(cur_flow))+"\n"
        response = requests.request("GET", url+str(int(cur_flow)), data=payload, headers=headers)
        
        # print str(response.status_code)
        # print (response.text.encode('utf8'))
        if (response.status_code==200):
            # if debug == 'ON':
                # print 'Time;'+str(time.time()-s_time)+';Request_Type;GET;Switch_Num;'+str(args[0])+';Function_Name;modify_meter1;Flow#;'+str(cur_flow)				
            if ((response.content.find('meter-id>'+str(args[1])+'<')!=-1) or ((response.content.find('meter-id>')==-1) and (response.content.find('type>2054')==-1))):
                #print(cur_flow)
                s_time = time.time()
                print '\n previous_meter DELTED FLOW#: '+str(cur_flow)
                #print response.content
                response = requests.request("DELETE", url+str(cur_flow), data=payload, headers=headers)
                # print 'Time;'+str(time.time()-s_time)+';Request_Type;DELETE;Switch_Num;'+str(args[0])+';Function_Name;modify_meter3;Flow#;'+str(cur_flow)				
            else:
                out_count=out_count+1
        else:
            # if debug == 'ON':
            #     print 'Time;'+str(time.time()-s_time)+';Request_Type;GET;Switch_Num;'+str(args[0])+';Function_Name;modify_meter2;Flow#;'+str(cur_flow)			
            out_count=out_count+1
        
        cur_flow=cur_flow+1
    

def modify_meter(*args):
    global debug, error, headers
    total_modify_time=time.time()
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 #the switch name
    #args[1] = 2 #meter #
    #args[2] = 20 #BW rate in Megabits per sec
    
    #deletes the meters associated with args[1]
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:meter/'+str(args[1])
    # print ("\n....."+url+".....\n") #debuging code
    payload=''
    #response = R_ses.delete(url, data=payload, headers=headers)
    response = requests.request("DELETE", url, data=payload, headers=headers)
    
    #delete all of the flows in the config datastore belonging to the current meter
    out_count=0
    cur_flow=1+max_num_of_flows_per_user*(int(args[1])-1)+num_of_static_flows
    print '\n\nStart modify_meter on '+str(int(args[1]))
    url = "http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+str(args[0])+"/flow-node-inventory:table/0/flow/"
    while(out_count<max_num_of_flows_per_user+1):
        s_time = time.time()
        response = requests.request("GET", url+str(int(cur_flow)), data=payload, headers=headers)
        # print url+str(int(cur_flow))+"\n"
        # print str(response.status_code)
        # print (response.text.encode('utf8'))
        if (response.status_code==200):
            if debug == 'ON':
                print 'Time;'+str(time.time()-s_time)+';Request_Type;GET;Switch_Num;'+str(args[0])+';Function_Name;modify_meter1;Flow#;'+str(cur_flow)				
            if ((response.content.find('meter-id>'+str(args[1])+'<')!=-1) or ((response.content.find('meter-id>')==-1) and (response.content.find('type>2054')==-1))):
                #print(cur_flow)
                s_time = time.time()
                print '\nDELTED FLOW#: '+str(cur_flow)
                #print response.content
                response = requests.request("DELETE", url+str(cur_flow), data=payload, headers=headers)
                print 'Time;'+str(time.time()-s_time)+';Request_Type;DELETE;Switch_Num;'+str(args[0])+';Function_Name;modify_meter3;Flow#;'+str(cur_flow)				
            else:
                out_count=out_count+1
        else:
            if debug == 'ON':
                print 'Time;'+str(time.time()-s_time)+';Request_Type;GET;Switch_Num;'+str(args[0])+';Function_Name;modify_meter2;Flow#;'+str(cur_flow)			
            out_count=out_count+1
        
        cur_flow=cur_flow+1
    
    
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:meter/'+str(args[1])
    
    #convert the BW rate to kilobits per sec.
    #print('Mbps='+str(sys.argv[1])) #debuging code
    kbps=int(float(args[2])*8*1000)
    print('kbps rate limit='+str(kbps)) #debuging code

    #xml code to add a meter
    payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<meter xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<meter-id>"+str(args[1])+"</meter-id>\n\
\t<container-name>mymeter</container-name>\n\
\t<meter-name>mymeter</meter-name>\n\
\t<flags>meter-kbps</flags>\n\
\t<meter-band-headers>\n\
\t\t<meter-band-header>\n\
\t\t\t<band-id>0</band-id>\n\
\t\t\t<band-rate>"+str(kbps)+"</band-rate>\n\
\t\t\t<meter-band-types>\n\
\t\t\t\t<flags>ofpmbt-drop</flags>\n\
\t\t\t</meter-band-types>\n\
\t\t\t<band-burst-size>100</band-burst-size>\n\
\t\t\t<drop-rate>"+str(kbps)+"</drop-rate>\n\
\t\t\t<drop-burst-size>1000</drop-burst-size>\n\
\t\t</meter-band-header>\n\
\t</meter-band-headers>\n\
</meter>"
    #print(payload) #debuging code
    #send http put request
    #response = R_ses.put(url, data=payload, headers=headers)
    s_time = time.time()
    response = requests.request("PUT", url, data=payload, headers=headers)
    #print('Status Code ='+str(response.status_code))#debuging code
    if ((response.status_code==201) or (response.status_code==200)):
        print('Meter '+str(args[1])+' was modified to '+str(args[2])+' MB\n')

        # This will cause a temporary down town before switch bws
        # url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:meter/'+str(args[3])
        # payload=''
        # response = requests.request("DELETE", url, data=payload, headers=headers)
        # if ((response.status_code==201) or (response.status_code==200) or (response.status_code==404)):
        #     print('Meter '+str(args[3])+' was deleted.\n')
    else:
        flow_error.append('3')
        print(str(response.text)) #debuging code
        print('ERROR:Unable to modify Meter '+str(args[1])+'\n')
    if debug == 'ON':
        print 'Time;'+str(time.time()-s_time)+';Request_Type;PUT;Switch_Num;'+str(args[0])+';Function_Name;add_meter'
        print 'MODIFY METER TOTAL Time;'+str(time.time()-total_modify_time)



#TODO Finish adding debug timers for all Requests to get the time it takes to configure the switch. By knowing how long each Request takes we can look at the preformance of the CPU, to see how dynamic path and meter configuration preforms better than regular queue tables for flexibilty. Con to the stem is it takes longer to reconfigure, but it provides meter and flow reconfiguration for decisive security actions at the cost of the switches CPU.


def add_flow_with_meter(*args):
    global num_of_static_flows,max_num_of_flows_per_user, headers
    ttttt1= time.time()
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 # the switch name
    #args[1] = 1 #the input port #
    #args[2] = 2 #the ouput port # or group #
    #args[3] = 155.0.0.2 #user ip address (assumed to have a 255.255.255.0 netmask)
    #args[4] = 1.0 #meter #
    #args[5] = 1 #1 means desination address and 0 means source address
    #args[6] = 1 #this indicates which topology to build; inivertently this changes the priority
    #args[7] = 1 #this indicates which base station
    #args[8] = 99 #this indicates whether we need a group arp on this flow or not and if we need just an arp flow

    flow_num=1+max_num_of_flows_per_user*(int(args[4])-1)+num_of_static_flows
    print '\n\n\n\n '+str(int(args[4]))
    # time.sleep(20)
    #the initial GET
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(int(flow_num))
    payload = ""
    #response = R_ses.get(url, data=payload, headers=headers)
    response = requests.request("GET", url, headers=headers, data=payload)
    print("If Response code "+str(response.status_code)+" = 404/200 then it is good") #debuging code	
    
    #determines the next available flow number to use
    while(response.status_code!=404):
        flow_num=flow_num+1
        url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(int(flow_num))
        #response = R_ses.get(url, data=payload, headers=headers)
        response = requests.request("GET", url, headers=headers, data=payload)
        # print "response="+str(response.status_code)+"\n"
        # print str(url)
    print('flow num ------------------------------- '+str(flow_num)+'----------switch # '+str(args[0]))+'----------time:'+str(time.time()-ttttt1)
    #print('CALL FUNCTIONS -----------------------------------------------: '+str(time.time()-ttttt1))
    
    ip_data=[]
    if(args[5]==1):
        ip_part="destination"
        ip_data.append(' ')
        ip_data.append(str(args[3]))
    else:
        ip_part="source"
        ip_data.append(str(args[3]))
        ip_data.append(' ')

    if(args[6]==1):
        priority_part="90"
    else:
        priority_part="80"
        

    
    #add a flow entry with a meter
    #2054 #for arp
    #2048 #0x0800
    print str(args)
    flow_type=['ARP','IPv4']#,'TCP','ICMP']#,'UDP']	
    temp=np.zeros((int(len(flow_type))))
    #flow_rec[0] = flow #
    if(len(args)==9):
        if(int(args[8])==99):
            add_group_arp_with_meter(args[0],args[1],args[2])
            temp[0]=add_flow_arp_for_group_with_meter(args[0],args[1],args[2],args[3],args[4],flow_num,ip_part,int(priority_part))
        elif(int(args[8])==44):
            temp[0]=add_flow_arp_with_meter(args[0],args[1],args[2],args[3],args[4],flow_num,ip_part,int(priority_part)+1)
    
    priority_part = int(priority_part)+int(args[7])

    if(len(args)==9 and int(args[8])==0):
        temp[1]=add_flow_ipv4_with_meter(args[0],args[1],args[2],args[3],args[4],flow_num,ip_part,int(priority_part)-1)
    elif(len(args)==9 and (int(args[8])==44 or int(args[8])==99)):
        priority_part = priority_part
        # DO NOTHING. This is because we are only adding an ARP flow and no other flows.
    elif (len(args)==9 and int(args[8])==55):
        temp[1]=add_flow_ipv4_for_group_with_meter(args[0],args[1],args[2],args[3],args[4],flow_num,ip_part,int(priority_part))
    else:
        temp[1]=add_flow_ipv4_with_meter(args[0],args[1],args[2],args[3],args[4],flow_num,ip_part,int(priority_part))
    #temp[2]=add_flow_tcp_with_meter(args[0],args[1],args[2],args[3],args[4],temp[1]+1,ip_part,int(priority_part))
    #temp[3]=add_flow_icmp_with_meter(args[0],args[1],args[2],args[3],args[4],temp[2]+1,ip_part,int(priority_part))
    #temp[4]=add_flow_udp_with_meter(args[0],args[1],args[2],args[3],args[4],temp[3]+1,ip_part,int(priority_part))
    
    
    
    #flow_rec serves to capture the information regarding each flow into a table format
    #if the number 7 is changed go to the BW_Limiter_API_v013 and change the flow list initializer
    flow_rec=np.empty([len(temp),7], dtype=object)	
    for p in range(0,len(temp)):
        if(temp[p]!=0):
            #print(flow_rec[p]) #debuging code
            flow_rec[p][0] = int(temp[p])
            flow_rec[p][1] = int(priority_part)+(len(temp)-1-p)
            flow_rec[p][2] = str(flow_type[p])
            if (len(args)==9 and int(args[8])==55):
                flow_rec[p][3] = str(args[1])+' --> Group('+str(args[2])+')'
            else:
                flow_rec[p][3] = str(args[1])+' --> '+str(args[2])
            flow_rec[p][4] = int(args[4])
            flow_rec[p][5] = ip_data[0]
            flow_rec[p][6] = ip_data[1]
    # print(flow_rec) #debuging code
    print('DELTA TIME 4 ADD FLOW W/ METER: '+str(time.time()-ttttt1))
    #print('CALL FUNCTIONS TOTAL--------------------------------------------------------: '+str(time.time()-ttttt1))
    return(flow_rec)


def add_flow_arp_with_meter(*args):
    global error
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 # the switch name
    #args[1] = 1 #the input port #
    #args[2] = 2 #the ouput port #
    #args[3] = 155.0.0.2 #user ip address (assumed to have a 255.255.255.0 netmask)
    #args[4] = 1.0 #meter #
    #args[5] = 3 #next flow num to check
    #args[6] = desination #or source
    #args[7] = 2 #priority #

    flow_num=int(args[5])

    #the initial GET
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
    payload = ""
    #response = R_ses.get(url, data=payload, headers=headers)
    response = requests.request("GET", url, data=payload, headers=headers)
    #print(str(response.status_code)) #debuging code	

    #determines the next available flow number to use
    while(response.status_code!=404):
        flow_num=flow_num+1
        url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
        #response = R_ses.get(url, data=payload, headers=headers)
        response = requests.request("GET", url, data=payload, headers=headers)

        #out_part=str(args[2])
        
    if(len(args[6])=='destination'):
        prio_part=str(int(args[7])+1)
    else:
        prio_part=str(args[7])
            
    #add a flow entry with a meter
    payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<flow xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<id>"+str(flow_num)+"</id>\n\
\t<match>\n\
\t\t<ethernet-match>\n\
\t\t\t<ethernet-type>\n\
\t\t\t\t<type>2054</type>\n\
\t\t\t</ethernet-type>\n\
\t\t</ethernet-match>\n\
\t\t<in-port>openflow:"+str(args[0])+":"+str(args[1])+"</in-port>\n\
\t</match>\n\
\t<instructions>\n\
\t\t<instruction>\n\
\t\t\t<order>0</order>\n\
\t\t\t<meter>\n\
\t\t\t\t<meter-id>"+str(int(args[4]))+"</meter-id>\n\
\t\t\t</meter>\n\
\t\t</instruction>\n\
\t\t<instruction>\n\
\t\t\t<order>1</order>\n\
\t\t\t<apply-actions>\n\
\t\t\t\t<action>\n\
\t\t\t\t\t<order>0</order>\n\
\t\t\t\t\t<output-action>\n\
\t\t\t\t\t\t<output-node-connector>"+str(args[2])+"</output-node-connector>\n\
\t\t\t\t\t\t<max-length>65535</max-length>\n\
\t\t\t\t\t</output-action>\n\
\t\t\t\t</action>\n\
\t\t\t</apply-actions>\n\
\t\t</instruction>\n\
\t</instructions>\n\
\t<priority>"+str(int(prio_part))+"</priority>\n\
\t<idle-timeout>0</idle-timeout>\n\
\t<hard-timeout>0</hard-timeout>\n\
\t<cookie>"+str(flow_num+1)+"</cookie>\n\
\t<table_id>0</table_id>\n</flow>"
    #print(payload) #debuging code
    
    if Qiang_ACK == 'FALSE':
        try:
            response = requests.request("PUT", url, data=payload, headers=headers, timeout=0.8)
        except requests.exceptions.Timeout:
            print "Timout occured"
        print('ARP Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
        return(flow_num)
    #response = R_ses.put(url, data=payload, headers=headers)
    response = requests.request("PUT", url, data=payload, headers=headers)
    #print(str(response.status_code)) #debuging code	
    #print(response.text) #debuging code


    if ((response.status_code==200) or (response.status_code==201)):
        #print('ARP Flow entry was added to table 0 slot '+str(flow_num)+'.\n') #debuging code
        print('ARP Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
        return(flow_num)
    else:
        flow_error.append('4')
        print('ERROR:Unable to add arp flow entry to table 0 slot '+str(flow_num)+'.\n')
        return(0)
        
def add_group_arp_with_meter(*args):
    global error
    #--------------------------------------HARD CODED FUNCTION FOR THIS PROJECT--------------------------------------
    
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 # the switch name
    #args[1] = 12 #the input port #
    #args[2] = [3,1] or [3,4,1] # the output ports and the group number being the last number
    # print "ARGs:\n"+str(args)

    group_list = args[2]
    group_num = group_list[len(group_list)-1]

    #the initial GET
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/group/'+str(group_num)
    print url
    
    #add a flow entry with a meter
    payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<group xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<group-id>"+str(group_num)+"</group-id>\n\
\t<group-name>SelectGroup</group-name>\n\
\t<group-type>group-all</group-type>\n\
\t<barrier>false</barrier>\n\
\t<buckets>\n"
    i=0
    while i <len(group_list)-1:
        payload = payload+"\
\t\t<bucket>\n\
\t\t\t<weight>1</weight>\n\
\t\t\t<watch_port>"+str(args[1])+"</watch_port>\n\
\t\t\t<watch_group>4294967295</watch_group>\n\
\t\t\t<action>\n\
\t\t\t\t<output-action>\n\
\t\t\t\t\t<output-node-connector>"+str(group_list[i])+"</output-node-connector>\n\
\t\t\t\t</output-action>\n\
\t\t\t\t<order>"+str(i+1)+"</order>\n\
\t\t\t</action>\n\
\t\t\t<bucket-id>"+str(i+1)+"</bucket-id>\n\
\t\t</bucket>\n"
        i=i+1
    
    payload = payload+"\
\t</buckets>\n</group>"
    #print(payload) #debuging code
    ttttt= time.time()
    #response = R_ses.put(url, data=payload, headers=headers)

    # if Qiang_ACK == 'FALSE':
    # 	try:
    # 		response = requests.request("PUT", url, data=payload, headers=headers, timeout=1)
    # 	except requests.exceptions.Timeout:
    # 		print "Timout occured"
    # 	print('ARP Group Flow entry was added.\n')

    response = requests.request("PUT", url, data=payload, headers=headers)
    print('DELTA TIME 4 GROUP ARP W/ METER: '+str(time.time()-ttttt))
    #print(str(response.status_code)) #debuging code	
    #print(response.text) #debuging 

    if ((response.status_code==200) or (response.status_code==201)):
        #print('ARP Flow entry was added to table 0 slot '+str(flow_num)+'.\n') #debuging code
        print('ARP Group Flow entry was added.\n')
    else:
        flow_error.append('5')
        print('ERROR:Unable to add arp group flow entry.\n')

def add_flow_arp_for_group_with_meter(*args):
    global error
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 # the switch name
    #args[1] = 1 #the input port # 
    #args[2] = 2 #the ouput port # or array of #'s
    #args[3] = 155.0.0.2 #user ip address (assumed to have a 255.255.255.0 netmask)
    #args[4] = 1.0 #meter #
    #args[5] = 3 #next flow num to check
    #args[6] = desination #or source
    #args[7] = 2 #priority #

    flow_num=args[5]

    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
        
    if(len(args[6])=='destination'):
        prio_part=str(int(args[7])+1)
    else:
        prio_part=str(args[7])
        
    group_list=args[2]
    group_num=group_list[len(group_list)-1]

    #add a flow entry with a meter
    payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<flow xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<id>"+str(flow_num)+"</id>\n\
\t<match>\n\
\t\t<ethernet-match>\n\
\t\t\t<ethernet-type>\n\
\t\t\t\t<type>2054</type>\n\
\t\t\t</ethernet-type>\n\
\t\t</ethernet-match>\n\
\t\t<in-port>openflow:"+str(args[0])+":"+str(args[1])+"</in-port>\n\
\t</match>\n\
\t<instructions>\n\
\t\t<instruction>\n\
\t\t\t<order>0</order>\n\
\t\t\t<meter>\n\
\t\t\t\t<meter-id>"+str(int(args[4]))+"</meter-id>\n\
\t\t\t</meter>\n\
\t\t</instruction>\n\
\t\t<instruction>\n\
\t\t\t<order>1</order>\n\
\t\t\t<apply-actions>\n\
\t\t\t\t<action>\n\
\t\t\t\t\t<order>0</order>\n\
\t\t\t\t\t<group-action>\n\
\t\t\t\t\t\t<group-id>"+str(group_num)+"</group-id>\n\
\t\t\t\t\t</group-action>\n\
\t\t\t\t</action>\n\
\t\t\t</apply-actions>\n\
\t\t</instruction>\n\
\t</instructions>\n\
\t<priority>"+str(int(prio_part))+"</priority>\n\
\t<idle-timeout>0</idle-timeout>\n\
\t<hard-timeout>0</hard-timeout>\n\
\t<cookie>"+str(flow_num+1)+"</cookie>\n\
\t<table_id>0</table_id>\n</flow>"
    #print(payload) #debuging code
    
    ttttt= time.time()
    if Qiang_ACK == 'FALSE':
        try:
            response = requests.request("PUT", url, data=payload, headers=headers, timeout=0.8)
        except requests.exceptions.Timeout:
            print "Timout occured"
        print('Group ARP Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
        return(flow_num)
    
    #response = R_ses.put(url, data=payload, headers=headers)
    response = requests.request("PUT", url, data=payload, headers=headers)
    print('DELTA TIME 4 ARP 4 GROUP: '+str(time.time()-ttttt))
    #print(str(response.status_code)) #debuging code	
    #print(response.text) #debuging code
    
    if ((response.status_code==200) or (response.status_code==201)):
        #print('ARP Flow entry was added to table 0 slot '+str(flow_num)+'.\n') #debuging code
        print('Group ARP Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
        return(flow_num)
    else:
        flow_error.append('6')
        print('ERROR:Unable to add group arp flow entry to table 0 slot '+str(flow_num)+'.\n')
        return(0)


def add_flow_ipv4_for_group_with_meter(*args):
    global error
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 # the switch name
    #args[1] = 1 #the input port #
    #args[2] = 2 #the group #
    #args[3] = 155.0.0.2 #user ip address (assumed to have a 255.255.255.0 netmask)
    #args[4] = 1.0 #meter #
    #args[5] = 3 #next flow num to check
    #args[6] = desination #or source
    #args[7] = 2 #priority #
    
    flow_num=int(args[5])

    #the initial GET
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
    payload = ""
    #response = R_ses.get(url, data=payload, headers=headers)
    response = requests.request("GET", url, data=payload, headers=headers)
    #print(str(response.status_code)) #debuging code	

    #determines the next available flow number to use
    while(response.status_code!=404):
        flow_num=flow_num+1
        url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
        #response = R_ses.get(url, data=payload, headers=headers)
        response = requests.request("GET", url, data=payload, headers=headers)
  
    #add a flow entry with a meter
    payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<flow xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<id>"+str(flow_num)+"</id>\n\
\t<match>\n\
\t\t<ethernet-match>\n\
\t\t\t<ethernet-type>\n\
\t\t\t\t<type>2048</type>\n\
\t\t\t</ethernet-type>\n\
\t\t</ethernet-match>\n\
\t\t<in-port>openflow:"+str(args[0])+":"+str(args[1])+"</in-port>\n\
\t\t<ipv4-"+str(args[6])+">"+str(args[3])+"/32</ipv4-"+str(args[6])+">\n\
\t</match>\n\
\t<instructions>\n\
\t\t<instruction>\n\
\t\t\t<order>0</order>\n\
\t\t\t<meter>\n\
\t\t\t\t<meter-id>"+str(int(args[4]))+"</meter-id>\n\
\t\t\t</meter>\n\
\t\t</instruction>\n\
\t\t<instruction>\n\
\t\t\t<order>1</order>\n\
\t\t\t<apply-actions>\n\
\t\t\t\t<action>\n\
\t\t\t\t\t<order>0</order>\n\
\t\t\t\t\t<group-action>\n\
\t\t\t\t\t\t<group-id>"+str(args[2])+"</group-id>\n\
\t\t\t\t\t</group-action>\n\
\t\t\t\t</action>\n\
\t\t\t</apply-actions>\n\
\t\t</instruction>\n\
\t</instructions>\n\
\t<priority>"+str(int(args[7]))+"</priority>\n\
\t<idle-timeout>0</idle-timeout>\n\
\t<hard-timeout>0</hard-timeout>\n\
\t<cookie>"+str(flow_num+1)+"</cookie>\n\
\t<table_id>0</table_id>\n</flow>"
    # print '\n\n\n'+str(payload) #debuging code
    
    if Qiang_ACK == 'FALSE':
        try:
            response = requests.request("PUT", url, data=payload, headers=headers, timeout=0.03)
        except requests.exceptions.Timeout:
            print "Timout occured"
        print('Group IPv4 Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
        return(flow_num)

    ttttt= time.time()
    #response = R_ses.put(url, data=payload, headers=headers)
    response = requests.request("PUT", url, data=payload, headers=headers)
    print('DELTA TIME 4 Group IPV4: '+str(time.time()-ttttt))
    #print(str(response.status_code)) #debuging code	
    #print(response.text) #debuging code

    if ((response.status_code==200) or (response.status_code==201)):
        #print('IPv4 Flow entry was added to table 0 slot '+str(flow_num)+'.\n') #debuging code
        print('Group IPv4 Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
        return(flow_num)
    else:
        flow_error.append('7')
        # print str(response.status_code)+'\n'
        print('ERROR:Unable to add group ipv4 flow entry to table 0 slot '+str(flow_num)+'.\n')
        return(0)


def add_flow_ipv4_with_meter(*args):
    global error
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 # the switch name
    #args[1] = 1 #the input port #
    #args[2] = 2 #the ouput port #
    #args[3] = 155.0.0.2 #user ip address (assumed to have a 255.255.255.0 netmask)
    #args[4] = 1.0 #meter #
    #args[5] = 3 #next flow num to check
    #args[6] = desination #or source
    #args[7] = 2 #priority #
    
    flow_num=int(args[5])

    #the initial GET
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
    payload = ""
    #response = R_ses.get(url, data=payload, headers=headers)
    response = requests.request("GET", url, data=payload, headers=headers)
    #print(str(response.status_code)) #debuging code	

    #determines the next available flow number to use
    while(response.status_code!=404):
        flow_num=flow_num+1
        url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
        #response = R_ses.get(url, data=payload, headers=headers)
        response = requests.request("GET", url, data=payload, headers=headers)
  
    #add a flow entry with a meter
    payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<flow xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<id>"+str(flow_num)+"</id>\n\
\t<match>\n\
\t\t<ethernet-match>\n\
\t\t\t<ethernet-type>\n\
\t\t\t\t<type>2048</type>\n\
\t\t\t</ethernet-type>\n\
\t\t</ethernet-match>\n\
\t\t<in-port>openflow:"+str(args[0])+":"+str(args[1])+"</in-port>\n\
\t\t<ipv4-"+str(args[6])+">"+str(args[3])+"/32</ipv4-"+str(args[6])+">\n\
\t</match>\n\
\t<instructions>\n\
\t\t<instruction>\n\
\t\t\t<order>0</order>\n\
\t\t\t<meter>\n\
\t\t\t\t<meter-id>"+str(int(args[4]))+"</meter-id>\n\
\t\t\t</meter>\n\
\t\t</instruction>\n\
\t\t<instruction>\n\
\t\t\t<order>1</order>\n\
\t\t\t<apply-actions>\n\
\t\t\t\t<action>\n\
\t\t\t\t\t<order>0</order>\n\
\t\t\t\t\t<output-action>\n\
\t\t\t\t\t\t<output-node-connector>"+str(args[2])+"</output-node-connector>\n\
\t\t\t\t\t\t<max-length>65535</max-length>\n\
\t\t\t\t\t</output-action>\n\
\t\t\t\t</action>\n\
\t\t\t</apply-actions>\n\
\t\t</instruction>\n\
\t</instructions>\n\
\t<priority>"+str(int(args[7]))+"</priority>\n\
\t<idle-timeout>0</idle-timeout>\n\
\t<hard-timeout>0</hard-timeout>\n\
\t<cookie>"+str(flow_num+1)+"</cookie>\n\
\t<table_id>0</table_id>\n</flow>"
    # print '\n\n\n'+str(payload) #debuging code
    
    if Qiang_ACK == 'FALSE':
        try:
            response = requests.request("PUT", url, data=payload, headers=headers, timeout=0.03)
        except requests.exceptions.Timeout:
            print "Timout occured"
        print('IPv4 Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
        return(flow_num)

    ttttt= time.time()
    #response = R_ses.put(url, data=payload, headers=headers)
    response = requests.request("PUT", url, data=payload, headers=headers)
    print('DELTA TIME 4 IPV4: '+str(time.time()-ttttt))
    #print(str(response.status_code)) #debuging code	
    #print(response.text) #debuging code

    if ((response.status_code==200) or (response.status_code==201)):
        #print('IPv4 Flow entry was added to table 0 slot '+str(flow_num)+'.\n') #debuging code
        print('IPv4 Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
        return(flow_num)
    else:
        flow_error.append('7')
        # print str(response.status_code)+'\n'
        print('ERROR:Unable to add ipv4 flow entry to table 0 slot '+str(flow_num)+'.\n')
        return(0)

def add_flow_tcp_with_meter(*args):
    global error
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 # the switch name
    #args[1] = 1 #the input port #
    #args[2] = 2 #the ouput port #
    #args[3] = 155.0.0.2 #user ip address (assumed to have a 255.255.255.0 netmask)
    #args[4] = 1.0 #meter #
    #args[5] = 3 #next flow num to check
    #args[6] = desination #or source
    #args[7] = 2 #priority #

    flow_num=int(args[5])

    #the initial GET
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
    payload = ""
    #response = R_ses.get(url, data=payload, headers=headers)
    response = requests.request("GET", url, data=payload, headers=headers)
    #print(str(response.status_code)) #debuging code	
    #ttttt3= time.time()
    #determines the next available flow number to use
    while(response.status_code!=404):
        flow_num=flow_num+1
        url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
        #response = R_ses.get(url, data=payload, headers=headers)
        response = requests.request("GET", url, data=payload, headers=headers)
    #print('time for search-----------------------------'+str(time.time()-ttttt3))
    #add a flow entry with a meter
    payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<flow xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<id>"+str(flow_num)+"</id>\n\
\t<match>\n\
\t\t<ethernet-match>\n\
\t\t\t<ethernet-type>\n\
\t\t\t\t<type>2048</type>\n\
\t\t\t</ethernet-type>\n\
\t\t</ethernet-match>\n\
\t\t<ip-match>\n\
\t\t\t<ip-protocol>6</ip-protocol>\n\
\t\t</ip-match>\n\
\t\t<in-port>openflow:"+str(args[0])+":"+str(args[1])+"</in-port>\n\
\t\t<ipv4-"+str(args[6])+">"+str(args[3])+"/32</ipv4-"+str(args[6])+">\n\
\t</match>\n\
\t<instructions>\n\
\t\t<instruction>\n\
\t\t\t<order>0</order>\n\
\t\t\t<meter>\n\
\t\t\t\t<meter-id>"+str(int(args[4]))+"</meter-id>\n\
\t\t\t</meter>\n\
\t\t</instruction>\n\
\t\t<instruction>\n\
\t\t\t<order>1</order>\n\
\t\t\t<apply-actions>\n\
\t\t\t\t<action>\n\
\t\t\t\t\t<order>0</order>\n\
\t\t\t\t\t<output-action>\n\
\t\t\t\t\t\t<output-node-connector>"+str(args[2])+"</output-node-connector>\n\
\t\t\t\t\t\t<max-length>65535</max-length>\n\
\t\t\t\t\t</output-action>\n\
\t\t\t\t</action>\n\
\t\t\t</apply-actions>\n\
\t\t</instruction>\n\
\t</instructions>\n\
\t<priority>"+str(int(args[7]))+"</priority>\n\
\t<idle-timeout>0</idle-timeout>\n\
\t<hard-timeout>0</hard-timeout>\n\
\t<cookie>"+str(flow_num+1)+"</cookie>\n\
\t<table_id>0</table_id>\n</flow>"
    #print(payload) #debuging code
    
    ttttt= time.time()
    response = R_ses.put(url, data=payload, headers=headers)
    response = requests.request("PUT", url, data=payload, headers=headers)
    print('DELTA TIME 4 TCP: '+str(time.time()-ttttt))
    #print(str(response.status_code)) #debuging code	
    #print(response.text) #debuging code
    ttttt2= time.time()
    if ((response.status_code==200) or (response.status_code==201)):
        #print('TCP Flow entry was added to table 0 slot '+str(flow_num)+'.\n') #debuging code
        #print('TCP Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
        #print('time for response_-------------------------------------'+str(time.time()-ttttt2))
        return(flow_num)
    else:
        flow_error.append('8')
        #print('time for rsponse_-------------------------------------'+str(time.time()-ttttt2))
        print('ERROR:Unable to add tcp flow entry to table 0 slot '+str(flow_num)+'.\n')
        return(0)
    
def add_flow_icmp_with_meter(*args):
    global error 
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 # the switch name
    #args[1] = 1 #the input port #
    #args[2] = 2 #the ouput port #
    #args[3] = 155.0.0.2 #user ip address (assumed to have a 255.255.255.0 netmask)
    #args[4] = 1.0 #meter #
    #args[5] = 3 #next flow num to check
    #args[6] = desination #or source
    #args[7] = 2 #priority #

    flow_num=int(args[5])

    #the initial GET
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
    payload = ""
    #response = R_ses.get(url, data=payload, headers=headers)
    response = requests.request("GET", url, data=payload, headers=headers)
    #print(str(response.status_code)) #debuging code	

    #determines the next available flow number to use
    while(response.status_code!=404):
        flow_num=flow_num+1
        url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
        #response = R_ses.get(url, data=payload, headers=headers)
        response = requests.request("GET", url, data=payload, headers=headers)
  
    #add a flow entry with a meter
    payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<flow xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<id>"+str(flow_num)+"</id>\n\
\t<match>\n\
\t\t<ethernet-match>\n\
\t\t\t<ethernet-type>\n\
\t\t\t\t<type>2048</type>\n\
\t\t\t</ethernet-type>\n\
\t\t</ethernet-match>\n\
\t\t<ip-match>\n\
\t\t\t<ip-protocol>1</ip-protocol>\n\
\t\t</ip-match>\n\
\t\t<in-port>openflow:"+str(args[0])+":"+str(args[1])+"</in-port>\n\
\t\t<ipv4-"+str(args[6])+">"+str(args[3])+"/32</ipv4-"+str(args[6])+">\n\
\t</match>\n\
\t<instructions>\n\
\t\t<instruction>\n\
\t\t\t<order>0</order>\n\
\t\t\t<meter>\n\
\t\t\t\t<meter-id>"+str(int(args[4]))+"</meter-id>\n\
\t\t\t</meter>\n\
\t\t</instruction>\n\
\t\t<instruction>\n\
\t\t\t<order>1</order>\n\
\t\t\t<apply-actions>\n\
\t\t\t\t<action>\n\
\t\t\t\t\t<order>0</order>\n\
\t\t\t\t\t<output-action>\n\
\t\t\t\t\t\t<output-node-connector>"+str(args[2])+"</output-node-connector>\n\
\t\t\t\t\t\t<max-length>65535</max-length>\n\
\t\t\t\t\t</output-action>\n\
\t\t\t\t</action>\n\
\t\t\t</apply-actions>\n\
\t\t</instruction>\n\
\t</instructions>\n\
\t<priority>"+str(int(args[7]))+"</priority>\n\
\t<idle-timeout>0</idle-timeout>\n\
\t<hard-timeout>0</hard-timeout>\n\
\t<cookie>"+str(flow_num+1)+"</cookie>\n\
\t<table_id>0</table_id>\n</flow>"
    #print(payload) #debuging code
    
    response = requests.request("PUT", url, data=payload, headers=headers)
    #print(str(response.status_code)) #debuging code	
    #print(response.text) #debuging code

    if ((response.status_code==200) or (response.status_code==201)):
        #print('TCP Flow entry was added to table 0 slot '+str(flow_num)+'.\n') #debuging code
        print('ICMP Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
        return(flow_num)
    else:
        flow_error.append('9')
        print('ERROR:Unable to add icmp flow entry to table 0 slot '+str(flow_num)+'.\n')
        return(0)

def add_flow_udp_with_meter(*args):
    global error
    #print(args) #debuging code
    #NOTES:
    #args[0] = 106225813884652 or 106225813884040 # the switch name
    #args[1] = 1 #the input port #
    #args[2] = 2 #the ouput port #
    #args[3] = 155.0.0.2 #user ip address (assumed to have a 255.255.255.0 netmask)
    #args[4] = 1.0 #meter #
    #args[5] = 3 #next flow num to check
    #args[6] = desination #or source
    #args[7] = 2 #priority #

    flow_num=int(args[5])

    #the initial GET
    url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
    payload = ""
    response = requests.request("GET", url, data=payload, headers=headers)
    #print(str(response.status_code)) #debuging code	

    #determines the next available flow number to use
    while(response.status_code!=404):
        flow_num=flow_num+1
        url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'+str(flow_num)
        response = requests.request("GET", url, data=payload, headers=headers)
  
    #add a flow entry with a meter
    payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<flow xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<id>"+str(flow_num)+"</id>\n\
\t<match>\n\
\t\t<ethernet-match>\n\
\t\t\t<ethernet-type>\n\
\t\t\t\t<type>2048</type>\n\
\t\t\t</ethernet-type>\n\
\t\t</ethernet-match>\n\
\t\t<ip-match>\n\
\t\t\t<ip-protocol>17</ip-protocol>\n\
\t\t</ip-match>\n\
\t\t<in-port>openflow:"+str(args[0])+":"+str(args[1])+"</in-port>\n\
\t\t<ipv4-"+str(args[6])+">"+str(args[3])+"/32</ipv4-"+str(args[6])+">\n\
\t</match>\n\
\t<instructions>\n\
\t\t<instruction>\n\
\t\t\t<order>0</order>\n\
\t\t\t<meter>\n\
\t\t\t\t<meter-id>"+str(int(args[4]))+"</meter-id>\n\
\t\t\t</meter>\n\
\t\t</instruction>\n\
\t\t<instruction>\n\
\t\t\t<order>1</order>\n\
\t\t\t<apply-actions>\n\
\t\t\t\t<action>\n\
\t\t\t\t\t<order>0</order>\n\
\t\t\t\t\t<output-action>\n\
\t\t\t\t\t\t<output-node-connector>"+str(args[2])+"</output-node-connector>\n\
\t\t\t\t\t\t<max-length>65535</max-length>\n\
\t\t\t\t\t</output-action>\n\
\t\t\t\t</action>\n\
\t\t\t</apply-actions>\n\
\t\t</instruction>\n\
\t</instructions>\n\
\t<priority>"+str(int(args[7]))+"</priority>\n\
\t<idle-timeout>0</idle-timeout>\n\
\t<hard-timeout>0</hard-timeout>\n\
\t<cookie>"+str(flow_num+1)+"</cookie>\n\
\t<table_id>0</table_id>\n</flow>"
    #print(payload) #debuging code
    
    #response = R_ses.put(url, data=payload, headers=headers)
    response = requests.request("PUT", url, data=payload, headers=headers)
    #print(str(response.status_code)) #debuging code	
    #print(response.text) #debuging code

    if ((response.status_code==200) or (response.status_code==201)):
        #print('TCP Flow entry was added to table 0 slot '+str(flow_num)+'.\n') #debuging code
        print('UDP Flow entry was added to connect port '+str(args[1])+' to '+str(args[2])+'.\n')
        return(flow_num)
    else:
        flow_error.append('10')
        print('ERROR:Unable to add udp flow entry to table 0 slot '+str(flow_num)+'.\n')

def add_f_l(*args):
    #NOTES:
    #args[0] = f_l # the flow entry lis
    #args[1] = temp #the flow entry data
    
    # This allows add_f_l to add multiple flows at once
    flow_entry_counter=0
    p=0
    temp = args[0]
    
    # Goes through and finds an empty row(meaning a row that has a zero or 'NONE' in its first column) to store the flow data in
    while p<len(temp) and flow_entry_counter<len(args[1]):
        if debug=='ON':
            print "---------"+str(flow_entry_counter)
        if temp[p][0]==0 or temp[p][0]==None:
            # print str(args[1][0])
            # print str(args[1][1])
            # goes through all of the flow list for each flow entry
            while flow_entry_counter<len(args[1]):
                if args[1][flow_entry_counter][0]==None: 
                    # print str(args[1][flow_entry_counter])
                    flow_entry_counter=flow_entry_counter+1
                else:
                    break
            if flow_entry_counter<len(args[1]):
                temp[p] = args[1][flow_entry_counter]
                flow_entry_counter=flow_entry_counter+1
            else: 
                break
            if debug=='ON':
                print str(flow_entry_counter)
        p=p+1
    return(temp)

def modify_f_l(*args):
    
    #NOTES:
    #args[0] = f_l # the flow entry list
    #args[1] = 1.0 #meter #
    #args[2] = 1 or 0 #this is the future topology # of the user
    #ttttt=time.time()
    temp = args[0]

    emp = np.empty([1,len(temp[0][0])], dtype=object)

    #print (args)# debuging code
    #goes through and finds any row with the meter 'args[1]' to remove the flow data from my f_l database

    # print '\n\n\n'
    # print str(len(temp[0])) # This outputs the # of switches
    # print '\n\n\n'
    # print str(len(temp[0][0])) # This outputs the # of flows
    # print '\n\n\n'
    # print str(len(temp[0][0][0]))  # This outputs the # of items on each row. This currently static to 7 items
    # print '\n\n\n'
                                        # of switches
    for s in range(0,len(temp)):
        print "s value: "+str(s)
                                            # of flows
        for f in range(0,len(temp[0])):
            # print str(len(temp[s][f]))  # This outputs the # of items on each row. This currently static to 7 items
            # print '\n\n\n'
            # print str(temp[s][f][4])
            # print '\n\n\n'
            # print str(int(args[1]))
            if(temp[s][f][4]==int(args[1])): #and (int(temp[s][f][4])!=0)):
                temp[s][f]=emp
    #print('CALL MODIFY_F_L --------------------------------------------: '+str(time.time()-ttttt))
    
    return(temp)
    
def output_flow(*args):
    b1_u=args[0]
    b2_u=args[1]
    nou=len(b1_u)+len(b2_u)+1
    switch=args[2]
    f_l=args[3]
    top_num=args[4]

    #outputs the current flow configurations on each switch to a csv file
    try:
        os.remove('flow_entries_topology'+str(top_num)+'.csv')
    except:
        print "Their are no previous f_l files."
    f1 = open('flow_entries_topology'+str(top_num)+'.csv','w')
    f1.truncate()
    writer = csv.writer(f1)
    writer.writerow(['Topology #','Switch #','Flow #','Priority #','Protocol','Action','Meter #','Source Add.','Destination Add.'])
    # b=[]
    # b.extend(b1_u)
    # b.extend(b2_u)
    for l in range(0,nou):
        for s in range(0,len(switch)):
            for f in range(0,len(f_l[l][top_num[l]][s])):
                #goes through all of the flows for user 'u' in all of the switches
                # q=0
            # while(q<len(f_l[l][top_num[l]][s][f])):
                if debug=='ON':
                    print str(f) + ' ' + str(s) + ' ' + str(l)
                # print str(len(f_l[l][top_num[l]][s]))
                # print str(f_l[l][top_num[l]][s][f])
                if f_l[l][top_num[l]][s][f][0]!=None:
                    
                    # print str(f_l[l][top_num[l]][p][q])
                    # if(int(f_l[l][top_num[l]][p][q][0])!=0):
                    a=[]
                    a.extend([str(top_num[l]),s+1])
                    if debug=='ON':
                        # This prints the data being stored in the excel sheet
                        print str(f_l[l][top_num[l]][s][f])

                    a.extend(f_l[l][top_num[l]][s][f])
                    writer.writerow(a)
                    # else:
                    #     break
                else:
                    # print str(q) + ' ' + str(p)
                    # print str(f_l[l][top_num[l]][p][q])
                    break
                    # q=q+1
    f1.close()

def create_topology(*args):
    global max_num_of_flows_per_user, s_nums, ports
    #print(args) #debuging code
    b1_u = args[0]
    b2_u = args[1]
    f_l = args[2]	#with the designated topology
    switch = args[3]
    m_l = args[4] #with the designated topology
    top_num = args[5] #with the designated topology

    ttttt1=time.time()
    ender=0
    ttttt=time.time()

    #TODO Dont forget to set the two topology variables s_num and ports

    
    # Creats the ARP connections
    # b_num = 0
    u_index=len(b1_u)+len(b2_u)
    
    if top_num[u_index]==0 or top_num[u_index]==-1:

        # for path_num in [0,1]: # <== This variable contains the current path #
        #     i=0
            # By setting the top_num for the ARP flows to 1 they are only created once
            # during the init of the network
        if top_num[u_index]==0:
            top_num[u_index]=1
            # while i<len(s_nums[path_num]):
                # i indices 0,2,4

                # mapping from INPUT ports[i][0] to OUTPUT ports[i][1]
                #the ip address for an ARP flow does not matteeer but the meter does
                # print str(len(m_l))
                # print '\n'
                # print str(len(top_num))
                # print '\n'
                # print str(top_num[u_index])
                # print str(m_l[u_index][top_num[u_index]][s_nums[i]][0])

                # need to write some code to determine if their is any port within a switch that sends ARP's 
                # to more than 1 other port. If so then apply a group flow instead of a normal flow


                # Determines if their are any grouping flows required
                # for p in range(0,len(s_nums)-1): # <== path number
                #     for sn in range(0,len(s_nums[p])) 
                #         temp_p=p+1 #<== this is intially the 2 path
                #         while temp_p<len(s_nums):
                #             temp_sn=0 #<== this is the switch number within the temp_p path
                #             while temp_sn<=len(s_nums[temp_p]):
                #                 if s_nums[p][sn] == s_nums[temp_p][temp_sn]:
                #                     #if another path uses the same switch

                #                     cn=0 #<== connection eg. [12,1]
                #                     while cn < len(ports[p][sn]):
                #                         temp_cn=0 #<== this is intially the 2nd paths connections eg. [12,3]
                #                         while temp_cn < len(ports[temp_p][temp_sn])
                                            
                #                             if ports[p][sn][0] != ports[temp_p][temp_sn][0] and ports[p][sn][1] == ports[temp_p][temp_sn][1]
                #                                 # eg. [12,1] and [11,1]
                #                             elif ports[p][sn][0] == ports[temp_p][temp_sn][0] and ports[p][sn][1] != ports[temp_p][temp_sn][1]
                #                                 # eg. [12,1] and [12,2]
                #                             elif ports[p][sn][0] == ports[temp_p][temp_sn][0] and ports[p][sn][1] == ports[temp_p][temp_sn][1]:
                #                                 # eg. [12,1] and [12,1]
                #                             temp_cn=temp_cn+1
                #                         cn=cn+1
                #                 temp_sn=temp_sn+1
                #             temp_p=temp_p+1top_num[u_index]
        ############################################################# Determines if their are any grouping flows required ############################START
        arp_list = []
        # arp_list [][switch #]
        #            [input port]
        #            [output port]
        sug_list = []
        #0 sug_list [][T(1) or F(0) should you group]      
        #1            [group #]
        #2            [switch #]
        #3            [input port #]
        #4            [output port #]
        #5            [defines this path as the users sending data (source=0) or the users recieving data (destination=1)]
        #6            [path #'s]

        arp_counter=0
        for p in range(len(s_nums)): # <== path number
            for sn in range(len(s_nums[p])): # <== switch numbers
                for cn in range(len(ports[p][sn])):
                    # eg adds the 12==>1 route
                    arp_list.append([s_nums[p][sn],ports[p][sn][cn][0],ports[p][sn][cn][1],p])

                    # eg adds the 1==>12 route
                    arp_list.append([s_nums[p][sn],ports[p][sn][cn][1],ports[p][sn][cn][0],p])

                    print str(arp_list[arp_counter-2])
                    print str(arp_list[arp_counter-1])

                    sug_list.append([-1,-1,-1,-1,-1,0,[p]])
                    sug_list.append([-1,-1,-1,-1,-1,1,[p]])
                    
        
        
        #NOTE
        # if sug_list[][0] == 0 and sug_list[][1] == 0 this means create a normal ipv4 with 1 input port and 1 output port
        # if sug_list[][0] > 0 and sug_list[][1] > 0 this means create a group ipv4 with 1 input port and multiple output port
        # if sug_list[][0] == -1 and sug_list[][1] == -1 this means do not create a ipv4 because a group ipv4 has taken into account this route

        # This loop goes through and checks every other route to the current route to see if their
        # is any other route using the same input port with a different/same output port.
        # #TODO this function has a high big O value
        arp_counter=0
        group_num_counter=[1 for x in range(len(switch))]
        while arp_counter<len(arp_list):
            if arp_list[arp_counter][0]!=(-1):
                group_list=[arp_list[arp_counter][2]]

                temp_count=arp_counter+1
                while temp_count<len(arp_list):
                    if arp_list[temp_count][0]!=(-1):

                        if (arp_list[arp_counter][0] == arp_list[temp_count][0] and
                        arp_list[arp_counter][1] == arp_list[temp_count][1] and
                        arp_list[arp_counter][2] == arp_list[temp_count][2]):
                            # eg. [12,1] and [12,1]
                            # this will prevent redundant arp flows
                            arp_list[temp_count][0]=-1
                            # this will add
                            sug_list[arp_counter][6].append(arp_list[temp_count][3])
                            sug_list[temp_count][6]=[-1]

                        elif (arp_list[arp_counter][0] == arp_list[temp_count][0] and
                        arp_list[arp_counter][1] == arp_list[temp_count][1] and
                        arp_list[arp_counter][2] != arp_list[temp_count][2]):
                            # eg. [12,1] and [12,2]
                            # this will collect all of the ports that need to be added in this grouping arp
                            group_list.append(arp_list[temp_count][2])
                            arp_list[temp_count][0]=-1
                            # print "temp_counter = "+str(temp_count)+" \narp_counter = "+str(arp_counter)
                            # print "len(sug_list)= "+str(len(sug_list))
                            # print "len(arp_list)= "+str(len(arp_list))
                            # print "\n sug_list[temp_count]= "+str(sug_list[temp_count])
                            # print "sug_list[temp_count][3] = "+str(sug_list[temp_count][3])+"\n"
                            # print "sug_list[arp_counter][3] = "+str(sug_list[arp_counter][3])
                            sug_list[arp_counter][6].append(arp_list[temp_count][3])
                            sug_list[temp_count][6]=[-1]

                    temp_count=temp_count+1
                # print arp_list[0]
                # adds the group number to the end of the group list
                group_list.append(group_num_counter[arp_list[arp_counter][0]])
                group_num_counter[arp_list[arp_counter][0]]=group_num_counter[arp_list[arp_counter][0]]+1

                switch_num = arp_list[arp_counter][0]
                
                # print "CURRENT FLOW: "+str(arp_list[arp_counter])
                # print "Group List: \n"+str(group_list)
                # print "Updated FLow List: "+str(arp_list)
                # time.sleep(10)
                if len(group_list)>2:
                    if top_num[u_index]==1:
                        temp = add_flow_with_meter(switch[arp_list[arp_counter][0]],arp_list[arp_counter][1],group_list,'0.0.0.0',m_l[u_index][top_num[u_index]][switch_num][0],1,top_num[u_index],0,99)
                        f_l[u_index][top_num[u_index]][switch_num] = add_f_l(f_l[u_index][top_num[u_index]][switch_num],temp)
                    sug_list[arp_counter][0]=1
                    sug_list[arp_counter][1]=group_list[len(group_list)-1]
                    sug_list[arp_counter][2]=arp_list[arp_counter][0]
                    sug_list[arp_counter][3]=arp_list[arp_counter][1]
                    sug_list[arp_counter][4]=arp_list[arp_counter][2]
                elif len(group_list)==2:

                    if top_num[u_index]==1:
                        temp = add_flow_with_meter(switch[arp_list[arp_counter][0]],arp_list[arp_counter][1],group_list[0],'0.0.0.0',m_l[u_index][top_num[u_index]][switch_num][0],1,top_num[u_index],0,44)
                        f_l[u_index][top_num[u_index]][switch_num] = add_f_l(f_l[u_index][top_num[u_index]][switch_num],temp)
                    sug_list[arp_counter][0]=0
                    sug_list[arp_counter][1]=0
                    sug_list[arp_counter][2]=arp_list[arp_counter][0]
                    sug_list[arp_counter][3]=arp_list[arp_counter][1]
                    sug_list[arp_counter][4]=arp_list[arp_counter][2]
                
                arp_list[arp_counter][0]=-1
            
            print "\n\n\n ARP #"+str(arp_counter)+"\n"
            # time.sleep(1)
            arp_counter=arp_counter+1

        top_num[u_index]=-1
                # time.sleep(6000)
                # p=0
                # while p<len(ports[path_num][i]):
                #     # p indices [12,1]
                #     temp = add_flow_with_meter(switch[s_nums[path_num][i]],ports[path_num][i][p][0],ports[path_num][i][p][1],'0.0.0.0',m_l[u_index][top_num[u_index]][s_nums[path_num][i]][0],0,top_num[u_index],b_num,44)
                #     # print str(temp)
                #     f_l[u_index][top_num[u_index]][s_nums[path_num][i]] = add_f_l(f_l[u_index][top_num[u_index]][s_nums[path_num][i]],temp)

                #     # mapping from OUTPUT ports[i][1] to INPUT ports[i][0]
                #     temp = add_flow_with_meter(switch[s_nums[path_num][i]],ports[path_num][i][p][1],ports[path_num][i][p][0],'0.0.0.0',m_l[u_index][top_num[u_index]][s_nums[path_num][i]][0],1,top_num[u_index],b_num,44)
                #     # print str(temp)
                #     f_l[u_index][top_num[u_index]][s_nums[path_num][i]] = add_f_l(f_l[u_index][top_num[u_index]][s_nums[path_num][i]],temp)
                #     p=p+1
                # i=i+1
    # flow_thread=[]
    print "Sug_List \n"
    for x in range(len(sug_list)):
        print str(x)+" "+str(sug_list[x])

    # print "(0 in sug_list[0][3]) = "+str(0 in sug_list[0][3])
    # print "(1 in sug_list[0][3]) = "+str(1 in sug_list[0][3])
    # time.sleep(6000)
    ########################### Below creates paths for users based on the desired path that each user is allowed to take ###########################END
    # b1_paths = [0] #<== This contains all of the paths that we want users in b2 to be able to use
    # for u in range(0,len(b1_u)):
    #     if b1_u[u] != 'none':
    #         #user #1 input route        
            
    #         sug_count=0
    #         for path_num in range(len(s_nums)):#,1,2]: #<== This variable contains the current path #
    #             b_num = 1-path_num#2*len(s_nums)-path_num #<== This will change when implemented for base station 1 to 
    #             i=0
                
    #             # flow_thread=[]
    #             while i<len(s_nums[path_num]):

    #                 p=0
    #                 while p<len(ports[path_num][i]):
    #                     if sug_list[sug_count][0] > 0 and sug_list[sug_count][1] > 0 and sug_list[sug_count][2] == ports[path_num][i][p][0] and int(path_num) in sug_list[sug_count][3] and int(path_num) in b1_paths:
    #                         # # Waits for a user input to confirm the network portion has been setup
    #                         # sec = 0
    #                         # sec = input('Have you configured 12 to '+str(ports[path_num][i][p][1])+'? (1=Yes or 0=No)\n')
    #                         # while sec == 0:
    #                         #     sec = input('Have you configured 12 ==> '+str(ports[path_num][i][p][1])+'? (1=Yes or 0=No)\n')
    #                         group_num = sug_list[sug_count][1]
    #                         # this is allow one port to ouput to multiple ports on the network layer
    #                         temp = add_flow_with_meter(switch[s_nums[path_num][i]],ports[path_num][i][p][0],group_num,b1_u[u],m_l[u][top_num[u]][s_nums[path_num][i]][0],0,top_num[u],b_num,55)
    #                         # print str(temp)
    #                         f_l[u][top_num[u]][s_nums[path_num][i]] = add_f_l(f_l[u][top_num[u]][s_nums[path_num][i]],temp)
    #                     elif sug_list[sug_count][0] == 0 and sug_list[sug_count][1] == 0 and sug_list[sug_count][2] == ports[path_num][i][p][0] and int(path_num) in sug_list[sug_count][3] and int(path_num) in b1_paths:
    #                         # mapping from INPUT ports[path_num][i][0] to OUTPUT ports[path_num][i][1]
    #                         temp = add_flow_with_meter(switch[s_nums[path_num][i]],ports[path_num][i][p][0],ports[path_num][i][p][1],b1_u[u],m_l[u][top_num[u]][s_nums[path_num][i]][0],0,top_num[u],b_num)
    #                         # print str(temp)
    #                         f_l[u][top_num[u]][s_nums[path_num][i]] = add_f_l(f_l[u][top_num[u]][s_nums[path_num][i]],temp)




    #                     if sug_list[sug_count+1][0] > 0 and sug_list[sug_count+1][1] > 0 and sug_list[sug_count+1][2] == ports[path_num][i][p][1] and int(path_num) in sug_list[sug_count+1][3] and int(path_num) in b1_paths:
    #                         group_num = sug_list[sug_count+1][1]
    #                         # this is allow one port to ouput to multiple ports on the network layer
    #                         temp = add_flow_with_meter(switch[s_nums[path_num][i]],ports[path_num][i][p][1],group_num,b1_u[u],m_l[u][top_num[u]][s_nums[path_num][i]][0],1,top_num[u],b_num,55)
    #                         # print str(temp)
    #                         f_l[u][top_num[u]][s_nums[path_num][i]] = add_f_l(f_l[u][top_num[u]][s_nums[path_num][i]],temp)
    #                     elif sug_list[sug_count+1][0] == 0 and sug_list[sug_count+1][1] == 0 and sug_list[sug_count+1][2] == ports[path_num][i][p][1] and int(path_num) in sug_list[sug_count+1][3] and int(path_num) in b1_paths:
    #                         # mapping from OUTPUT ports[path_num][i][1] to INPUT ports[path_num][i][0]
    #                         temp = add_flow_with_meter(switch[s_nums[path_num][i]],ports[path_num][i][p][1],ports[path_num][i][p][0],b1_u[u],m_l[u][top_num[u]][s_nums[path_num][i]][0],1,top_num[u],b_num)
                            
    #                         f_l[u][top_num[u]][s_nums[path_num][i]] = add_f_l(f_l[u][top_num[u]][s_nums[path_num][i]],temp)
    #                     sug_count=sug_count+2
    #                     p=p+1
    #                 i=i+1

    b2_paths = [1] #<== This contains all of the paths that we want users in b2 to be able to use
    # b2_paths are defined as the paths that are required for b2 users
    # sugcount1=sug_count #<== this will prevent b2_users from redundant b1 path flows#TODO improve this
    for u in range(0,len(b2_u)):
        if b2_u[u] != 'none':
            #user #2 input route        
            b2_index=u+len(b1_u)
            
            # for path_num in range(b2_paths): # [1,2]: #<== This variable contains the current path # being looked at for b2 users
            for c_path in range(len(sug_list)):
                b_num = 0#2*len(s_nums)-path_num #<== This will change when implemented for base station 1 to 
                
                for path_num in sug_list[c_path][6]:
                    if int(path_num) in b2_paths: #<==This checks if the path # in the list of paths that need to be configured are required for b2 users.
                        print "\n sug_list[c_path] = "+str(sug_list[c_path])
                        if sug_list[c_path][0] > 0 and sug_list[c_path][1] > 0:
                            # # Waits for a user input to confirm the network portion has been setup
                            # sec = 0
                            # sec = input('Have you configured 12 to '+str(ports[path_num][i][p][1])+'? (1=Yes or 0=No)\n')
                            # while sec == 0:
                            #     sec = input('Have you configured 12 ==> '+str(ports[path_num][i][p][1])+'? (1=Yes or 0=No)\n')
                            group_num = sug_list[c_path][1]
                            # this is allow one port to ouput to multiple ports on the network layer
                            temp = add_flow_with_meter(switch[sug_list[c_path][2]],sug_list[c_path][3],group_num,b2_u[u],m_l[b2_index][top_num[b2_index]][sug_list[c_path][2]][0],sug_list[c_path][5],top_num[b2_index],b_num,55)
                            # print str(temp)
                            f_l[b2_index][top_num[b2_index]][sug_list[c_path][2]] = add_f_l(f_l[b2_index][top_num[b2_index]][sug_list[c_path][2]],temp)
                        elif sug_list[c_path][0] == 0 and sug_list[c_path][1] == 0:
                            # mapping from INPUT ports[path_num][i][0] to OUTPUT ports[path_num][i][1]
                            temp = add_flow_with_meter(switch[sug_list[c_path][2]],sug_list[c_path][3],sug_list[c_path][4],b2_u[u],m_l[b2_index][top_num[b2_index]][sug_list[c_path][2]][0],sug_list[c_path][5],top_num[b2_index],b_num)
                            # print str(temp)
                            f_l[b2_index][top_num[b2_index]][sug_list[c_path][2]] = add_f_l(f_l[b2_index][top_num[b2_index]][sug_list[c_path][2]],temp)
                        break

    # b_num = 1
    # for u in range(0,len(b2_u)):
    #     b2_index=u+len(b1_u)
    #     if b2_u[u] != 'none':
    #         #user #2 input route            
    #         switch_top=0 # <== This variable contains the current path #
    #         for switch_top in [0]:#,2]:
    #             i=0
    #             # flow_thread=[]
    #             while i<len(s_nums):

    #                 p=0
    #                 while p<len(ports[i]):
    #                     # mapping from INPUT ports[i][0] to OUTPUT ports[i][1]
    #                     temp = add_flow_with_meter(switch[s_nums[switch_top][i]],ports[i][p][0],ports[i][p][1],b2_u[u],m_l[b2_index][top_num[b2_index]][s_nums[switch_top][i]][0],0,top_num[b2_index],b_num)
    #                     # print str(temp)
    #                     f_l[b2_index][top_num[b2_index]][s_nums[switch_top][i]] = add_f_l(f_l[b2_index][top_num[b2_index]][s_nums[switch_top][i]],temp)

    #                     # mapping from OUTPUT ports[i][1] to INPUT ports[i][0]
    #                     temp = add_flow_with_meter(switch[s_nums[switch_top][i]],ports[i][p][1],ports[i][p][0],b2_u[u],m_l[b2_index][top_num[b2_index]][s_nums[switch_top][i]][0],1,top_num[b2_index],b_num)
    #                     # print str(temp)
    #                     f_l[b2_index][top_num[b2_index]][s_nums[switch_top][i]] = add_f_l(f_l[b2_index][top_num[b2_index]][s_nums[switch_top][i]],temp)
    #                     p=p+1
    #                 i=i+1
    #             switch_top=switch_top+1

    
    #need to look into the max # of meters allowed as that affects how many users we can have

    return f_l



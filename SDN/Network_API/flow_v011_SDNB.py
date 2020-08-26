import requests
import sys
import time
import numpy as np
import csv
import os

max_num_of_flows_per_user = 4 #TODO THIS NUMBER SHOULD CHANGE TO THE MAX NUMBER OF FLOWS 1 USER MAY HAVE
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
'Authorization': "Basic YWRtaW46YWRtaW4=",
'cache-control': "no-cache"
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
	global debug, error
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

def modify_meter(*args):
	global debug, error
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
	print '\n\nStart modify_meter'
	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/flow-node-inventory:table/0/flow/'
	while(out_count<max_num_of_flows_per_user+1):
		s_time = time.time()
		response = requests.request("GET", url+str(cur_flow), data=payload, headers=headers)
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
	else:
		flow_error.append('3')
		print(str(response.text)) #debuging code
		print('ERROR:Unable to modify Meter '+str(args[1])+'\n')
	if debug == 'ON':
		print 'Time;'+str(time.time()-s_time)+';Request_Type;PUT;Switch_Num;'+str(args[0])+';Function_Name;add_meter'
		print 'MODIFY METER TOTAL Time;'+str(time.time()-total_modify_time)



#TODO Finish adding debug timers for all Requests to get the time it takes to configure the switch. By knowing how long each Request takes we can look at the preformance of the CPU, to see how dynamic path and meter configuration preforms better than regular queue tables for flexibilty. Con to the stem is it takes longer to reconfigure, but it provides meter and flow reconfiguration for decisive security actions at the cost of the switches CPU.


def add_flow_with_meter(*args):
	global num_of_static_flows,max_num_of_flows_per_user
	ttttt1= time.time()
	#print(args) #debuging code
	#NOTES:
	#args[0] = 106225813884652 or 106225813884040 # the switch name
	#args[1] = 1 #the input port #
	#args[2] = 2 #the ouput port #
	#args[3] = 155.0.0.2 #user ip address (assumed to have a 255.255.255.0 netmask)
	#args[4] = 1.0 #meter #
	#args[5] = 1 #1 means desination address and 0 means source address
	#args[6] = 1 #this indicates which topology to build; inivertently this changes the priority
	#args[7] = 1 #this indicates which base station
	#args[8] = 99 #this indicates whether we need a group arp on this flow or not and if we need just an arp flow

	flow_num=1+max_num_of_flows_per_user*(int(args[4])-1)+num_of_static_flows
	# print '\n\n\n\n '+str(int(args[4]))
	# time.sleep(20)
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
	
	flow_type=['ARP','IPv4']#,'TCP','ICMP']#,'UDP']	
	temp=np.zeros((int(len(flow_type))))
	#flow_rec[0] = flow #
	if(len(args)==9):
		if(int(args[8])==99):
			add_group_arp_with_meter(args[0])
			temp[0]=add_flow_arp_for_group_with_meter(args[0],args[1],args[2],args[3],args[4],flow_num,ip_part,int(priority_part))
		elif(int(args[8])==0):
			temp[0]=add_flow_arp_for_group_with_meter(args[0],args[1],args[2],args[3],args[4],flow_num,ip_part,int(priority_part))
		elif(int(args[8])==44):
			temp[0]=add_flow_arp_with_meter(args[0],args[1],args[2],args[3],args[4],flow_num,ip_part,int(priority_part)+1)
	
	if(args[7]==0):
		priority_part = int(priority_part)+1	

	if(len(args)==9 and int(args[8])==0):
		temp[1]=add_flow_ipv4_with_meter(args[0],args[1],args[2],args[3],args[4],temp[0]+1,ip_part,int(priority_part)-1)
	elif(len(args)==9 and int(args[8])==44):
		priority_part = priority_part
		# DO NOTHING. This is because we are only adding an ARP flow and no other flows.
	else:
		temp[1]=add_flow_ipv4_with_meter(args[0],args[1],args[2],args[3],args[4],temp[0]+1,ip_part,int(priority_part))
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

	#the initial GET
	url = 'http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:'+str(args[0])+'/group/1'

	#add a flow entry with a meter
	payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<group xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<group-id>1</group-id>\n\
\t<group-name>SelectGroup</group-name>\n\
\t<group-type>group-all</group-type>\n\
\t<barrier>false</barrier>\n\
\t<buckets>\n\
\t\t<bucket>\n\
\t\t\t<weight>1</weight>\n\
\t\t\t<watch_port>5</watch_port>\n\
\t\t\t<watch_group>4294967295</watch_group>\n\
\t\t\t<action>\n\
\t\t\t\t<output-action>\n\
\t\t\t\t\t<output-node-connector>1</output-node-connector>\n\
\t\t\t\t</output-action>\n\
\t\t\t\t<order>1</order>\n\
\t\t\t</action>\n\
\t\t\t<bucket-id>1</bucket-id>\n\
\t\t</bucket>\n\
\t\t<bucket>\n\
\t\t\t<weight>1</weight>\n\
\t\t\t<watch_port>5</watch_port>\n\
\t\t\t<watch_group>4294967295</watch_group>\n\
\t\t\t<action>\n\
\t\t\t\t<output-action>\n\
\t\t\t\t\t<output-node-connector>11</output-node-connector>\n\
\t\t\t\t</output-action>\n\
\t\t\t\t<order>1</order>\n\
\t\t\t</action>\n\
\t\t\t<bucket-id>2</bucket-id>\n\
\t\t</bucket>\n\
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
	print('DELTA TIME 4 ARP: '+str(time.time()-ttttt))
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
	#args[2] = 2 #the ouput port #
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
\t\t\t\t\t\t<group-id>1</group-id>\n\
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
		if temp[p][0]==0 or temp[p][0]==None:

			# goes through all of the flow list for each flow entry
			temp[p] = args[1][flow_entry_counter]
			flow_entry_counter=flow_entry_counter+1
		p=p+1
	return(args[0])

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

	print '\n\n\n'
	print str(len(temp[0])) # This outputs the # of switches
	print '\n\n\n'
	print str(len(temp[0][0])) # This outputs the # of flows
	print '\n\n\n'
	print str(len(temp[0][0][0]))  # This outputs the # of items on each row. This currently static to 7 items
	print '\n\n\n'
										# of switches
	for s in range(0,len(temp[0])):
											# of flows
		for f in range(0,len(temp[0][0])):
			if(temp[s][f][4]==int(args[1])): #and (int(temp[s][f][4])!=0)):
				temp[args[2]][s][f]=emp
	#print('CALL MODIFY_F_L --------------------------------------------: '+str(time.time()-ttttt))
	
	return(temp)
	
def output_flow(*args):
	b1_u=args[0]
	b2_u=args[1]
	nou=len(b1_u)+len(b2_u)
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
	b=[]
	b.extend(b1_u)
	b.extend(b2_u)
	for l in range(0,nou):
		for p in range(0,len(switch)):
			#goes through all of the flows for user 'u' in all of the switches
			q=0
			while(q<len(f_l[l][top_num[l]][p])):
				if(f_l[l][top_num[l]][p][q][0]!=None):
					# print str(q) + ' ' + str(p)
					# print str(f_l[l][top_num[l]][p][q])
					if(int(f_l[l][top_num[l]][p][q][0])!=0):
						a=[]
						
						a.extend([str(top_num[l]),p+1])
						a.extend(f_l[l][top_num[l]][p][q])
						writer.writerow(a)
					else:
						break
				else:
					# print str(q) + ' ' + str(p)
					# print str(f_l[l][top_num[l]][p][q])
					break
				q=q+1
	f1.close()

def create_topology(*args):
	global max_num_of_flows_per_user
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

	s_nums = [0]#,2,4] #TODO change this to the switches being used in the topology
	ports = [[12,1]]#,[1,7],[3,12]]

	# Creats the ARP connections
	i=0
	b_num = 0
	u_index=len(b1_u)+len(b2_u)
	while i<len(s_nums):
		# mapping from INPUT ports[i][0] to OUTPUT ports[i][1]
		#the ip address for an ARP flow does not matteeer but the meter does
		# print str(len(m_l))
		# print '\n'
		# print str(len(top_num))
		# print '\n'
		# print str(top_num[u_index])
		# print str(m_l[u_index][top_num[u_index]][s_nums[i]][0])
		temp = add_flow_with_meter(switch[s_nums[i]],ports[i][0],ports[i][1],'0.0.0.0',m_l[u_index][top_num[u_index]][s_nums[i]][0],0,top_num[u_index],b_num,44)
		f_l[u_index][top_num[u_index]][s_nums[i]] = add_f_l(f_l[u_index][top_num[u_index]][s_nums[i]],temp)

		# mapping from OUTPUT ports[i][1] to INPUT ports[i][0]
		temp = add_flow_with_meter(switch[s_nums[i]],ports[i][1],ports[i][0],'0.0.0.0',m_l[u_index][top_num[u_index]][s_nums[i]][0],1,top_num[u_index],b_num,44)
		f_l[u_index][top_num[u_index]][s_nums[i]] = add_f_l(f_l[u_index][top_num[u_index]][s_nums[i]],temp)

		i=i+1
	# flow_thread=[]
	
	for u in range(0,len(b1_u)):
		if b1_u[u] != 'none':
			#user #1 input route
			# s_num=0
			# temp = add_flow_with_meter(switch[s_num],12,1,b1_u[u],m_l[u][top_num[u]][s_num][0],0,switch,b_num)
			# f_l = add_f_l(f_l,u,s_num,temp,top_num[u])
			# s_num=2
			# temp = add_flow_with_meter(switch[s_num],1,7,b1_u[u],m_l[u][top_num[u]][s_num][0],0,switch,b_num)
			# f_l = add_f_l(f_l,u,s_num,temp,top_num[u])
			# s_num=4
			# temp = add_flow_with_meter(switch[s_num],3,12,b1_u[u],m_l[u][top_num[u]][s_num][0],0,switch,b_num)
			# f_l = add_f_l(f_l,u,s_num,temp,top_num[u])
			
			i=0
			# flow_thread=[]
			while i<len(s_nums):

				# mapping from INPUT ports[i][0] to OUTPUT ports[i][1]
				temp = add_flow_with_meter(switch[s_nums[i]],ports[i][0],ports[i][1],b1_u[u],m_l[u][top_num[u]][s_nums[i]][0],0,top_num[u],b_num)
				f_l[u][top_num[u]][s_nums[i]] = add_f_l(f_l[u][top_num[u]][s_nums[i]],temp)

				# mapping from OUTPUT ports[i][1] to INPUT ports[i][0]
				temp = add_flow_with_meter(switch[s_nums[i]],ports[i][1],ports[i][0],b1_u[u],m_l[u][top_num[u]][s_nums[i]][0],1,top_num[u],b_num)
				f_l[u][top_num[u]][s_nums[i]] = add_f_l(f_l[u][top_num[u]][s_nums[i]],temp)

				i=i+1

			#BC network to user #1 output route
			# s_num=4
			# temp = add_flow_with_meter(switch[s_num],12,3,b1_u[u],m_l[u][top_num[u]][s_num][0],1,switch,b_num)
			# f_l = add_f_l(f_l,u,s_num,temp,top_num[u])
			# s_num=2
			# temp = add_flow_with_meter(switch[s_num],7,1,b1_u[u],m_l[u][top_num[u]][s_num][0],1,switch,b_num)
			# f_l = add_f_l(f_l,u,s_num,temp,top_num[u])
			# s_num=0
			# temp = add_flow_with_meter(switch[s_num],1,12,b1_u[u],m_l[u][top_num[u]][s_num][0],1,switch,b_num)
			# f_l = add_f_l(f_l,u,s_num,temp,top_num[u])
	# output_flow(b1_u,b2_u,switch,f_l,top_num))
	# time.sleep(30)
	b_num = 1
	for u in range(0,len(b2_u)):
		if b2_u[u] != 'none':
			b2_index=u+len(b1_u)
			#user #2 input route
			s_num=0 #the switch number being modified
			temp = add_flow_with_meter(switch[s_num],10,3,b2_u[u],m_l[b2_index][top_num[b2_index]][s_num][0],0,switch,b_num)
			f_l = add_f_l(f_l,b2_index,s_num,temp,top_num[b2_index])
			s_num=1
			temp = add_flow_with_meter(switch[s_num],1,5,b2_u[u],m_l[b2_index][top_num[b2_index]][s_num][0],0,switch,b_num)
			f_l = add_f_l(f_l,b2_index,s_num,temp,top_num[b2_index])
			s_num=3
			temp = add_flow_with_meter(switch[s_num],3,12,b2_u[u],m_l[b2_index][top_num[b2_index]][s_num][0],0,switch,b_num)
			f_l = add_f_l(f_l,b2_index,s_num,temp,top_num[b2_index])

			#BC network to user #2 output route
			s_num=3
			temp = add_flow_with_meter(switch[s_num],12,3,b2_u[u],m_l[b2_index][top_num[b2_index]][s_num][0],1,switch,b_num)
			f_l = add_f_l(f_l,b2_index,s_num,temp,top_num[b2_index])
			s_num=1
			temp = add_flow_with_meter(switch[s_num],5,1,b2_u[u],m_l[b2_index][top_num[b2_index]][s_num][0],1,switch,b_num)
			f_l = add_f_l(f_l,b2_index,s_num,temp,top_num[b2_index])
			s_num=0
			temp = add_flow_with_meter(switch[s_num],3,10,b2_u[u],m_l[b2_index][top_num[b2_index]][s_num][0],1,switch,b_num)
			f_l = add_f_l(f_l,b2_index,s_num,temp,top_num[b2_index])
	#num of expected flows = # of routes * nou * # of flows per route -1
	#print('CALL ADD_FLOW_WITH_METER #1---------------------------------------------: '+str(time.time()-ttttt11))
	#print('CALL ADD_F_L #1-------------------------------------------------------------------------------: '+str(time.time()-ttttt1))

	#print('Topology Setup Time------------------------------------------------------------------------: '+str(time.time()-ttttt))
	
	
	#need to look into the max # of meters allowed as that affects how many users we can have

	return f_l



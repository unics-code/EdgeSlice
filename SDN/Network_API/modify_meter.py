import requests
import sys

#NOTES:
#sys.argv[0] = modify_meter.py #the name of the python script
#sys.argv[1] = 106225813884652 or 106225813884040 #the switch name
#sys.argv[2] = 20 #BW rate in Megabytes per sec
#sys.argv[3] = 0 #meter #

#STATUS CODES:
#201 Created
#200 OK

headers = {
    'Accept': "application/xml",
    'Content-Type': "application/xml",
    'Authorization': "Basic YWRtaW46YWRtaW4=",
    'cache-control': "no-cache"
    }

url = "http://localhost:8181/restconf/config/opendaylight-inventory:nodes/node/openflow:"+str(sys.argv[1])+"/flow-node-inventory:meter/"+str(sys.argv[3])

#convert the BW rate to kilobits per sec.
#print('MBps='+str(sys.argv[2]))#debug code
kbps=int(float(sys.argv[2])*8*1000)
print('kbps rate limit='+str(kbps))#debug code

if (len(sys.argv)==4):
	#print(url)#debug code
	#modify the meter if all the arguments are provided by the user
	payload = "\
<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n\
<meter xmlns=\"urn:opendaylight:flow:inventory\">\n\
\t<meter-id>"+str(sys.argv[3])+"</meter-id>\n\
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
\t\t\t<drop-rate>16</drop-rate>\n\
\t\t\t<band-burst-size>100</band-burst-size>\n\
\t\t\t<drop-burst-size>1000</drop-burst-size>\n\
\t\t</meter-band-header>\n\
\t</meter-band-headers>\n\
</meter>"
#print(payload)#debug code
else:
	print('# of arguments='+str(len(sys.argv))+'. You must provide 3 arguments')#debug code

response = requests.request("PUT", url, data=payload, headers=headers)
#print('Status Code ='+str(response.status_code))#debug code

response.encoding = 'utf-8'
#print(response.text)
#print(str(response.status_code))

#send http put request
if (response.status_code==200):
	print('Meter '+str(sys.argv[3])+' was modified\n')
else:
	#print(str(response.text))
	print('ERROR:Unable to PUT Meter '+str(sys.argv[3])+'\n')

	
#python command
#clear; python add_meter.py 106225813884652 0 20
#clear; python add_meter.py 106225813884040

import socket, ctypes, time, sys
import numpy as np

buffer_size = 256

# ######## transport    ##########################################################

transport_addr = '155.0.0.1'
transport_port = 10500
#transport_port = 11002

transport_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
transport_socket.connect((transport_addr, transport_port))
start = time.time()
for l in range(int(sys.argv[1])):
	transport_data = "155.0.0.35,"+str(sys.argv[2])+",155.0.0.65,"+str(sys.argv[3])#,155.0.0.36,25"#,155.0.0.38,25"
	#transport_data = "172.16.0.2,10,172.16.0.4,10,172.16.0.6,10,end"
	#transport_data = "172.16.0.2,10,172.16.0.4,10,172.16.0.6,10,172.16.0.8,10,155.0.0.36,100"
	#transport_data = "172.16.0.2," + str(5) + ",172.16.0.4," + str(10) + ",155.0.0.36,10,172.16.0.6," + str(10) + ",172.16.0.8," + str(10) + ",155.0.0.35,10"

	transport_socket.sendall(transport_data.encode())
	complete_info = transport_socket.recv(buffer_size).decode()
	#print("complete_info:",complete_info)
	delta_time = time.time() -start
	print "Test#: "+str(l)+",Delta: "+str(delta_time)
	if delta_time >10.0:
		break
	time.sleep(5)
	start = time.time()
	
transport_socket.close()



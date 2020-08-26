import ctypes
import threading
import socket
import numpy as np



def connect_controller(ctl,nou):
	BUFFER_SIZE=256
	QUATO = np.zeros(2*nou, dtype=np.double) #this is the data being sent from the AI to modify the BW for each user
	controller, ctl_addr = ctl.accept()

	print("Get new controller socket" + str(ctl_addr))

	recv_data = controller.recv(ctypes.sizeof(ctypes.c_double)*BUFFER_SIZE)

	data = np.fromstring(recv_data, dtype=np.double)
	
	#print(data)
	QUATO[:nou*2] = data[:nou*2]
	#print(QUATO)

	return QUATO

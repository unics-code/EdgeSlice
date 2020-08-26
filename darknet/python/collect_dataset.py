#!python3

'''
##############################
### Receive Video stream #####
### from Android client #######
### Use yolo to do detect ####
## (return a message to the mobile device) ##
##############################
'''
from ctypes import *
import math
import random
import os
import socket
import time
import cv2
import numpy as np
from PIL import Image
import sys
import pickle
import struct
import timeit
import time
import threading
import ctypes


# generate different colors for different classes 
COLORS = np.random.uniform(0, 255, size=(80,3))

def sample(probs):
    s = sum(probs)
    probs = [a/s for a in probs]
    r = random.uniform(0, 1)
    for i in range(len(probs)):
        r = r - probs[i]
        if r <= 0:
            return i
    return len(probs)-1

def c_array(ctype, values):
    arr = (ctype*len(values))()
    arr[:] = values
    return arr

class BOX(Structure):
    _fields_ = [("x", c_float),
                ("y", c_float),
                ("w", c_float),
                ("h", c_float)]

class DETECTION(Structure):
    _fields_ = [("bbox", BOX),
                ("classes", c_int),
                ("prob", POINTER(c_float)),
                ("mask", POINTER(c_float)),
                ("objectness", c_float),
                ("sort_class", c_int)]


class IMAGE(Structure):
    _fields_ = [("w", c_int),
                ("h", c_int),
                ("c", c_int),
                ("data", POINTER(c_float))]

class METADATA(Structure):
    _fields_ = [("classes", c_int),
                ("names", POINTER(c_char_p))]

    
lib = CDLL("/home/nano/darknet/libdarknet.so", RTLD_GLOBAL)
lib.network_width.argtypes = [c_void_p]
lib.network_width.restype = c_int
lib.network_height.argtypes = [c_void_p]
lib.network_height.restype = c_int

predict = lib.network_predict
predict.argtypes = [c_void_p, POINTER(c_float)]
predict.restype = POINTER(c_float)

set_gpu = lib.cuda_set_device
set_gpu.argtypes = [c_int]

make_image = lib.make_image
make_image.argtypes = [c_int, c_int, c_int]
make_image.restype = IMAGE

get_network_boxes = lib.get_network_boxes
get_network_boxes.argtypes = [c_void_p, c_int, c_int, c_float, c_float, POINTER(c_int), c_int, POINTER(c_int)]
get_network_boxes.restype = POINTER(DETECTION)

make_network_boxes = lib.make_network_boxes
make_network_boxes.argtypes = [c_void_p]
make_network_boxes.restype = POINTER(DETECTION)

free_detections = lib.free_detections
free_detections.argtypes = [POINTER(DETECTION), c_int]

free_ptrs = lib.free_ptrs
free_ptrs.argtypes = [POINTER(c_void_p), c_int]

network_predict = lib.network_predict
network_predict.argtypes = [c_void_p, POINTER(c_float)]

reset_rnn = lib.reset_rnn
reset_rnn.argtypes = [c_void_p]

load_net = lib.load_network
load_net.argtypes = [c_char_p, c_char_p, c_int]
load_net.restype = c_void_p

do_nms_obj = lib.do_nms_obj
do_nms_obj.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

do_nms_sort = lib.do_nms_sort
do_nms_sort.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

free_image = lib.free_image
free_image.argtypes = [IMAGE]

letterbox_image = lib.letterbox_image
letterbox_image.argtypes = [IMAGE, c_int, c_int]
letterbox_image.restype = IMAGE

load_meta = lib.get_metadata
lib.get_metadata.argtypes = [c_char_p]
lib.get_metadata.restype = METADATA

load_image = lib.load_image_color
load_image.argtypes = [c_char_p, c_int, c_int]
load_image.restype = IMAGE

rgbgr_image = lib.rgbgr_image
rgbgr_image.argtypes = [IMAGE]

predict_image = lib.network_predict_image
predict_image.argtypes = [c_void_p, IMAGE, c_int]
predict_image.restype = POINTER(c_float)

#def classify(net, meta, im):
#    out = predict_image(net, im)
#    res = []
#    for i in range(meta.classes):
#        res.append((meta.names[i], out[i]))
#    res = sorted(res, key=lambda x: -x[1])
#    return res

### modified ###

HOST=''
USER_PORT=9001
CTL_PORT=11111
BUFFER_SIZE = 256
QUATO = 100
num_points = 5
wait_time = 0.01
Latency = []
Count = 0


def threading_controller(controller):
    global QUATO
    global Latency
    print ("entered controller threading.", controller)

    while True:
        recv_data = controller.recv(ctypes.sizeof(ctypes.c_double)*BUFFER_SIZE)
        if len(recv_data)<=0: break

        data = np.fromstring(recv_data, dtype=np.double)
        #print(data)
        QUATO = int(data[0])
        print('GPU virtual resource is ' + str(QUATO))
        Latency = []

        while(len(Latency)<num_points): time.sleep(wait_time)
        assert(len(Latency)>=num_points) #make sure there has data in the latency
        send_data = np.mean(Latency[1:]) * np.ones(BUFFER_SIZE, dtype=np.double)

        #try to send data, if error break
           
        controller.sendall(send_data)

	# if controller drop, then close and re-accept
    controller.close()


def connect_controller():

    ctl = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

    ctl.bind((HOST, CTL_PORT))
    ctl.listen(10)
    print('Controller Socket now listening')

    while True:
        controller, ctl_addr = ctl.accept()
        print("Get new controller socket" + str(ctl_addr))
        # start the thread darknet
        threads = threading.Thread(target=threading_controller, args=(controller,))
        threads.start()

def recv_image_from_socket(client):
    buffers = b''
    while len(buffers)<4:
        try:
            buf = client.recv(4-len(buffers))
        except:
            return False
        buffers += buf

    size, = struct.unpack('!i', buffers)
    #print "receiving %d bytes" % size
    recv_data = b''
    while len(recv_data) < size:
        try:
            data = client.recv(1024)
        except:
            return False
        recv_data += data

    frame_data = recv_data[:size]
    #recv_data = recv_data[size:]

    imgdata = np.fromstring(frame_data, dtype='uint8')
    decimg = cv2.imdecode(imgdata,1)

    return decimg

def detect(net, meta, image, quato, thresh=.5, hier_thresh=.5, nms=.45):

    # GET C,H,W, and DATA values

    img = image.transpose(2, 0, 1)
    c, h, w = img.shape[0], img.shape[1], img.shape[2]
    nump_data = img.ravel() / 255.0
    nump_data = np.ascontiguousarray(nump_data, dtype=np.float32)

    # make c_type pointer to numpy array
    ptr_data = nump_data.ctypes.data_as(POINTER(c_float))

    # make IMAGE data type
    im = IMAGE(w=w, h=h, c=c, data=ptr_data)

    num = c_int(0)
    pnum = pointer(num)
    predict_image(net, im, quato)
    dets = get_network_boxes(net, im.w, im.h, thresh, hier_thresh, None, 0, pnum)
    num = pnum[0]
    if (nms): do_nms_obj(dets, num, meta.classes, nms);

    res = []
    for j in range(num):
        for i in range(meta.classes):
            if dets[j].prob[i] > 0:
                b = dets[j].bbox
                classid = i
                calssnamess = meta.names[i].decode('UTF-8')
                res.append((calssnamess, dets[j].prob[i], (b.x, b.y, b.w, b.h),classid))
    res = sorted(res, key=lambda x: -x[1])

    #free_image(im)
    free_detections(dets, num)
    return res

# display the pic after detecting
def showPicResult(r,im):
    for i in range(len(r)):
        x1=r[i][2][0]-r[i][2][2]/2
        y1=r[i][2][1]-r[i][2][3]/2
        x2=r[i][2][0]+r[i][2][2]/2
        y2=r[i][2][1]+r[i][2][3]/2

        color = COLORS[r[i][3]]
        cv2.rectangle(im,(int(x1),int(y1)),(int(x2),int(y2)),color,2)
        #putText
        x3 = int(x1+5)
        y3 = int(y1-10)
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        text = "{}: {:.4f}".format(str(r[i][0]), float(r[i][1]))
        if ((x3<=im.shape[0]) and (y3>=0)):
            cv2.putText(im, text, (x3,y3), font, 0.5, color, 1,cv2.CV_AA)
        else:
            cv2.putText(im, text, (int(x1),int(y1+6)), font, 0.5, color, 1,cv2.CV_AA)

    #if frameID>= 45 and frameID<=50:
    #    cv2.imwrite("/home/nvidia/Desktop/haoxin/images/newNexus320/320off/image%3d.bmp" %frameID,im)
    cv2.imshow('Detection Window', im)
    cv2.waitKey(0)
    #cv2.destroyAllWindows()


if __name__ == "__main__":

    t1 = threading.Thread(target = connect_controller)
    t1.setDaemon(True)
    t1.start()

    #detect_net = load_net(b"./cfg/yolov3-tiny.cfg", b"yolov3-tiny.weights", 0)
    #detect_net = load_net(b"./cfg/yolov3-416.cfg", b"yolov3.weights", 0)
    detect_net = load_net(b"./cfg/yolov3-608.cfg", b"yolov3.weights", 0)

    detect_meta = load_meta(b"cfg/coco.data")

    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.bind((HOST,USER_PORT))
    s.listen(10)

    while True:
        client,addr=s.accept()
        print ("Get new user socket")

        StartTime = time.time()

        while True:
            decimg = recv_image_from_socket(client)
            if decimg is False: 
                print("client droped, break, waiting other clients")
                break
            result = detect(detect_net, detect_meta, decimg, QUATO, thresh=0.7)
            Latency.append(time.time() - StartTime)
            print(str(time.time() - StartTime))
            #print(result)
            #time.sleep(1)
            str1 = '0'+'\n'
            client.sendall(str1.encode())
            StartTime = time.time()

	# if client drop, then close and re-accept
        client.close()



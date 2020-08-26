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
import Queue
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

    
lib = CDLL("/root/darknet_backup/libdarknet.so", RTLD_GLOBAL)
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
Interval = 2
Count = 0

def connect_controller():
    global QUATO
    global Count
    ctl = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

    ctl.bind((HOST, CTL_PORT))
    ctl.listen(10)
    print('Controller Socket now listening')

    while True:
        controller, ctl_addr = ctl.accept()
        print("Get new controller socket" + str(ctl_addr))
        while True:
            recv_data = controller.recv(ctypes.sizeof(ctypes.c_double)*BUFFER_SIZE)
            if len(recv_data) <=0:
                break
            Count = 0
            data = np.fromstring(recv_data, dtype=np.double)
            #print(data)
            QUATO = int(data[0])
            print(QUATO)


def detect(net, meta, thresh=.5, hier_thresh=.5, nms=.45):
    global QUATO

    im = load_image("data/1.jpg", 0, 0)

    num = c_int(0)
    pnum = pointer(num)
    predict_image(net, im, QUATO)
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



if __name__ == "__main__":

    t1 = threading.Thread(target = connect_controller)
    t1.setDaemon(True)
    t1.start()

    detect_net = load_net("./cfg/yolov3.cfg", "yolov3.weights", 0)
    detect_meta = load_meta("cfg/coco.data")

    data = b''

    StartTime = time.time()
    while True:

        result = detect(detect_net, detect_meta, thresh=0.7)
            
        Latency = time.time() - StartTime
        print(Latency)
        StartTime = time.time()
        



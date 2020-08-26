#!python3

'''
##############################
### Receive Video stream #####
### from Android client #######
### Use yolo to do detect ####
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
import threading
import Queue

f = open('/home/nvidia/Desktop/haoxin/whx.txt','w+')
f2 = open('/home/nvidia/Desktop/haoxin/whx1.txt','w+')
os.environ['GLOG_minloglevel'] = '2' 

HOST=''
PORT=8815

working_dir = "/db"
output_dir = os.path.join(working_dir, "output")
car_output_dir = os.path.join(output_dir, "car_output")

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

    
lib = CDLL("/home/nvidia/darknet/libdarknet.so", RTLD_GLOBAL)
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
predict_image.argtypes = [c_void_p, IMAGE]
predict_image.restype = POINTER(c_float)

#def classify(net, meta, im):
#    out = predict_image(net, im)
#    res = []
#    for i in range(meta.classes):
#        res.append((meta.names[i], out[i]))
#    res = sorted(res, key=lambda x: -x[1])
#    return res

### modified ###
def recImage(client,data,q):
    while True:
        buf = ''
        while len(buf)<4:
            buf += client.recv(4-len(buf))
        size = struct.unpack('!i', buf)[0]
        print "receiving %d bytes" % size
        while len(data) < size:
            data += client.recv(4096)
        frame_data = data[:size]
        data = data[size:]
        imgdata = np.fromstring(frame_data, dtype='uint8')
        decimg = cv2.imdecode(imgdata,1)
        q.put(decimg)
        #frameID += 1
        #endtime_recv = time.time()
        print ("frame finish offloading")

def showCamera(winname2,q):
    while True:
        if not q.empty():
            cv2.imshow(winname2,q.get())
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break


def detect(net, meta, image, thresh=.5, hier_thresh=.5, nms=.45):
    #check if image is an OpenCV frame
    if isinstance(image, np.ndarray):
        # GET C,H,W, and DATA values
        print ('1')
        img = image.transpose(2, 0, 1)
        c, h, w = img.shape[0], img.shape[1], img.shape[2]
        nump_data = img.ravel() / 255.0
        nump_data = np.ascontiguousarray(nump_data, dtype=np.float32)

        # make c_type pointer to numpy array
        ptr_data = nump_data.ctypes.data_as(POINTER(c_float))

        # make IMAGE data type
        im = IMAGE(w=w, h=h, c=c, data=ptr_data)

    else:
        im = load_image(image, 0, 0)
        print ('2')

    stime = time.time()
    num = c_int(0)
    pnum = pointer(num)
    predict_image(net, im)
    dets = get_network_boxes(net, im.w, im.h, thresh, hier_thresh, None, 0, pnum)
    num = pnum[0]
    if (nms): do_nms_obj(dets, num, meta.classes, nms);

    res = []
    for j in range(num):
        for i in range(meta.classes):
            if dets[j].prob[i] > 0:
                b = dets[j].bbox
                calssnamess = meta.names[i].decode('UTF-8')
                res.append((calssnamess, dets[j].prob[i], (b.x, b.y, b.w, b.h)))
    res = sorted(res, key=lambda x: -x[1])
#    free_image(im)
    free_detections(dets, num)
    return res

    
def draw_results(res, img, frameID):
    numCar=0
    for element in res:
        box = element[2]
        xmin = int(box[0] - box[2] / 2. + 1)
        xmax = int(box[0] + box[2] / 2. + 1)
        ymin = int(box[1] - box[3] / 2. + 1)
        ymax = int(box[1] + box[3] / 2. + 1)
#        saveResult.write(str(frameID)+' '+ str(numCar)+' '+ str(box[0])+' '+ str(box[1])+' '+ str(box[2])+' '+ str(box[3])+' ' +element[0] +'\n')
        timestamp = str(time.strftime("%Y_%m_%d_%H_%M_%S"))
#        my_dict={'X-Amz-Meta-Timestamp': timestamp,'X-Amz-Meta-Label': str(element[0])}

#        rand_color = (random.randint(0,255),random.randint(0,255),random.randint(0,255))
#        cv2.rectangle(img, (xmin, ymin), (xmax, ymax),color=rand_color , thickness=3, )
#        cv2.putText(img, str(element[0])+" "+ '%.2f' % element[1],
#                    (xmin, ymin),
#                     cv2.FONT_HERSHEY_SIMPLEX, 1.5, rand_color, thickness=1)
        
#        if str(element[0]) == 'car':
#            #prepare to send the cropped image
#            clientsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#            clientsock.connect((HOST, PORT))
#            image_class = str(element[0])
#            clientsock.send(image_class.ljust(20))
#            clientsock.close()
        if str(element[0]) == 'car':
            #prepare to send the cropped image
#            clientsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#            clientsock.connect((HOST, PORT))
            image_class = str(element[0])
#            clientsock.send(image_class.ljust(20))
#            clientsock.close()
            xmin = max(xmin,0)
            ymin = max(ymin,0) 
            xmax = min(xmax,960)
            ymax = min(ymax,540)      
            img_crop = img[ymin:ymax, xmin:xmax]
#            im=caffe.io.load_image('/home/coo/caffe/examples/images/audi.png')



#            net.blobs['data'].data[...] = transformer.preprocess('data',img_crop)

#            out = net.forward()

##            imagenet_labels_filename = '/caffe/data/ilsvrc12/car_class.txt'
#            labels = np.loadtxt(imagenet_labels_filename, str, delimiter='\t')

#            top_k = net.blobs['prob'].data[0].flatten().argsort()[-1:-6:-1]
#	#for i in np.arange(top_k.size):
#	#	print top_k[i], labels[top_k[i]]

#            classifyreslut =  labels[top_k[0]].split(' ',1)
#            print (classifyreslut[1])

#            color_net.blobs['data'].data[...] = color_transformer.preprocess('data',img_crop)
#            color_out = color_net.forward()
#	
#            color_labels = np.loadtxt(color_labels_file, str, delimiter='\t')
#            top_k = color_net.blobs['prob'].data[0].flatten().argsort()[-1:-6:-1]
#            #for i in np.arange(top_k.size):
#            #    print top_k[i], color_labels[top_k[i]]
#            color_result =  color_labels[top_k[0]].split(' ',1)



#            saveResult.write(str(frameID)+' '+ str(numCar)+' '+ str(box[0])+' '+ str(box[1])+' '+ str(box[2])+' '+ str(box[3])+' ' +element[0] +'\n')
#            saveResult2.write(str(frameID)+' '+ str(numCar)+' '+classifyreslut[1] + ' ' + color_result[1] + '\n')
#            print (color_result[1])
            out_file_name = str(int(frameID))+'_'+str(int(numCar))+".jpg"
            out_file_name = str(timestamp)+'_'+str(int(numCar))+".jpg"
            out_file_full_name = os.path.join(car_output_dir, out_file_name)
            cv2.imwrite(out_file_full_name, img_crop)
            print ("number: ", numCar)
            numCar+=1
            
#            mc_car.fput_object('server-car', out_file_name, out_file_full_name, metadata=my_dict)
#            print (mc_car.stat_object('server-car', out_file_name).metadata['X-Amz-Meta-Timestamp'])

#        elif str(element[0]) == 'person':
#            #prepare to send the cropped image
##            clientsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
##            clientsock.connect((HOST, PORT))
#            image_class = str(element[0])
##            clientsock.send(image_class.ljust(20))
##            clientsock.close()       
#            img_crop = img[ymin:ymax, xmin:xmax]
#            timestamp = str(time.strftime("%Y_%m_%d_%H_%M_%S_"))
#            out_file_name = str(int(frameID))+'_'+str(int(num))+".jpg"
#            out_file_full_name = os.path.join(person_output_dir, out_file_name)
#            cv2.imwrite(out_file_full_name, img_crop)
#            print "number: ", num
#            num+=1

#            mc_person.fput_object('myperson', out_file_name, out_file_full_name, metadata=my_dict)
#            print(mc_person.stat_object('myperson', out_file_name).metadata['X-Amz-Meta-Timestamp'])

if __name__ == "__main__":
    detect_net = load_net("./cfg/yolov3.cfg", "yolov3.weights", 0)
    detect_meta = load_meta("cfg/coco.data")
    
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    print ('Socket created')

    s.bind((HOST,PORT))
    print ('Socket bind complete')
    s.listen(10)
    print ('Socket now listening')

    client,addr=s.accept()
    print ("Get new socket")

    winname1 = "Detection Window"
    cv2.namedWindow(winname1)
    winname2 = "Camera Window"
    cv2.namedWindow(winname2)

    data = b''
    frameID = 1
    starttime = time.time()

    threads = []

    #q = Queue.Queue()
    q = Queue.LifoQueue()
    t1 = threading.Thread(target = recImage, args = (client,data,q))
    threads.append(t1)
    t2 = threading.Thread(target = showCamera, args = (winname2,q))
    threads.append(t2)

    for t in threads:
        #t.setDaemon(True)
        t.start()

    while True:
        if not q.empty():
            decimg = q.get()
            result = detect(detect_net, detect_meta, decimg, thresh=0.1)
            cv2.imshow(winname1,decimg)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            print ("DETECT", result)

        #print >> f2, "%f" %(endtime_det - endtime_recv)

        #draw_results(result, frame, frameID)
        #endtime = time.time()

#        frame=pickle.loads(frame_data, encoding="latin1")  
#        cv2.imshow('frame', frame)

#        print frame
#        cv2.imshow('frame',frame)
#    fr = 0
#    while cap.isOpened():

#        ret, frame = cap.read()
#        
#        #RUN OBJECT DETECTION ON FRAME
#        result = detect(detect_net, detect_meta, frame, thresh=0.5)
#        print ("DETECT", result)
#        draw_results(result, frame)
##        print "frameID: ", fr
##        fr += 1
#        cv2.imshow('frame', frame)
#        if cv2.waitKey(1) & 0xFF == ord('q'):
#            break

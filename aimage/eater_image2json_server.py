#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time,os,sys,signal
import numpy as np
import cv2
from PIL import Image, ImageFont, ImageDraw
import argparse
parser = argparse.ArgumentParser(description='')
parser.add_argument('--inference',type=str, default="demo_object_detection",help='')
parser.add_argument('--ssl',action='store_true',help='')
parser.add_argument('--crt',type=str, default="",help='signed certificate file path')
parser.add_argument('--key',type=str, default="",help='private key file path')
parser.add_argument('--port',type=int, default=3000,help='')
parser.add_argument('--host',type=str, default="localhost",help='')
parser.add_argument('--quality',type=int, default=60,help='')
parser.add_argument('--dataset_dir',type=str, default="man2woman",help='')
args = parser.parse_args()


import eater_bridge_server as ebs
import evaluator
model = evaluator.Evaluator()

class ImageServer(ebs.EaterBridgeServer):
    def __init__(self,**kargs):
        super().__init__(**kargs)
        self.data_queue = []
        self.model = None
        import evaluator;self.model = evaluator.Evaluator()
    def update(self):
        #if self.model is None: self.model = yolov3.YOLO()
        self.data_queue += bridge.getDataBlocksAsArray()
        if len(self.data_queue) > 0:
            batch_data, socket_mapper, self.data_queue = ebs.slice_as_batch_size(self.data_queue,128)

            batch_data = np.uint8(batch_data)
            for i in range(len(batch_data)):
                # batch_data[i] = cv2.cvtColor(batch_data[i],cv2.COLOR_BGR2RGB)

                img = batch_data[i]

                #img = Image.fromarray(img)
                # img = Image.fromarray(np.uint8(img))
                r_image = self.model.eval(img)
                #r_image = np.asarray(r_image)
                # r_image = cv2.resize(r_image,(img.shape[1],img.shape[0]))
                # print(r_image)

                batch_data[i] = r_image

                # batch_data[i] = model.detect_image(np.array(batch_data[i]))
                # data = batch_data[i]
                # batch_data[i] = cv2.cvtColor(np.array(batch_data[i]),cv2.COLOR_BGR2RGB)

            stored_datablocks = ebs.pack_array_datablock(socket_mapper,batch_data)
            bridge.setDataBlocksFromArray(stored_datablocks)



bridge = ImageServer(**args.__dict__)

def terminate(a,b):
    global bridge
    bridge.destroy()
    time.sleep(2)
    exit(9)
signal.signal(signal.SIGINT, terminate)
signal.signal(signal.SIGTERM, terminate)
bridge.run()

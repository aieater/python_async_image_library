#!/usr/bin/env python3

import cv2
import aimage
import os
import numpy as np
import json
import time
import signal
from aimage.eater.application import image2image_server
#from aimage.eater.application import image2json_server
from easydict import EasyDict as edict

args = edict()
args.ssl = False
args.crt = None
args.key = None
args.inference = "test"
args.host = "localhost"
args.port = 3000
args.quality = 60
# args.dataset_dir = man2woman

bridge = image2image_server.ImageServer(**args.__dict__)


def terminate(a, b):
    bridge.destroy()
    exit(9)


signal.signal(signal.SIGINT, terminate)
signal.signal(signal.SIGTERM, terminate)
bridge.run()

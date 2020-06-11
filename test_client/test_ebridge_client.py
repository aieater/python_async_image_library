#!/usr/bin/env python3

import json
import os

import aimage
import cv2
import numpy as np
from aimage.eater.bridge import client
import signal
import time


class CListener():
    def disconnected(self, s):
        print("disconnected")
        pass

    def connected(self, s):
        print("connected")
        pass


def terminate(a, b):
    client.destroy()
    exit(9)
signal.signal(signal.SIGINT, terminate)
signal.signal(signal.SIGTERM, terminate)

client = client.EaterBridgeClient(host="localhost", port=3000, listener=CListener())
client.start()

while True:
    time.sleep(1)
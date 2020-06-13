#!/usr/bin/env python3

import json
import os
import signal
import time
import queue

import cv2
import numpy as np

import aimage

import aimage.eater.bridge as bridge
import aimage.eater.bridge.client as client
import aimage.eater.bridge.protocol as protocol


def terminate(a, b):
    client.destroy()
    exit(9)


signal.signal(signal.SIGINT, terminate)
signal.signal(signal.SIGTERM, terminate)


def echo():
    class ProtocolStack(bridge.client.StreamClientFactory):
        def on_connected(self):
            s = self.protocol_instance
            s.add_input_protocol(protocol.DirectStream())
            s.add_output_protocol(protocol.DirectStream())

        def on_disconnected(self):
            pass

    c = client.EaterBridgeClient(host="localhost", port=3000, protocol_stack=ProtocolStack)
    c.start()
    request_count = 0
    index = 0
    while True:
        if request_count < 1:
            s = str(index)
            c.write(s)
            request_count += len(s)
            index += 1
        data = c.read()
        if isinstance(data, bytes) or isinstance(data, bytearray):
            print(data)
            request_count -= len(data)
        else:
            time.sleep(0.001)

def data2data():
    class ProtocolStack(bridge.client.StreamClientFactory):
        def on_connected(self):
            s = self.protocol_instance
            s.add_input_protocol(protocol.LengthSplitIn())
            s.add_output_protocol(protocol.LengthSplitOut())
        def on_disconnected(self):
            pass

    c = client.EaterBridgeClient(host="localhost", port=3000, protocol_stack=ProtocolStack)
    c.start()
    request_count = 0
    while True:
        if request_count < 2:
            datas = ["test", "test2"]
            print(f"Main:send({request_count}):", datas)
            c.write(datas)
            request_count += 2
        blocks = c.read()
        if blocks is not None:
            if isinstance(blocks, list):
                for data in blocks:
                    request_count -= 1
                    # TODO list / bytes
                    print(f"Main:response({request_count}):", data.decode('utf-8'))
                    # for data in extend:
                    #     print(data.decode('utf-8'))
                    # blocks = client.read()
                    # for img in blocks:
                    #     aimage.show(img)
        else:
            time.sleep(0.1)
        


if __name__ == "__main__":
    #data2data()
    echo()

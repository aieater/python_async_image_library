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
import aimage.eater.bridge as bridge
import aimage.eater.bridge.protocol as protocol
import aimage.eater.bridge.server as server

args = edict()
args.ssl = False
args.crt = None
args.key = None
args.inference = "test"
args.host = "localhost"
args.port = 3000
args.quality = 60


def echo():
    class ProtocolStack(server.StreamFactory):
        def build_protocol_stack(self, s):
            s.add_input_protocol(protocol.DirectStream())
            s.add_output_protocol(protocol.DirectStream())

    class EchoServer(server.EaterBridgeServer):
        def __init__(self, **kargs):
            super().__init__(**kargs)
            self.data_queue = []
            self.model = None

        def update(self):
            if self.model is None:
                import evaluator
                self.model = evaluator.Evaluator()
            self.data_queue += self.getDataBlocksAsArray()
            if len(self.data_queue) > 0:
                batch_data, socket_mapper, self.data_queue = server.slice_as_batch_size(self.data_queue, 128)
                stored_datablocks = server.pack_array_datablock(socket_mapper, batch_data)
                self.setDataBlocksFromArray(stored_datablocks)

    # class EchoServer(server.EaterBridgeServer):
    #     def __init__(self, **kargs):
    #         super().__init__(**kargs)
    #         self.data_queue = []
    #         self.model = None

    #     def update(self):
    #         if self.model is None:
    #             import evaluator
    #             self.model = evaluator.Evaluator()
    #         self.data_queue += self.getDataBlocksAsArray()
    #         if len(self.data_queue) > 0:
    #             batch_data, socket_mapper, self.data_queue = server.slice_as_batch_size(self.data_queue, 128)

    #             batch_data = np.uint8(batch_data)
    #             for i in range(len(batch_data)):
    #                 img = batch_data[i]
    #                 r_image = self.model.eval(img)
    #                 batch_data[i] = r_image

    #             stored_datablocks = server.pack_array_datablock(socket_mapper, batch_data)
    #             self.setDataBlocksFromArray(stored_datablocks)

    args.protocol_stack = ProtocolStack

    #bridge = image2image_server.ImageServer(**args.__dict__)
    bridge = EchoServer(**args.__dict__)

    def terminate(a, b):
        bridge.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    bridge.run()


def data2data():
    class ProtocolStack(server.StreamFactory):
        def build_protocol_stack(self, s):
            s.add_input_protocol(protocol.LengthSplitIn())
            s.add_output_protocol(protocol.LengthSplitOut())

    class EchoServer(server.EaterBridgeServer):
        def __init__(self, **kargs):
            super().__init__(**kargs)
            self.data_queue = []
            self.model = None

        def update(self):
            if self.model is None:
                import evaluator
                self.model = evaluator.Evaluator()
            self.data_queue += self.getDataBlocksAsArray()
            if len(self.data_queue) > 0:
                batch_data, socket_mapper, self.data_queue = server.slice_as_batch_size(self.data_queue, 128)
                print("EchoServer:update", self.data_queue,  batch_data)
                stored_datablocks = server.pack_array_datablock(socket_mapper, batch_data)
                self.setDataBlocksFromArray(stored_datablocks)

    args.protocol_stack = ProtocolStack
    bridge = EchoServer(**args.__dict__)

    def terminate(a, b):
        bridge.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    bridge.run()

    # s.add_input_protocol(protocol.LengthSplitIn())
    # s.add_input_protocol(protocol.ImageDecoder())
    # s.add_output_protocol(protocol.ImageEncoder(quality=60))
    # s.add_output_protocol(protocol.LengthSplitOut())


if __name__ == "__main__":
    data2data()
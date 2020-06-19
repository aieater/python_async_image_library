#!/usr/bin/env python3

import logging
import signal
import sys
import aimage

#aimage.is_available_native_queue = True

import numpy as np
from easydict import EasyDict as edict

import aimage.eater.bridge as bridge

def setup_log(name=__name__, level=logging.DEBUG):
    logger = logging.getLogger(name) if name is not None else logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(filename)s:%(lineno)d] %(message)s"))
    logger.addHandler(handler)
    return logger


setup_log("aimage.eater.bridge", level=logging.DEBUG)
logger = setup_log(__name__, logging.DEBUG)

def echo(args):
    class ProtocolStack(bridge.server.StreamFactory):
        def build_protocol_stack(self, s):
            s.add_input_protocol(bridge.protocol.DirectStream())
            s.add_output_protocol(bridge.protocol.DirectStream())
            self.enable_info()

    class Server(bridge.server.EaterBridgeServer):
        def __init__(self, kargs):
            super().__init__(kargs)
            self.data_queue = []
            self.model = None

        def update(self):
            if self.model is None:
                import evaluator
                self.model = evaluator.Evaluator()
            new_data = self.getDataBlocksAsArray()
            self.data_queue += new_data
            if len(self.data_queue) > 0:
                batch_data, socket_mapper, self.data_queue = bridge.server.slice_as_batch_size(self.data_queue, 128)
                stored_datablocks = bridge.server.pack_array_datablock(socket_mapper, batch_data)
                self.setDataBlocksFromArray(stored_datablocks)
            return len(new_data)

    args.protocol_stack = ProtocolStack

    sv = Server(args)

    def terminate(a, b):
        sv.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    sv.run()


def data2data(args):
    class ProtocolStack(bridge.server.StreamFactory):
        def build_protocol_stack(self, s):
            s.add_input_protocol(bridge.protocol.LengthSplitIn())
            s.add_output_protocol(bridge.protocol.LengthSplitOut())
            self.enable_info()

    class Server(bridge.server.EaterBridgeServer):
        def __init__(self, kargs):
            super().__init__(kargs)
            self.data_queue = []
            self.model = None

        def update(self):
            if self.model is None:
                import evaluator
                self.model = evaluator.Evaluator()
            new_data = self.getDataBlocksAsArray()
            self.data_queue += new_data
            if len(self.data_queue) > 0:
                batch_data, socket_mapper, self.data_queue = bridge.server.slice_as_batch_size(self.data_queue, 128)
                logger.debug("EchoServer:update", self.data_queue, batch_data)
                stored_datablocks = bridge.server.pack_array_datablock(socket_mapper, batch_data)
                self.setDataBlocksFromArray(stored_datablocks)
            return len(new_data)

    args.protocol_stack = ProtocolStack
    sv = Server(args)

    def terminate(a, b):
        sv.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    sv.run()


def image2image(args):
    class ProtocolStack(bridge.server.StreamFactory):
        def build_protocol_stack(self, s):
            s.add_input_protocol(bridge.protocol.LengthSplitIn())
            s.add_input_protocol(bridge.protocol.ImageDecoder())
            s.add_output_protocol(bridge.protocol.ImageEncoder(quality=args.quality))
            s.add_output_protocol(bridge.protocol.LengthSplitOut())
            self.enable_info()

    class Server(bridge.server.EaterBridgeServer):
        def __init__(self, kargs):
            super().__init__(kargs)
            self.data_queue = []
            self.model = None

        def update(self):
            if self.model is None:
                import evaluator
                self.model = evaluator.Evaluator()
            new_data = self.getDataBlocksAsArray()
            self.data_queue += new_data
            if len(self.data_queue) > 0:
                batch_data, socket_mapper, self.data_queue = bridge.server.slice_as_batch_size(self.data_queue, 128)
                logger.debug("EchoServer:update", self.data_queue, batch_data)
                batch_data = np.uint8(batch_data)
                for i in range(len(batch_data)):
                    img = batch_data[i]
                    r_image = self.model.eval(img)
                    batch_data[i] = r_image

                stored_datablocks = bridge.server.pack_array_datablock(socket_mapper, batch_data)
                self.setDataBlocksFromArray(stored_datablocks)
            return len(new_data)
    args.protocol_stack = ProtocolStack
    sv = Server(args)

    def terminate(a, b):
        sv.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    sv.run()



def image2image(args):
    class ProtocolStack(bridge.server.StreamFactory):
        def build_protocol_stack(self, s):
            s.add_input_protocol(bridge.protocol.LengthSplitIn())
            s.add_input_protocol(bridge.protocol.ImageDecoder())
            s.add_output_protocol(bridge.protocol.ImageEncoder(quality=args.quality))
            s.add_output_protocol(bridge.protocol.LengthSplitOut())
            self.enable_info()

    class Server(bridge.server.EaterBridgeServer):
        def __init__(self, kargs):
            super().__init__(kargs)
            self.data_queue = []
            self.model = None

        def update(self):
            if self.model is None:
                import evaluator
                self.model = evaluator.Evaluator()
            new_data = self.getDataBlocksAsArray()
            self.data_queue += new_data
            if len(self.data_queue) > 0:
                batch_data, socket_mapper, self.data_queue = bridge.server.slice_as_batch_size(self.data_queue, 4)
                logger.debug("EchoServer:update", self.data_queue, batch_data)
                self.model.eval(batch_data)
                stored_datablocks = bridge.server.pack_array_datablock(socket_mapper, batch_data)
                self.setDataBlocksFromArray(stored_datablocks)
            return len(new_data)

    args.protocol_stack = ProtocolStack
    sv = Server(args)

    def terminate(a, b):
        sv.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    sv.run()


if __name__ == "__main__":

    args = edict()
    args.ssl = False
    args.crt = None
    args.key = None
    args.host = "::0"
    args.port = 4649
    args.quality = 60


    image2image(args)

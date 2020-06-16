#!/usr/bin/env python3

import logging
import signal
import sys
import aimage
aimage.is_available_native_queue = True

import numpy as np
from easydict import EasyDict as edict

import aimage.eater.bridge as bridge

#from aimage.eater.application import image2image_server


def debug(*args, **kwargs):
    logger.debug(" ".join([str(s) for s in ['\033[1;30m', *args, '\033[0m']]), **kwargs)


def success(*args, **kwargs):
    logger.info(" ".join([str(s) for s in ['\033[0;32m', *args, '\033[0m']]), **kwargs)


def warn(*args, **kwargs):
    logger.warning(" ".join([str(s) for s in ['\033[0;31m', *args, '\033[0m']]), **kwargs)


def info(*args, **kwargs):
    logger.info(" ".join([str(s) for s in ['\033[0;36m', *args, '\033[0m']]), **kwargs)


def setup_log(name=__name__, level=logging.DEBUG):
    logger = logging.getLogger(name) if name is not None else logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(filename)s:%(lineno)d] %(message)s"))
    logger.addHandler(handler)
    # logger.info("info")
    # logger.debug("debug")
    # logger.warning("warning")
    # logger.error("error")
    # logger.critical("critical")
    return logger


setup_log("aimage.eater.bridge", level=logging.DEBUG)
logger = setup_log(__name__, logging.DEBUG)

args = edict()
args.ssl = False
args.crt = None
args.key = None
args.host = "localhost"
args.port = 3000
args.quality = 60


def echo():
    class ProtocolStack(bridge.server.StreamFactory):
        def build_protocol_stack(self, s):
            s.add_input_protocol(bridge.protocol.DirectStream())
            s.add_output_protocol(bridge.protocol.DirectStream())
            self.enable_info()

    class Server(bridge.server.EaterBridgeServer):
        def __init__(self, **kargs):
            super().__init__(**kargs)
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

    sv = Server(**args.__dict__)

    def terminate(a, b):
        sv.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    sv.run()


def data2data():
    class ProtocolStack(bridge.server.StreamFactory):
        def build_protocol_stack(self, s):
            s.add_input_protocol(bridge.protocol.LengthSplitIn())
            s.add_output_protocol(bridge.protocol.LengthSplitOut())
            self.enable_info()

    class Server(bridge.server.EaterBridgeServer):
        def __init__(self, **kargs):
            super().__init__(**kargs)
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
                #debug("EchoServer:update", self.data_queue, batch_data)
                stored_datablocks = bridge.server.pack_array_datablock(socket_mapper, batch_data)
                self.setDataBlocksFromArray(stored_datablocks)
            return len(new_data)

    args.protocol_stack = ProtocolStack
    sv = Server(**args.__dict__)

    def terminate(a, b):
        sv.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    sv.run()


def image2image(quality=60):
    class ProtocolStack(bridge.server.StreamFactory):
        def build_protocol_stack(self, s):
            s.add_input_protocol(bridge.protocol.LengthSplitIn())
            s.add_input_protocol(bridge.protocol.ImageDecoder())
            s.add_output_protocol(bridge.protocol.ImageEncoder(quality=quality))
            s.add_output_protocol(bridge.protocol.LengthSplitOut())
            self.enable_info()

    class Server(bridge.server.EaterBridgeServer):
        def __init__(self, **kargs):
            super().__init__(**kargs)
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
                #debug("EchoServer:update", self.data_queue, batch_data)
                batch_data = np.uint8(batch_data)
                for i in range(len(batch_data)):
                    img = batch_data[i]
                    r_image = self.model.eval(img)
                    batch_data[i] = r_image

                stored_datablocks = bridge.server.pack_array_datablock(socket_mapper, batch_data)
                self.setDataBlocksFromArray(stored_datablocks)
            return len(new_data)

    args.protocol_stack = ProtocolStack
    sv = Server(**args.__dict__)

    def terminate(a, b):
        sv.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    sv.run()


if __name__ == "__main__":
    # echo()
    # data2data()
    image2image()

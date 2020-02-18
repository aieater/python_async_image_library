#!/usr/bin/env python3
from __future__ import print_function
import os
def to_bool(s): return s in [1,'True','TRUE','true','1','yes','Yes','Y','y','t','on']
import inspect
DEBUG = False
if "DEBUG" in os.environ:
    DEBUG = to_bool(os.environ["DEBUG"])
    if DEBUG:
        try: import __builtin__
        except ImportError: import builtins as __builtin__
        import inspect
        def lpad(s,c): return s[0:c].ljust(c)
        def rpad(s,c):
            if len(s) > c: return s[len(s)-c:]
            else: return s.rjust(c)
        def print(*args, **kwargs):
            s = inspect.stack()
            __builtin__.print("\033[44m%s@%s(%s):\033[0m " % (rpad(s[1][1], 20), lpad(str(s[1][3]), 10), rpad(str(s[1][2]), 4)), end="")
            return __builtin__.print(*args, **kwargs)
def _pre_(): print("\033[A                                                                \033[A",flush=True)


from twisted.internet import reactor, protocol, endpoints
from twisted.protocols import basic
from twisted.internet import ssl, reactor

import traceback
import uuid
import cv2
import threading
import multiprocessing
import time
import struct
import numpy as np
import signal
import math
from bridge_protocol import StreamIO
import bridge_protocol as bp


class StackedServerSocketProtocol(protocol.Protocol):
    def __init__(self, factory, addr):
        self.addr = addr
        self.factory = factory
        self.input_middlewares = []
        self.output_middlewares = []
        self.is_available = False

        self.tm = time.time()
        self.in_ave_q = []
        self.out_ave_q = []
        self.bandwidth_inbound = 0
        self.bandwidth_outbound = 0
        self.total_inbound = 0
        self.total_outbound = 0
        self.queue_name = "default"

    def connectionMade(self):
        import aimage
        aimage.create_queue(self.queue_name)
        self.is_available = True
        self.uuid = str(uuid.uuid4())
        self.factory.clients[self.uuid] = self
        print("C:"+str(self.addr))

    def connectionLost(self, reason):
        import aimage
        aimage.delete_queue(self.queue_name)
        self.is_available = False
        del self.factory.clients[self.uuid]
        print("D:"+str(self.addr)+str(reason))

    def dataReceived(self, data):
        self.bandwidth_inbound += len(data)
        if self.is_available:
            self.input_middlewares[0].write(data)

    def update(self):
        if time.time() - self.tm > 1.0:
            if len(self.in_ave_q) > 3:
                self.in_ave_q.pop(0)
                self.out_ave_q.pop(0)
            self.in_ave_q.append(self.bandwidth_inbound)
            self.out_ave_q.append(self.bandwidth_outbound)
            print("%.2fMB/s, %.2fMB/s (I/O)" % ((np.mean(self.in_ave_q)/1024/1024), (np.mean(self.out_ave_q)/1024/1024)))
            self.tm = time.time()
            self.bandwidth_inbound = 0
            self.bandwidth_outbound = 0
        try:
            # From clients
            for i in range(len(self.input_middlewares)-1):
                b = self.input_middlewares[i].read(-1)
                if len(b):
                    self.input_middlewares[i+1].write(b)

            for m in self.input_middlewares:
                m.update()

            for i in range(len(self.output_middlewares)-1):
                b = self.output_middlewares[i].read(-1)
                if len(b):
                    self.output_middlewares[i+1].write(b)
            for m in self.output_middlewares:
                m.update()

            buf = self.output_middlewares[-1].read(-1)
            if len(buf) > 0:
                self.bandwidth_outbound += len(buf)
                self.transport.write(buf)
        except:
            traceback.print_exc()
            try:
                self.transport.close()
            except:
                pass

    def read(self, size=-1):
        if self.is_available:
            return self.input_middlewares[-1].read(size)
        return []

    def write(self, objects):
        if self.is_available:
            self.output_middlewares[0].write(objects)

class ObjectTable:
    def __init__(self):
        self.data_table = {}
        pass

    def setDataBlocks(self):
        pass

    def getDataBlocks(self):
        pass


class StreamFactory(protocol.Factory):
    def __init__(self, **kargs):
        self.quality = kargs["quality"]
        self.clients = {}
        self.update()

    def buildProtocol(self, addr):
        s = StackedServerSocketProtocol(self, addr)
        s.queue_name = str(uuid.uuid4())
        s.input_middlewares.append(bp.LengthSplitIn())
        s.input_middlewares.append(bp.ImageDecoder(queue_name=s.queue_name,))
        s.output_middlewares.append(bp.ImageEncoder(queue_name=s.queue_name, quality=self.quality))
        s.output_middlewares.append(bp.LengthSplitOut())
        # s.input_middlewares.append(bp.DirectStream())
        # s.output_middlewares.append(bp.DirectStream())
        return s

    def getDataBlocksAsArray(self, size=-1):
        socket_datamap_array = []
        for k in self.clients:
            client_socket = self.clients[k]
            block = client_socket.read()
            if len(block) > 0:
                for data in block:
                    socket_datamap_array.append({"socket": k, "data": data})
        return socket_datamap_array

    def setDataBlocksFromArray(self, socket_datamap_array):
        for obj in socket_datamap_array:
            k = obj["socket"]
            data = obj["data"]
            if k in self.clients:
                client_socket = self.clients[k]
                client_socket.write([data])

    def update(self):
        for k in self.clients:
            client_socket = self.clients[k]
            client_socket.update()
        reactor.callLater(0.001, self.update)

# batch_data,src_block,rest_block
def slice_as_batch_size(data_queue, batch_size):
    socket_mapper = []
    batch_data = []
    cnt = 0
    while len(socket_mapper) < batch_size and len(data_queue) > 0:
        obj = data_queue.pop(0)
        socket_mapper.append(obj)
        batch_data.append(obj["data"])
    return batch_data, socket_mapper, data_queue

def pack_array_datablock(socket_mapper, modified_data):
    dst_mapper = []
    pre = None
    for i in range(len(socket_mapper)):
        obj = socket_mapper[i]
        obj["data"] = modified_data[i]
        dst_mapper.append(obj)
    return dst_mapper


class EaterBridgeServer(object):
    def getDataBlocksAsArray(self, size=-1):
        try:
            if self.input_queue.empty() == False:
                obj = self.input_queue.get_nowait()
                return obj
        except:
            traceback.print_exc()
            pass
        return []

    def setDataBlocksFromArray(self, a):
        try:
            if self.output_queue.full() == False:
                self.output_queue.put_nowait(a)
        except:
            traceback.print_exc()
            return False
        return True

    # def getDataBlocksAsArray(self,size=-1):
    #     obj = self.input_queue.get_nowait()
    #     return self.factory.getDataBlocksAsArray(size)
    # def setDataBlocksFromArray(self,a):
    #     self.factory.setDataBlocksFromArray(a)
    def __init__(self, **kargs):
        self.input_queue = multiprocessing.Queue()
        self.output_queue = multiprocessing.Queue()
        self.signal_queue = multiprocessing.Queue()

        print("Start server", "tcp:"+str(kargs["port"]))
        parameter_block = []
        protocol = "tcp"
        if kargs["ssl"]:
            protocol = "ssl"
        parameter_block.append(protocol)
        parameter_block.append(str(kargs["port"]))
        if len(kargs["host"]):
            parameter_block.append("interface="+kargs["host"].replace(":", "\\:"))
        if len(kargs["key"]):
            parameter_block.append("privateKey="+kargs["key"])
        if len(kargs["crt"]):
            parameter_block.append("certKey="+kargs["crt"])
        self.factory = StreamFactory(**kargs)
        parameter = ":".join(parameter_block)
        print(parameter)
        endpoints.serverFromString(reactor, parameter).listen(self.factory)

        def runner(input_queue, output_queue, signal_queue):
            import aimage

            def __update__():
                try:
                    if input_queue.full() == False:
                        obj = self.factory.getDataBlocksAsArray(-1)
                        if len(obj) > 0:
                            input_queue.put_nowait(obj)
                except:
                    traceback.print_exc()
                    pass
                try:
                    if output_queue.empty() == False:
                        obj = output_queue.get_nowait()
                        self.factory.setDataBlocksFromArray(obj)
                    if signal_queue.empty() == False:
                        exit()
                except:
                    traceback.print_exc()
                    pass
                reactor.callLater(0.001, __update__)
            __update__()
            reactor.run(False)

        self.thread = multiprocessing.Process(target=runner, args=(self.input_queue, self.output_queue, self.signal_queue), daemon=True)
        self.thread.start()
        # self.thread = threading.Thread(target=runner,args=(self.input_queue,self.output_queue),daemon=True)
        # self.thread.start()

        # self.thread = multiprocessing.Process(target=reactor.run,args=(False,),daemon=True)
        # self.thread.start()
        # self.thread = threading.Thread(target=reactor.run,args=(False,))
        # self.thread.setDaemon(True)
        # self.thread.start()

    def update(self): pass

    def destroy(self):
        self.signal_queue.put_nowait(None)

    def run(self):
        while True:
            self.update()
            time.sleep(0.001)


if __name__ == '__main__':

    from PIL import Image, ImageFont, ImageDraw

    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--inference', type=str, default="demo_object_detection", help='')
    parser.add_argument('--ssl', action='store_true', help='')
    parser.add_argument('--crt', type=str, default="", help='signed certificate file path')
    parser.add_argument('--key', type=str, default="", help='private key file path')
    parser.add_argument('--port', type=int, default=3001, help='')
    parser.add_argument('--host', type=str, default="localhost", help='')
    parser.add_argument('--quality', type=int, default=85, help='')
    args = parser.parse_args()

    import eater_bridge_server as ebs

    class TestModel():
        def detect_image(self, img):
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    class DemoServer(ebs.EaterBridgeServer):
        def __init__(self, **kargs):
            super().__init__(**kargs)
            self.data_queue = []
            self.model = TestModel()

        def update(self):  # Override
            if self.model is None:
                pass
                # import yolov3
                # self.model = yolov3.YOLO()
            self.data_queue += bridge.getDataBlocksAsArray()
            if len(self.data_queue) > 0:
                batch_data, socket_mapper, self.data_queue = ebs.slice_as_batch_size(self.data_queue, 128)

                if self.model is not None:
                    batch_data = np.uint8(batch_data)
                    for i in range(len(batch_data)):
                        # batch_data[i] = cv2.cvtColor(batch_data[i],cv2.COLOR_BGR2RGB)

                        img = batch_data[i]

                        img = Image.fromarray(img)
                        # img = Image.fromarray(np.uint8(img))
                        r_image = self.model.detect_image(img)
                        r_image = np.asarray(r_image)
                        # r_image = cv2.resize(r_image,(img.shape[1],img.shape[0]))
                        # print(r_image)

                        batch_data[i] = r_image

                        # batch_data[i] = model.detect_image(np.array(batch_data[i]))
                        # data = batch_data[i]
                        # batch_data[i] = cv2.cvtColor(np.array(batch_data[i]),cv2.COLOR_BGR2RGB)

                stored_datablocks = ebs.pack_array_datablock(socket_mapper, batch_data)
                bridge.setDataBlocksFromArray(stored_datablocks)

    bridge = DemoServer(**args.__dict__)
    bridge.run()

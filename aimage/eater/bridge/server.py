#!/usr/bin/env python3
import datetime
import logging
import multiprocessing
import time
import uuid

import numpy as np
from twisted.internet import endpoints, protocol, reactor, ssl

from ..bridge import protocol as bp

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.setLevel(logging.DEBUG)
logger.propagate = True

DEBUG = False


def debug(*args, **kwargs):
    logger.debug(" ".join([str(s) for s in ['\033[1;30m', *args, '\033[0m']]), **kwargs)


def success(*args, **kwargs):
    logger.info(" ".join([str(s) for s in ['\033[0;32m', *args, '\033[0m']]), **kwargs)


def warn(*args, **kwargs):
    logger.warning(" ".join([str(s) for s in ['\033[0;31m', *args, '\033[0m']]), **kwargs)


def info(*args, **kwargs):
    logger.info(" ".join([str(s) for s in ['\033[0;36m', *args, '\033[0m']]), **kwargs)


class StackedServerSocketProtocol(protocol.Protocol):
    def __init__(self, factory, addr):
        super().__init__()
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
        self.description = ""

    def add_input_protocol(self, p):
        p.queue_name = self.queue_name
        self.input_middlewares.append(p)

    def add_output_protocol(self, p):
        p.queue_name = self.queue_name
        self.output_middlewares.append(p)

    def connectionMade(self):
        import aimage
        if aimage.is_native:
            aimage.create_queue(self.queue_name)
        self.is_available = True
        self.uuid = str(uuid.uuid4())
        self.factory.clients[self.uuid] = self
        #print("C:" + str(self.addr))

    def connectionLost(self, reason):
        import aimage
        if aimage.is_native:
            aimage.delete_queue(self.queue_name)
        self.is_available = False
        del self.factory.clients[self.uuid]
        #print("D:" + str(self.addr) + str(reason))

    def dataReceived(self, data):
        #info("TCP:READ:", data)
        self.bandwidth_inbound += len(data)
        if self.is_available:
            self.input_middlewares[0].write(data)

    def update(self):
        has_event = 0
        if time.time() - self.tm > 1.0:
            if len(self.in_ave_q) > 3:
                self.in_ave_q.pop(0)
                self.out_ave_q.pop(0)
            self.total_inbound += self.bandwidth_inbound
            self.total_outbound += self.bandwidth_outbound
            self.in_ave_q.append(self.bandwidth_inbound)
            self.out_ave_q.append(self.bandwidth_outbound)
            t = datetime.datetime.now()
            ts = f'{t.year}/{t.month}/{t.day} {str(t.hour).zfill(2)}:{str(t.minute).zfill(2)}:{str(t.second).zfill(2)}'
            self.description = "%s://%s:%s %s : I:%.2fMB/s, O:%.2fMB/s TI:%.2fMB, TO:%.2fMB" % (self.addr.type, self.addr.host, self.addr.port, ts, (np.mean(self.in_ave_q) / 1024 / 1024), (np.mean(self.out_ave_q) / 1024 / 1024), self.total_inbound / 1024 / 1024, self.total_outbound / 1024 / 1024)
            self.tm = time.time()
            self.bandwidth_inbound = 0
            self.bandwidth_outbound = 0
        try:
            # From clients
            for i in range(len(self.input_middlewares) - 1):
                b = self.input_middlewares[i].read(-1)
                if len(b):
                    self.input_middlewares[i + 1].write(b)
                    has_event += 1

            for m in self.input_middlewares:
                m.update()

            for i in range(len(self.output_middlewares) - 1):
                b = self.output_middlewares[i].read(-1)
                if len(b):
                    self.output_middlewares[i + 1].write(b)
                    has_event += 1
            for m in self.output_middlewares:
                m.update()

            buf = self.output_middlewares[-1].read(-1)
            if len(buf) > 0:
                self.bandwidth_outbound += len(buf)
                self.transport.write(buf)
                #info("TCP:WRITE:", buf)
                has_event += 1
        except Exception as e:
            warn(e)
            try:
                self.transport.close()
                has_event += 1
            except Exception as e:
                warn(e)
                pass
        return has_event

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
        super().__init__()
        self.previous_max_socket_num = 0
        self.enabled_info = False
        self.clients = {}
        self.log_tm = 0
        self.update()

    def build_protocol_stack(self, s):
        s.input_middlewares.append(bp.DirectStream())
        s.output_middlewares.append(bp.DirectStream())

    def buildProtocol(self, addr):
        s = StackedServerSocketProtocol(self, addr)
        s.queue_name = str(uuid.uuid4())
        self.build_protocol_stack(s)
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

    def enable_info(self):
        self.enabled_info = True

    def update(self):
        has_event = 0
        for k in self.clients:
            client_socket = self.clients[k]
            has_event += client_socket.update()
        t = time.time()
        if t - self.log_tm > 1.0:
            self.log_tm = t
            if self.enabled_info:
                for k in range(self.previous_max_socket_num):
                    print("\033[2A", flush=True)
                    print("\033[0K", end="\r")
                if len(self.clients) > 0:
                    for k in self.clients:
                        print(self.clients[k].description, flush=True)
                self.previous_max_socket_num = len(self.clients)
        reactor.callLater(0.001 if has_event > 0 else 0.02, self.update)


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
            if self.input_queue.empty() is False:
                obj = self.input_queue.get_nowait()
                return obj
        except Exception as e:
            warn(e)
            pass
        return []

    def setDataBlocksFromArray(self, a):
        try:
            if self.output_queue.full() is False:
                self.output_queue.put_nowait(a)
        except Exception as e:
            warn(e)
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
        self.signal_queue_r = multiprocessing.Queue()
        self.signal_queue_w = multiprocessing.Queue()

        if "port" not in kargs:
            raise Exception("Required parameter: port was None")
        if "host" not in kargs:
            raise Exception("Required parameter: host was None")

        info("Start server", "tcp:" + str(kargs["port"]))
        parameter_block = []
        protocol = "tcp"
        if "ssl" in kargs and kargs["ssl"]:
            protocol = "ssl"
            if "key" not in kargs:
                raise Exception("Required parameter: key was None")
            if "crt" not in kargs:
                raise Exception("Required parameter: crt was None")
            parameter_block.append("privateKey=" + kargs["key"])
            parameter_block.append("certKey=" + kargs["crt"])
        parameter_block.append(protocol)
        parameter_block.append(str(kargs["port"]))
        if len(kargs["host"]):
            parameter_block.append("interface=" + kargs["host"].replace(":", "\\:"))

        if "protocol_stack" in kargs:
            self.factory = kargs["protocol_stack"]()
        else:
            raise Exception("protocol_stack is required.")
        parameter = ":".join(parameter_block)
        info(parameter)
        endpoints.serverFromString(reactor, parameter).listen(self.factory)

        def runner(input_queue, output_queue, signal_queue_r, signal_queue_w):
            import aimage

            def __update__():
                has_event = 0
                try:
                    if input_queue.full() is False:
                        obj = self.factory.getDataBlocksAsArray(-1)
                        if len(obj) > 0:
                            input_queue.put_nowait(obj)
                            has_event += 1
                except Exception as e:
                    warn(e)
                    pass
                try:
                    if output_queue.empty() is False:
                        obj = output_queue.get_nowait()
                        self.factory.setDataBlocksFromArray(obj)
                        has_event += 1
                    if signal_queue_r.empty() is False:
                        signal_queue_w.put(1)
                        # End of application
                        return
                except Exception as e:
                    warn(e)
                    pass
                reactor.callLater(0.001 if has_event > 0 else 0.02, __update__)

            __update__()
            reactor.run(False)

        self.thread = multiprocessing.Process(target=runner, args=(self.input_queue, self.output_queue, self.signal_queue_r, self.signal_queue_w), daemon=True)
        self.thread.start()
        # self.thread = threading.Thread(target=runner,args=(self.input_queue,self.output_queue),daemon=True)
        # self.thread.start()

        # self.thread = multiprocessing.Process(target=reactor.run,args=(False,),daemon=True)
        # self.thread.start()
        # self.thread = threading.Thread(target=reactor.run,args=(False,))
        # self.thread.setDaemon(True)
        # self.thread.start()

    def update(self):
        return 0

    def destroy(self):
        try:
            self.signal_queue_r.put_nowait(None)
            self.signal_queue_w.get()
        except Exception as e:
            warn(e)

    def run(self):
        while True:
            has_event = self.update()
            if has_event == 0:
                time.sleep(0.01)

#!/usr/bin/env python3
import datetime
import logging
import multiprocessing
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid

import numpy as np
import psutil
import twisted.internet.endpoints
import twisted.internet.protocol
import twisted.internet.reactor
import twisted.internet.ssl

if platform.platform() == "Darwin":
    os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

logger = logging.getLogger(__name__)
if __name__ == "__main__":
    import protocol as bridge_protocol
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(filename)s:%(lineno)d] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
else:
    from . import protocol as bridge_protocol
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.DEBUG)
    logger.propagate = True

#################################################################################
# Util

cpu_usage = 0
gpu_usages = []
resource_watcher_queue = queue.Queue()
resource_watcher_thread = None


def resource_watcher(q):
    tm = time.time()
    ROCM_SMI = shutil.which('rocm-smi')
    NVIDIA_SMI = shutil.which('nvidia-smi')
    while True:
        try:
            if time.time() - tm > 2.0:
                if NVIDIA_SMI:
                    try:
                        a = subprocess.check_output("nvidia-smi | grep MiB | grep Default", shell=True).decode("utf-8")
                        if "MiB" in a:
                            index = 0
                            sp = a.split("\n")
                            # canvas = np.zeros((128, 256, 3), dtype=np.uint8)
                            cpu_usage = psutil.cpu_percent()
                            # aimage.draw_text(canvas, "CPU: {}%".format(rpad(str(cpu_usage), 4)), 5, 20 + 20 * index)
                            gpu_usages = []
                            for b in sp:
                                if "Default" in b:
                                    usage = b.split("|")[3].replace("Default", "").strip()
                                    memory = b.split("|")[2].split("/")[0].strip()
                                    # mes = "{} {} {}".format(index, rpad(usage, 4), rpad(memory, 10))
                                    gpu_usages += [[index, usage, memory]]
                                    # aimage.draw_text(canvas, mes, 5, 20 + 20 * (index + 1))
                                    index += 1
                            # aimage.save_image(os.path.join(os.path.dirname(__file__), ".gpu.jpg"), canvas)
                            q.put((cpu_usage, gpu_usages))
                    except Exception as e:
                        pass
                if ROCM_SMI:
                    try:
                        a = subprocess.check_output("rocm-smi | grep Mhz", shell=True).decode("utf-8")
                        if "Mhz" in a:
                            # GPU  Temp   AvgPwr  SCLK    MCLK    Fan     Perf  PwrCap  VRAM%  GPU%
                            # 0    33.0c  18.0W   808Mhz  350Mhz  21.96%  auto  250.0W    0%   0
                            index = 0
                            sp = a.split("\n")
                            # canvas = np.zeros((128, 256, 3), dtype=np.uint8)
                            cpu_usage = psutil.cpu_percent()
                            # aimage.draw_text(canvas, "CPU: {}%".format(rpad(str(cpu_usage), 4)), 5, 20 + 20 * index)
                            gpu_usages = []
                            for b in sp:
                                if "Mhz" in b:
                                    ss = re.findall(r"\S+", b)
                                    gpu_indx = ss[0]
                                    temp = ss[1]
                                    avgpwr = ss[2]
                                    sclk = ss[3]
                                    mclk = ss[4]
                                    fan = ss[5]
                                    perf = ss[6]
                                    pwrcap = ss[7]
                                    vram = ss[8]
                                    gpu_usage = ss[9]
                                    gpu_mem = vram
                                    if len(ss) == 11:
                                        gpu_mem = ss[10]
                                    # mes = "{} {} {}".format(index, rpad(usage, 4), rpad(memory, 10))
                                    gpu_usages += [[gpu_indx, gpu_usage, gpu_mem]]
                                    # aimage.draw_text(canvas, mes, 5, 20 + 20 * (index + 1))
                                    index += 1
                            # aimage.save_image(os.path.join(os.path.dirname(__file__), ".gpu.jpg"), canvas)
                            q.put((cpu_usage, gpu_usages))
                    except Exception as e:
                        pass
                tm = time.time()
            else:
                time.sleep(0.5)
        except Exception as e:
            time.sleep(0.5)


def gpu_log():
    global cpu_usage, gpu_usages, resource_watcher_thread, resource_watcher_queue
    if resource_watcher_thread is None:
        resource_watcher_thread = threading.Thread(name="gpu_log", target=resource_watcher, args=(resource_watcher_queue, ), daemon=True)
        resource_watcher_thread.start()
    try:
        cpu_usage, gpu_usages = resource_watcher_queue.get_nowait()
    except:
        pass
    return cpu_usage, gpu_usages


class StackedServerSocketProtocol(twisted.internet.protocol.Protocol):
    def __init__(self, global_factory, addr):
        super().__init__()
        self.addr = addr
        self.global_factory = global_factory
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
        self.uuid = str(uuid.uuid4())
        self.description = ""

    def add_input_protocol(self, p):
        p.queue_name = self.uuid
        self.input_middlewares.append(p)

    def add_output_protocol(self, p):
        p.queue_name = self.uuid
        self.output_middlewares.append(p)

    def connectionMade(self):
        import aimage
        if aimage.is_native:
            cores = multiprocessing.cpu_count()
            aimage.rebuild_worker(cores)
            aimage.create_queue(self.uuid)
        self.is_available = True
        self.global_factory.clients[self.uuid] = self
        #print("C:" + str(self.addr))

    def connectionLost(self, reason):
        import aimage
        if aimage.is_native:
            aimage.delete_queue(self.uuid)
        self.is_available = False
        del self.global_factory.clients[self.uuid]
        #print("D:" + str(self.addr) + str(reason))

    def dataReceived(self, data):
        #logger.debug("TCP:READ:", data[0:10])
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
        if self.is_available is False: return

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
                #logger.debug("TCP:WRITE:", buf[0:10])
                has_event += 1
        except Exception as e:
            logger.warning(e)
            try:
                self.transport.close()
                has_event += 1
            except Exception as e:
                logger.warning(e)
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


class StreamFactory(twisted.internet.protocol.Factory):
    def __init__(self, **kargs):
        super().__init__()
        self.previous_max_socket_num = 0
        self.enabled_info = False
        self.clients = {}
        self.log_tm = time.time() + 1.0
        self.update()

    def build_protocol_stack(self, s):
        s.add_input_protocol(bridge_protocol.DirectStream())
        s.add_output_protocol(bridge_protocol.DirectStream())

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
        if self.enabled_info:
            t = time.time()
            if t - self.log_tm > 1.0:
                self.log_tm = t
                cpu_usage, gpu_usages = gpu_log()
                mem = psutil.virtual_memory()
                cpu_res = 'C:{}% '.format(cpu_usage)
                gpu_ress = []
                for g in gpu_usages:
                    gpu_ress += ['G({}:{}:{})'.format(g[0], g[1], g[2])]
                mresources = '[{}M:{:.2f}MB({}%)] [{}]'.format(cpu_res, mem.used / 1024 / 1024, mem.percent, ",".join(gpu_ress))
                print("\033[0K", end="", flush=True)
                print(mresources, flush=True)
                for k in self.clients:
                    print("\033[0K", end="", flush=True)
                    print(self.clients[k].description, flush=True)
                clen = len(self.clients.keys())
                if self.previous_max_socket_num > clen:
                    for i in range(self.previous_max_socket_num - clen):
                        print("\033[0K", end="\n", flush=True)
                for k in range(max(self.previous_max_socket_num, clen)):
                    print("\033[1A", end="\r", flush=True)
                self.previous_max_socket_num = clen
                print("\033[1A", end="\r", flush=True)
        twisted.internet.reactor.callLater(0.001 if has_event > 0 else 0.02, self.update)


# batch_data,src_block,rest_block
def slice_as_batch_size(data_queue, batch_size):
    socket_mapper = []
    batch_data = []
    while len(socket_mapper) < batch_size and len(data_queue) > 0:
        obj = data_queue.pop(0)
        socket_mapper.append(obj)
        batch_data.append(obj["data"])
    return batch_data, socket_mapper, data_queue


def pack_array_datablock(socket_mapper, modified_data):
    dst_mapper = []
    for i in range(len(socket_mapper)):
        obj = socket_mapper[i]
        obj["data"] = modified_data[i]
        dst_mapper.append(obj)
    return dst_mapper


class EaterBridgeServer():
    def getDataBlocksAsArray(self, size=-1):
        try:
            if self.input_queue.empty() is False:
                obj = self.input_queue.get_nowait()
                return obj
        except Exception as e:
            logger.warning(e)
            pass
        return []

    def setDataBlocksFromArray(self, a):
        try:
            if self.output_queue.full() is False:
                self.output_queue.put_nowait(a)
        except Exception as e:
            logger.warning(e)
            return False
        return True

    # def getDataBlocksAsArray(self,size=-1):
    #     obj = self.input_queue.get_nowait()
    #     return self.factory.getDataBlocksAsArray(size)
    # def setDataBlocksFromArray(self,a):
    #     self.factory.setDataBlocksFromArray(a)
    def __init__(self, _dict={}, **kargs):
        for k in kargs:
            _dict[k] = kargs[k]
        kargs = _dict

        if "VSCODE_DEUBG" in os.environ:
            self.input_queue = queue.Queue()
            self.output_queue = queue.Queue()
            self.signal_queue_r = queue.Queue()
            self.signal_queue_w = queue.Queue()
        else:
            self.input_queue = multiprocessing.Queue()
            self.output_queue = multiprocessing.Queue()
            self.signal_queue_r = multiprocessing.Queue()
            self.signal_queue_w = multiprocessing.Queue()

        if "port" not in kargs:
            raise Exception("Required parameter: port was None")
        if "host" not in kargs:
            raise Exception("Required parameter: host was None")

        logger.info("Start server tcp:" + str(kargs["port"]))
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
        logger.info(parameter)
        twisted.internet.endpoints.serverFromString(twisted.internet.reactor, parameter).listen(self.factory)

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
                    logger.warning(e)
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
                    logger.warning(e)
                    pass
                twisted.internet.reactor.callLater(0.001 if has_event > 0 else 0.02, __update__)

            __update__()
            twisted.internet.reactor.run(False)

        #runner(self.input_queue, self.output_queue, self.signal_queue_r, self.signal_queue_w)
        #multiprocessing.set_start_method('spawn', True)

        if "VSCODE_DEUBG" in os.environ:
            self.thread = threading.Thread(target=runner, args=(self.input_queue, self.output_queue, self.signal_queue_r, self.signal_queue_w), daemon=True)
        else:
            self.thread = multiprocessing.Process(target=runner, args=(self.input_queue, self.output_queue, self.signal_queue_r, self.signal_queue_w), daemon=True)
        self.thread.start()

    def update(self):
        return 0

    def destroy(self):
        try:
            self.signal_queue_r.put_nowait(None)
            self.signal_queue_w.get()
        except Exception as e:
            logger.warning(e)

    def run(self):
        while True:
            has_event = self.update()
            if has_event == 0:
                time.sleep(0.01)


if __name__ == "__main__":
    from easydict import EasyDict as edict
    import signal

    class ProtocolStack(StreamFactory):
        def build_protocol_stack(self, s):
            s.add_input_protocol(bridge_protocol.LengthSplitIn())
            s.add_input_protocol(bridge_protocol.ImageDecoder())
            s.add_output_protocol(bridge_protocol.ImageEncoder(quality=args.quality))
            s.add_output_protocol(bridge_protocol.LengthSplitOut())
            self.enable_info()

    class Server(EaterBridgeServer):
        def __init__(self, **kargs):
            super().__init__(kargs)
            self.data_queue = []
            self.model = None

        def update(self):
            new_data = self.getDataBlocksAsArray()
            self.data_queue += new_data
            if len(self.data_queue) > 0:
                batch_data, socket_mapper, self.data_queue = slice_as_batch_size(self.data_queue, 4)
                #self.model.eval(batch_data)
                stored_datablocks = pack_array_datablock(socket_mapper, batch_data)
                self.setDataBlocksFromArray(stored_datablocks)
            return len(new_data)

    args = edict()
    args.ssl = False
    args.crt = None
    args.key = None
    args.host = "::0"
    args.port = 4649
    args.quality = 60

    args.protocol_stack = ProtocolStack
    sv = Server(**args.__dict__)

    def terminate(a, b):
        sv.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    sv.run()

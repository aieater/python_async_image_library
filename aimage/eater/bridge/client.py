#!/usr/bin/env python3
import logging
import math
import os
import platform
import queue
import sys
import threading
import uuid
import multiprocessing

import twisted.internet.protocol
import twisted.internet.reactor

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


def estimate_retry_delay_time(r, max_delay=10):
    s = math.exp(r / 1.5)
    return s if s < 10 else 10


class StackedClientSocketProtocol(twisted.internet.protocol.Protocol):
    def __init__(self, rq, wq):
        self.rq = rq
        self.wq = wq
        self.input_middlewares = []
        self.output_middlewares = []
        self.is_available = False
        self.is_invalid_socket = False
        self.uuid = str(uuid.uuid4())

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

    def connectionLost(self, reason):
        import aimage
        if aimage.is_native:
            aimage.delete_queue(self.uuid)
        self.is_available = False

    def dataReceived(self, data):
        #logger.info("TCP:READ:", data)
        if self.is_available:
            self.input_middlewares[0].write(data)

    def update(self):
        try:
            if self.is_invalid_socket: return
            if self.is_available is False: return
            try:
                # From opponent
                for i in range(len(self.input_middlewares) - 1):
                    b = self.input_middlewares[i].read()
                    if len(b):
                        self.input_middlewares[i + 1].write(b)
                for m in self.input_middlewares:
                    m.update()
                # To opponent
                for i in range(len(self.output_middlewares) - 1):
                    b = self.output_middlewares[i].read()
                    if len(b):
                        self.output_middlewares[i + 1].write(b)
                for m in self.output_middlewares:
                    m.update()
                buf = self.output_middlewares[-1].read(-1)
                if self.is_available and len(buf) > 0:
                    self.transport.write(buf)
                    #logger.info("TCP:WRITE:", buf)
            except Exception as e:
                logger.warning(e)
                self.is_invalid_socket = True
                try:
                    self.transport.close()
                    self.wq.clear()
                    self.rq.clear()
                except Exception as e:
                    logger.warning(e)
            while self.rq.empty() is False:
                o = self.rq.get_nowait()
                self.output_middlewares[0].write(o)

            b = self.input_middlewares[-1].read(-1)
            if len(b) > 0:
                self.wq.put_nowait(b)
        except Exception as e:
            logger.warning(e)


class StreamClientFactory(twisted.internet.protocol.ClientFactory):
    def __init__(self, rq, wq, **kwargs):
        self.rq = rq
        self.wq = wq
        self.retry = 0
        self.retying = False
        self.connected = False
        self.protocol_instance = None
        self.addr = None
        self.kwargs = kwargs
        self.update()

    def startedConnecting(self, connector):
        logger.info(f'Started to connect. {connector.host}:{connector.port} Timeout:{connector.timeout}')

    # Override
    def on_disconnected(self):
        pass

    # Override
    def on_connected(self):
        self.protocol_instance.add_input_protocol(bridge_protocol.DirectStream())
        self.protocol_instance.add_output_protocol(bridge_protocol.DirectStream())

    def buildProtocol(self, addr):
        self.addr = addr
        self.retry = 0
        self.retying = False
        self.connected = True
        logger.info(f'Connected {addr.type}://{addr.host}:{addr.port}')
        s = StackedClientSocketProtocol(self.rq, self.wq)
        self.protocol_instance = s
        self.on_connected()
        return s

    def update(self):
        if self.protocol_instance:
            self.protocol_instance.update()
            if self.protocol_instance.is_invalid_socket:
                self.protocol_instance = None
        twisted.internet.reactor.callLater(0.001, self.update)

    def deferred_connect(self, args):
        if self.retying is False and self.connected is False:
            self.retying = True
            self.retry += 1
            args[0].connect()

    def clientConnectionLost(self, connector, reason):
        delay = estimate_retry_delay_time(self.retry)
        logger.warning(f'Lost connection. RetryDelay:[{self.retry}]:{round(delay,2)}s\n  Reason: {reason}')
        self.on_disconnected()
        self.connected = False
        self.retying = False
        twisted.internet.reactor.callLater(delay, self.deferred_connect, (connector, ))

    def clientConnectionFailed(self, connector, reason):
        delay = estimate_retry_delay_time(self.retry)
        logger.warning(f'Connection failed. RetryDelay:[{self.retry}]:{round(delay,2)}s\n  Reason: {reason}')
        self.on_disconnected()
        self.connected = False
        self.retying = False
        twisted.internet.reactor.callLater(delay, self.deferred_connect, (connector, ))


class EaterBridgeClient:
    def __init__(self, **kargs):
        self.kargs = kargs
        self.host = kargs["host"]
        self.port = kargs["port"]
        self.rq = queue.Queue()
        self.wq = queue.Queue()
        self.protocol_stack = kargs["protocol_stack"](self.rq, self.wq, **self.kargs)

    def start(self):
        self.deferred = twisted.internet.reactor.connectTCP(self.host, self.port, self.protocol_stack)
        # self.deferred = twisted.internet.reactor.connectSSL(self.host, self.port, StreamClientFactory(self.rq,self.wq),twisted.internet.ssl.ClientContextFactory())
        self.thread = threading.Thread(target=twisted.internet.reactor.run, args=(False, ))
        self.thread.setDaemon(True)
        self.thread.start()

    def destroy(self):
        twisted.internet.reactor.stop()
        # self.thread.stop()

    def write(self, blocks):
        if self.rq.empty():
            self.rq.put(blocks)
            return True
        return False

    def read(self, size=-1):
        if self.wq.empty() is False:
            return self.wq.get()
        return None


def echo(HOST, PORT):
    class ProtocolStack(bridge.client.StreamClientFactory):
        def on_connected(self):
            s = self.protocol_instance
            s.add_input_protocol(bridge.protocol.DirectStream())
            s.add_output_protocol(bridge.protocol.DirectStream())

        def on_disconnected(self):
            pass

    c = bridge.client.EaterBridgeClient(host=HOST, port=PORT, protocol_stack=ProtocolStack)
    c.start()

    def terminate(a, b):
        c.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
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
            logger.warning(data)
            request_count -= len(data)
        else:
            time.sleep(0.01)


def data2data(HOST, PORT):
    class ProtocolStack(bridge.client.StreamClientFactory):
        def on_connected(self):
            s = self.protocol_instance
            s.add_input_protocol(bridge.protocol.LengthSplitIn())
            s.add_output_protocol(bridge.protocol.LengthSplitOut())

        def on_disconnected(self):
            pass

    c = bridge.client.EaterBridgeClient(host=HOST, port=PORT, protocol_stack=ProtocolStack)
    c.start()

    def terminate(a, b):
        c.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    request_count = 0
    fps_count = 0
    st = time.time()
    while True:
        if request_count < 2:
            if time.time() - st > 1.0:
                logger.info("FPS: " + fps_count)
                st = time.time()
                fps_count = 0
            fps_count += 1

            datas = ["test", "test2"]
            logger.info(f"Main:send({request_count}): " + datas)
            c.write(datas)
            request_count += 2
        blocks = c.read()
        if blocks is not None:
            if isinstance(blocks, list):
                for data in blocks:
                    request_count -= 1
                    # TODO list / bytes
                    logger.info(f"Main:response({request_count}): " + data.decode('utf-8'))
                    # for data in extend:
                    #     print(data.decode('utf-8'))
                    # blocks = client.read()
                    # for img in blocks:
                    #     aimage.show(img)
        else:
            time.sleep(0.01)

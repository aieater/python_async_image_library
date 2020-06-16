#!/usr/bin/env python3
import logging
import struct

import numpy as np

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


def check_type(d, name):
    if DEBUG:
        debug(name, type(d))


def to_bytes(d):
    if isinstance(d, bytes):
        return bytearray(d)
    if isinstance(d, bytearray):
        return d
    if isinstance(d, str):
        return d.encode('utf-8')
    if isinstance(d, list):
        return bytearray(d)
    if type(d).__module__ == np.__name__:
        return bytearray(d)
    return False


class StreamIO:
    def __init__(self):
        self.b = bytearray()

    def read(self, size=-1):
        _b = self.b
        if size == -1:
            # Return all
            self.b = bytearray()
            return _b
        # Return sliced buffer
        bb = _b[0:size]
        self.b = _b[size:]
        return bb

    def getbuffer(self):
        return self.b

    def write(self, data):
        _data = to_bytes(data)
        slen = 0
        if _data:
            slen = len(_data)
            self.b.extend(_data)
            return slen
        else:
            ex = "expected type is bytes. Got object was " + str(type(data))
            warn(ex)
            raise ex
        return slen

    def size(self):
        return len(self.b)

    def length(self):
        return len(self.b)


class DirectStream:
    def __init__(self):
        self.queue_name = None
        self.buffer = StreamIO()

    def write(self, data):
        return self.buffer.write(data)

    def read(self, size=-1):
        return self.buffer.read(size)

    def update(self):
        pass

    def info(self):
        return "DirectStream: TCP stream <bytes> => <bytes>"


class LengthSplitIn:  # Stream(socket) to Blocks
    def __init__(self, max_buffer_size=1024 * 1024 * 10):
        self.queue_name = None
        self.buffer = StreamIO()
        self.blocks = []
        self.max_buffer_size = max_buffer_size

    # stream to blocks
    def write(self, data):
        #debug("LengthSplitIn:write:I", data)
        slen = len(data)
        blen = self.buffer.length()
        check_type(data, "W:LengthSplitIn")
        if slen + blen > self.max_buffer_size:
            debug("LengthSplitIn:write", "Data size:", slen, "Buffer size:", blen)
            raise Exception("too much data size")
        self.buffer.write(data)
        buf = self.buffer.getbuffer()
        # More than header size
        while len(buf) >= 4:
            body_length = struct.unpack_from(">I", buf[0:4])[0]
            # Has contents
            if len(buf) >= 4 + body_length:
                head = self.buffer.read(4)
                (head)
                body = self.buffer.read(body_length)
                # debug("LengthSplitIn:write:R", body)
                self.blocks.append(body)
                buf = self.buffer.getbuffer()
            else:
                break
        return slen

    # blocks (extracted)
    def read(self, size=-1):
        if size == -1:
            _blocks = self.blocks
            self.blocks = []
            return _blocks
        _blocks = self.blocks[0:size]
        self.blocks = self.blocks[size:]
        return _blocks

    def update(self):
        pass

    def info(self):
        return "LengthSplitIn: Data block <bytes(<int,bytes,int,bytes,>)> => <[<bytes>,]>"


class LengthSplitOut:  # Block(s) to Stream(socket)
    def __init__(self, max_buffer_size=1024 * 1024 * 10):
        self.queue_name = None
        self.buffer = StreamIO()
        self.max_buffer_size = max_buffer_size

    # single data block to stream
    def write(self, blocks):
        check_type(blocks, "W:LengthSplitOut")

        tlen = 0
        blen = self.buffer.length()
        for data in blocks:
            tlen += len(data)
        if tlen + blen > self.max_buffer_size:
            debug("LengthSplitOut:write", "Data size:", tlen, "Buffer size:", blen)
            raise Exception("too much data size")

        for data in blocks:
            slen = len(data)
            blen = slen.to_bytes(4, 'big')
            self.buffer.write(blen)
            self.buffer.write(data)

        return tlen

    # stream (to socket)
    def read(self, size=-1):
        return self.buffer.read(size)

    def update(self):
        pass

    def info(self):
        return "LengthSplitOut: Data block <[<bytes>,]> => <bytes(<int,bytes,int,bytes,>)>"


class ImageDecoder:  # Blocks to Blocks
    def __init__(self, *, queue_name="default"):
        self.input_blocks = []
        self.processing_map = {}
        self.output_blocks = []
        self.rcv_index = 0
        self.req_index = 0
        self.queue_name = queue_name

    def write(self, blocks):
        check_type(blocks, "W:ImageDecoder")
        slen = 0
        for data in blocks:
            slen += len(data)
            self.input_blocks.append(data)
        return slen

    def read(self, size=-1):
        if size == -1:
            blocks = self.output_blocks
            self.output_blocks = []
            return blocks
        blocks = self.output_blocks[0:size]
        self.output_blocks = self.output_blocks[size:]
        return blocks

    def update(self):
        import aimage
        try:
            if aimage.is_native:
                if aimage.is_available_native_queue:
                    objs = []
                    for b in self.input_blocks:
                        objs.append({"input_buffer": b, "id": self.req_index})
                        self.req_index += 1
                    if len(objs) > 0:
                        aimage.decode_input(objs, self.queue_name)
                    self.input_blocks = []

                    ret = aimage.decode_output(self.queue_name)
                    if len(ret) > 0:
                        for obj in ret:
                            self.processing_map[obj["index"]] = obj
                    while True:
                        obj = self.processing_map.pop(self.rcv_index, None)
                        if obj:
                            self.output_blocks.append(obj["data"])
                            self.rcv_index += 1
                        else:
                            break
                else:
                    # for b in self.input_blocks: self.output_blocks.append(aimage.native_decoder(b))
                    for b in self.input_blocks:
                        self.output_blocks.append(aimage.native_fast_decoder(b))  # x3~x4 faster than OpenCV imdecode loader.
                    self.input_blocks = []
            else:
                # for b in self.input_blocks: self.output_blocks.append(aimage.native_decoder(b))
                for b in self.input_blocks:
                    self.output_blocks.append(aimage.opencv_decoder(b))
                self.input_blocks = []
        except Exception as e:
            warn(e)
            print(e)

    def info(self):
        return "ImageDecoder: Image data block <[<bytes>,]> => <[<ndarray>,]>"


class ImageEncoder:  # Blocks to Blocks
    def __init__(self, *, queue_name="default", quality=90):
        self.input_blocks = []
        self.processing_map = {}
        self.output_blocks = []
        self.req_index = 0
        self.rcv_index = 0
        self.queue_name = queue_name
        self.quality = quality

    def write(self, blocks):
        slen = 0
        check_type(blocks, "W:ImageEncoder")
        if isinstance(blocks, list) is False:
            raise Exception("Arg must be list(numpy,numpy,...)")
        for data in blocks:
            slen += len(data)
            self.input_blocks.append(np.uint8(data))
        return slen

    def read(self, size=-1):
        if size == -1:
            blocks = self.output_blocks
            self.output_blocks = []
            return blocks
        blocks = self.output_blocks[0:size]
        self.output_blocks = self.output_blocks[size:]
        return blocks

    def update(self):
        import aimage
        try:
            if aimage.is_native:
                if aimage.is_available_native_queue:
                    objs = []
                    for b in self.input_blocks:
                        # encode_input:
                        # [
                        #   {
                        #     id: int,
                        #     input_buffer: ndarray,
                        #   },
                        # ]
                        objs.append({"input_buffer": b, "id": self.req_index})
                        # objs.append({"input_buffer": b, "id": self.req_index})
                        self.req_index += 1
                    if len(objs) > 0: aimage.encode_input(objs, self.quality, "jpg", self.queue_name)
                    self.input_blocks = []

                    ret = aimage.encode_output(self.queue_name)

                    # encode_output:
                    # [
                    #   {
                    #     index: int
                    #     data: ndarray,
                    #   },
                    # ]
                    if len(ret) > 0:
                        for obj in ret:
                            self.processing_map[obj["index"]] = obj
                    while True:
                        obj = self.processing_map.pop(self.rcv_index, None)
                        if obj:
                            self.output_blocks.append(obj["data"])
                            self.rcv_index += 1
                        else:
                            break
                else:
                    # for b in self.input_blocks: self.output_blocks.append(aimage.native_encoder(b))
                    for b in self.input_blocks:
                        self.output_blocks.append(aimage.native_fast_encoder(b))  # x3~x4 faster than OpenCV imdecode loader.
                        # self.output_blocks.append(aimage.native_encoder(b, quality=self.quality, format="jpg"))
                    self.input_blocks = []
            else:
                # for b in self.input_blocks: self.output_blocks.append(aimage.native_encoder(b))
                for b in self.input_blocks:
                    self.output_blocks.append(aimage.opencv_encoder(b))
                self.input_blocks = []
        except Exception as e:
            print("Critical:", e)
            warn(e)
            exit(9)

    def info(self):
        return "ImageEncoder: Image data block <[<ndarray>,]> => <[<bytes>,]>"


def protocols():
    debug(DirectStream().info())
    debug(LengthSplitIn().info())
    debug(LengthSplitOut().info())
    debug(ImageDecoder().info())
    debug(ImageEncoder().info())


if __name__ == '__main__':
    debug("=============================================")
    protocols()
    debug("=============================================")

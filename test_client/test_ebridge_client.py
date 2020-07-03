#!/usr/bin/env python3

import logging
import multiprocessing
import os
import signal
import sys
import time

import cselector
import cv2
import numpy as np
import psutil
import pyglview
from easydict import EasyDict as edict

import aimage
import aimage.eater.bridge as bridge

aimage.is_available_native_queue = True

os.chdir(os.path.dirname(os.path.abspath(__file__)))


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


def image2image(HOST, PORT, fd, quality):
    cap = aimage.open(fd)

    class ProtocolStack(bridge.client.StreamClientFactory):
        def on_connected(self):
            s = self.protocol_instance
            s.add_output_protocol(bridge.protocol.ImageEncoder(quality=quality))
            s.add_output_protocol(bridge.protocol.LengthSplitOut())

            s.add_input_protocol(bridge.protocol.LengthSplitIn())
            s.add_input_protocol(bridge.protocol.ImageDecoder())

        def on_disconnected(self):
            pass

    client_socket = bridge.client.EaterBridgeClient(host=HOST, port=PORT, protocol_stack=ProtocolStack)
    client_socket.start()

    def terminate(a, b):
        client_socket.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)

    req_queue_count = 0
    req_fps_cache = 0
    req_fps_count = 0
    v_fps_count = 0
    v_fps_cache = 0
    time_cache = 0

    vargs = edict()
    vargs.keyboard_listener = cap.keyboard_listener
    vargs.cpu = False
    vargs.double_buffer = True
    vargs.fullscreen = False
    vargs.fps = cap.fps
    vargs.quality = quality
    vargs.window_x = 50
    vargs.window_y = 50
    vargs.window_width = int(cap.width)
    vargs.window_height = int(cap.height)
    frame_times = np.zeros((vargs.window_width, 4), dtype=np.float32)
    frame_time_queue = []
    frame_index = 0
    f_fps_cache = 0
    f_fps_count = 0
    previous_time = 0
    fps_limit = 1.0 / vargs.fps

    def tob(b):
        return 'T' if b else 'F'

    display_info = f'CPU:{tob(vargs.cpu)} DBf:{tob(vargs.double_buffer)} FS:{tob(vargs.fullscreen)} {int(vargs.window_width)}x{int(vargs.window_height)} sFPS:{vargs.fps}'

    view = pyglview.Viewer(**vargs)
    message = ""
    previous_img = None

    def loop():
        nonlocal previous_img, client_socket, fps_limit, previous_time, time_cache, cap, view, f_fps_count, f_fps_cache, v_fps_count, v_fps_cache, req_fps_cache, req_fps_count, req_queue_count, message, frame_times, frame_time_queue, frame_index
        now = time.time()
        if now - time_cache > 1.0:
            mem = psutil.virtual_memory()
            cpu_res = f'CPU:{str(psutil.cpu_percent()).rjust(4)}% '
            mresources = '{}{}MB({}%)'.format(cpu_res, str(round(mem.used / 1024 / 1024, 2)).rjust(8), str(round(mem.percent, 1)).rjust(4))
            v_fps_cache = v_fps_count
            req_fps_cache = req_fps_count
            f_fps_cache = f_fps_count
            message = f"CFPS:{str(f_fps_cache).rjust(3)} GLFPS:{str(v_fps_cache).rjust(3)} REQ:{str(req_fps_cache).rjust(3)} {mresources}"

            print("\033[0K", end="", flush=True)
            print(message, flush=True)
            print("\033[1A", end="", flush=True)

            time_cache = now
            v_fps_count = 0
            req_fps_count = 0
            f_fps_count = 0

        LIMIT_REQ = 8
        LIMIT_HF_REQ = 5
        if req_fps_cache < 20:
            LIMIT_REQ = 4
            LIMIT_HF_REQ = 3
        elif req_fps_cache < 30:
            LIMIT_REQ = 5
            LIMIT_HF_REQ = 4
        elif req_fps_cache < 40:
            LIMIT_REQ = 6
            LIMIT_HF_REQ = 4
        elif req_fps_cache < 50:
            LIMIT_REQ = 7
            LIMIT_HF_REQ = 5

        if req_queue_count <= LIMIT_REQ and now - previous_time >= (1.0 / (req_fps_cache + 1) * 0.90):
            previous_time = now
            push = True
            if req_queue_count >= LIMIT_HF_REQ:
                push = False
                previous_time = previous_time - (1.0 / (req_fps_cache + 1) * 0.90) * 0.9
            if push:
                check, img = cap.read()
                if previous_img is not None:
                    if img is previous_img:
                        check = False
                    else:
                        pass
                previous_img = img
                if check:
                    client_socket.write([img])
                    req_queue_count += 1
                    frame_time_queue.append(now)
        img = None
        blocks = client_socket.read()
        if blocks is not None:
            if isinstance(blocks, list):
                for data in blocks:
                    if img is None: img = np.array(data)
                    sub = now - frame_time_queue.pop(0)
                    sub *= 1000
                    req_queue_count -= 1
                    req_fps_count += 1
        if img is not None:
            aimage.draw_title(img=img, message=display_info + f' {str(int(sub)).rjust(4)}ms B:{str(req_queue_count).rjust(2)}')
            aimage.draw_footer(img=img, message=message)
            view.set_image(img)
            frame_index += 1
            v_fps_count += 1
        f_fps_count += 1

    view.set_loop(loop)
    view.start()


if __name__ == "__main__":
    servers = [
        edict({
            "title": "Local Development",
            "service": "None",
            "host": "localhost",
            "port": 4649,
            "ssl": None,
            "key": None,
        }),
        edict({
            "title": "Face Detector EfficientDetB0",
            "host": "240d:1a:1c6:2400:216:3eff:fec8:25e8",
            "service": "efficient_detb0",
            "port": 3000,
            "ssl": None,
            "key": None,
        }),
        edict({
            "title": "Face ID",
            "host": "240d:1a:1c6:2400:216:3eff:fec8:25e8",
            "service": "faceid",
            "port": 4000,
            "ssl": None,
            "key": None,
        }),
        edict({
            "title": "Face ID CosDis Estimator",
            "host": "240d:1a:1c6:2400:216:3eff:fec8:25e8",
            "service": "faceid_cos",
            "port": 5000,
            "ssl": None,
            "key": None,
        }),
        edict({
            "title": "Face Detector YoloV4",
            "host": "240d:1a:1c6:2400:216:3eff:fec8:25e8",
            "service": "yolov4",
            "port": 6000,
            "ssl": None,
            "key": None,
        }),
        edict({
            "title": "Face Detector EfficientDetB0@Dev",
            "host": "240d:1a:1c6:2400:216:3eff:fec8:25e8",
            "service": "efficient_detb0_dev",
            "port": 3001,
            "ssl": None,
            "key": None,
        }),
        edict({
            "title": "Face ID@Dev",
            "host": "240d:1a:1c6:2400:216:3eff:fec8:25e8",
            "service": "faceid_dev",
            "port": 4001,
            "ssl": None,
            "key": None,
        }),
        edict({
            "title": "Face ID CosDis Estimator@Dev",
            "host": "240d:1a:1c6:2400:216:3eff:fec8:25e8",
            "service": "faceid_cos_dev",
            "port": 5001,
            "ssl": None,
            "key": None,
        }),
        edict({
            "title": "Face Detector-Detector@Dev",
            "host": "240d:1a:1c6:2400:216:3eff:fec8:25e8",
            "service": "yolov4_dev",
            "port": 6001,
            "ssl": None,
            "key": None,
        }),
    ]

    index, title = cselector.selector([f"{o.title.ljust(40)} [{o.host}]:{o.port} @ {o.service}" for o in servers], title="Select an inference server.")
    selected = servers[index]
    for k in selected:
        v = selected[k]
        print(f" {k} => {v}")

    HOST = selected.host
    PORT = selected.port

    index, title = cselector.selector(["~/test.mp4", "-1", "0", "1", "2", "3"], title="0 = Camera, -1 = Screen, filepath => video, images...")
    FD = title  # 0 = Camera, -1 = Screen, filepath => video, images...
    image2image(HOST, PORT, FD, 30)

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
from easydict import EasyDict as edict

import pyglview

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

    def loop():
        nonlocal client_socket, fps_limit,  previous_time, time_cache, cap, view, f_fps_count, f_fps_cache, v_fps_count, v_fps_cache, req_fps_cache, req_fps_count, req_queue_count, message, frame_times, frame_time_queue, frame_index
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
            LIMIT_HF_REQ = 2
        elif req_fps_cache < 30:
            LIMIT_REQ = 5
            LIMIT_HF_REQ = 3
        elif req_fps_cache < 40:
            LIMIT_REQ = 6
            LIMIT_HF_REQ = 4
        elif req_fps_cache < 50:
            LIMIT_REQ = 7
            LIMIT_HF_REQ = 5

        if req_queue_count <= LIMIT_REQ and now - previous_time >= (1.0/(req_fps_cache+1)*0.90):
            previous_time = now
            push = True
            if req_queue_count >= LIMIT_HF_REQ and (req_queue_count % 2 == 0):
                push = False
            if push or True:
                check, img = cap.read()
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
            # offset = vargs.window_height - 20
            # x = frame_index % vargs.window_width
            # frame_times[x:x + 4] = 0
            # frame_times[x] = np.array((x, -sub, x, 0), dtype=np.int32)
            # pdist = np.array(frame_times.reshape(-1, 1, 2), dtype=np.float32)
            # n = np.min(pdist.reshape(-1, 2), axis=0)
            # # pdist[:,:,:0] = pdist[:,:,:0] * n[0]
            # pdist[:,:,1] = -(pdist[:,:,1] / n[1]) * 100 + offset
            # cv2.polylines(img=img, pts=np.array(pdist, dtype=np.int32), isClosed=True, color=(255, 160, 0), thickness=2, lineType=cv2.LINE_8, shift=0)

            # aimage.draw_title(img=img, message=display_info)
            aimage.draw_title(img=img, message=display_info + f' {str(int(sub)).rjust(4)}ms B:{str(req_queue_count).rjust(2)}')
            aimage.draw_footer(img=img, message=message)

            view.set_image(img)
            frame_index += 1
            v_fps_count += 1
        f_fps_count += 1

    view.set_loop(loop)
    view.start()


def image2image2(HOST, PORT, fd, quality):
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
    request_count = 0
    fps_count = 0
    fps = 0
    req_fps_count = 0
    req_fps = 0
    st = time.time()


    cap = aimage.open(fd)
    view = pyglview.Viewer(keyboard_listener=cap.keyboard_listener)

    def loop():
        nonlocal request_count, st, fps_count, cap, view, client_socket, fps, req_fps_count, req_fps
        if time.time() - st > 1.0:
            cpu_usage = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            cpu_res = f'CPU:{str(cpu_usage).rjust(4)}% '
            mresources = '[{}Mem:{}MB({}%)]'.format(cpu_res, str(round(mem.used / 1024 / 1024, 2)).rjust(8), str(round(mem.percent, 1)).rjust(4))
            fps = fps_count
            req_fps = req_fps_count

            print("\033[0K", end="", flush=True)
            print(f"FPS:{str(fps).rjust(3)}/REQFPS:{str(req_fps).rjust(3)}/RES:{mresources}", flush=True)
            print("\033[1A", end="", flush=True)
            st = time.time()
            fps_count = 0
            req_fps_count = 0
        fps_count += 1
        if request_count < 4:

            check, img = cap.read()

            if check:
                # logger.debug("Fetch")
                client_socket.write([img])
                request_count += 1
                req_fps_count += 1
        blocks = client_socket.read()
        if blocks is not None:
            if isinstance(blocks, list):
                for data in blocks:
                    data = np.array(data)
                    # logger.debug("Show")

                    # def draw_footer(img, message, color=(255, 200, 55), bg=(55, 55, 55), font_scale=1, font_type=0):  # @public
                    # def draw_title(img, message, color=(255, 200, 55), bg=(55, 55, 55), font_scale=1, font_type=0):  # @public
                    aimage.draw_footer(img=data, message="FPS:" + str(req_fps))
                    # aimage.draw_title(img=data, message="FPS:" + str(fps))
                    # aimage.draw_text(img=data, message="FPS:" + str(fps), x=5 + 1, y=25 * 2 + 2, color=(130, 50, 0), font_scale=2, font_type=2)
                    # aimage.draw_text(img=data, message="FPS:" + str(fps), x=5, y=25 * 2, color=(255, 100, 0), font_scale=2, font_type=2)
                    view.set_image(data)
                    break
                request_count -= len(blocks)

    view.set_loop(loop)
    view.start()
    print("Main thread ended")


def image2data(HOST, PORT, fd, quality):
    class ProtocolStack(bridge.client.StreamClientFactory):
        def on_connected(self):
            s = self.protocol_instance
            s.add_output_protocol(bridge.protocol.ImageEncoder(quality=quality))
            s.add_output_protocol(bridge.protocol.LengthSplitOut())

            s.add_input_protocol(bridge.protocol.LengthSplitIn())

        def on_disconnected(self):
            pass

    client_socket = bridge.client.EaterBridgeClient(host=HOST, port=PORT, protocol_stack=ProtocolStack)
    client_socket.start()

    def terminate(a, b):
        client_socket.destroy()
        exit(9)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    request_count = 0
    fps_count = 0
    fps = 0
    req_fps_count = 0
    req_fps = 0
    st = time.time()


    cap = aimage.open(fd)
    view = pyglview.Viewer(keyboard_listener=cap.keyboard_listener)

    def loop():
        nonlocal request_count, st, fps_count, cap, view, client_socket, fps, req_fps_count, req_fps
        if time.time() - st > 1.0:
            cpu_usage = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            cpu_res = f'CPU:{str(cpu_usage).rjust(4)}% '
            mresources = '[{}Mem:{}MB({}%)]'.format(cpu_res, str(round(mem.used / 1024 / 1024, 2)).rjust(8), str(round(mem.percent, 1)).rjust(4))
            fps = fps_count
            req_fps = req_fps_count

            print("\033[0K", end="", flush=True)
            print(f"FPS:{str(fps).rjust(3)}/REQFPS:{str(req_fps).rjust(3)}/RES:{mresources}", flush=True)
            print("\033[1A", end="", flush=True)
            st = time.time()
            fps_count = 0
            req_fps_count = 0
        fps_count += 1
        if request_count < 4:

            check, img = cap.read()

            if check:
                # logger.debug("Fetch")
                client_socket.write([img])
                request_count += 1
                req_fps_count += 1
        blocks = client_socket.read()
        if blocks is not None:
            if isinstance(blocks, list):
                for data in blocks:
                    data = np.array(data)
                    # logger.debug("Show")

                    # def draw_footer(img, message, color=(255, 200, 55), bg=(55, 55, 55), font_scale=1, font_type=0):  # @public
                    # def draw_title(img, message, color=(255, 200, 55), bg=(55, 55, 55), font_scale=1, font_type=0):  # @public
                    aimage.draw_footer(img=data, message="FPS:" + str(req_fps))
                    # aimage.draw_title(img=data, message="FPS:" + str(fps))
                    # aimage.draw_text(img=data, message="FPS:" + str(fps), x=5 + 1, y=25 * 2 + 2, color=(130, 50, 0), font_scale=2, font_type=2)
                    # aimage.draw_text(img=data, message="FPS:" + str(fps), x=5, y=25 * 2, color=(255, 100, 0), font_scale=2, font_type=2)
                    view.set_image(data)
                    break
                request_count -= len(blocks)

    view.set_loop(loop)
    view.start()
    print("Main thread ended")


if __name__ == "__main__":
    # cap = aimage.open(0)
    # while True:
    #     check, img = cap.read()
    #     if check:
    #         aimage.show(img)
    # cselector.selector(["image2image", "image2json"])

    HOST = "localhost"
    # HOST = "240d:1a:1c6:2400:216:3eff:fec8:25e8"
    # PORT = 4000
    PORT = 4649
    FD = "~/test6.mp4"  # 0 = Camera, -1 = Screen, filepath => video, images...
    image2image(HOST, PORT, FD, 30)
    # image2data()

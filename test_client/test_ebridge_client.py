#!/usr/bin/env python3

import logging
import os
import signal
import sys
import time

import cselector
import numpy as np
import psutil

import aimage
#aimage.is_available_native_queue = True
import aimage.eater.bridge as bridge

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


def image2image(HOST, PORT, fd, quality=60):
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

    import pyglview

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


def image2data(HOST, PORT, fd, quality=60):
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

    import pyglview

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
    FD = "~/test.mp4"  # 0 = Camera, -1 = Screen, filepath => video, images...
    image2image(HOST, PORT, FD)
    # image2data()

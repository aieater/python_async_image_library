#!/usr/bin/env python3

import contextlib
import glob
import importlib
import multiprocessing
import os
import platform
import queue
import sys
import threading
import time

import cv2
import numpy as np


def _ipython_imshow_(image):
    import IPython.display
    image = image[..., ::-1]
    check, img = cv2.imencode(".png", image)
    decoded_bytes = img.tobytes()
    IPython.display.display(IPython.display.Image(data=decoded_bytes))
    return None


def _cshow_(image):
    if is_notebook():
        return _ipython_imshow_(image)
    else:
        import imgcat
        return imgcat.imgcat(image)


def _gshow_(image):
    return _cv2_imshow_("", image)


if importlib.util.find_spec("acapture"):
    import acapture

    class FastJpegCapture(acapture.BaseCapture):
        def __init__(self, fd):
            self.f = os.path.expanduser(fd)
            if self.f[-1] != os.sep:
                self.f += os.sep
            self.f += "**" + os.sep + "*"
            files = glob.glob(self.f, recursive=True)
            self.flist = []
            for f in files:
                filename, ext = os.path.splitext(f)
                ext = ext.lower()
                if ext == ".jpg" or ext == ".jpeg":
                    f = os.path.join(self.f, f)
                    self.flist += [f]

        def is_ended(self):
            return len(self.flist) == 0

        def destroy(self):
            pass

        def read(self):
            while len(self.flist) > 0:
                ff = self.flist.pop(0)
                img = load_image(ff)
                if img is not None:
                    return (True, img)
            return (False, None)

    class AsyncFastJpegCapture(acapture.BaseCapture):
        def __other_process__(self, fd, rq, wq):
            fpath = os.path.expanduser(fd)
            if fpath[-1] != os.sep:
                fpath += os.sep
            fpath += "**" + os.sep + "*"
            files = glob.glob(fpath, recursive=True)
            for f in files:
                filename, ext = os.path.splitext(f)
                ext = ext.lower()
                if ext == ".jpg" or ext == ".jpeg":
                    f = os.path.join(fpath, f)
                    exit_signal = wq.get_nowait()
                    if exit_signal is not None:
                        break
                    img = load_image(f)
                    rq.put_nowait((True, img))
            rq.put_nowait((False, None))

        def __init__(self, fd):
            self.rq = multiprocessing.Queue()
            self.wq = multiprocessing.Queue()
            self.th = multiprocessing.Process(target=self.__other_process__, args=(fd, self.rq, self.wq))
            self.th.start()

        def is_ended(self):
            return len(self.flist) == 0

        def destroy(self):
            pass

        def read(self):
            self.rq.get()

    acapture.DirImgFileStub = AsyncFastJpegCapture
    # acapture.DirImgFileStub = FastJpegCapture

    open = acapture.open  # @public
else:
    print("Could not support video.")
    print("pip3 install pygame acapture")

__front_flag_for_opencv_problem__ = False


def _cv2_imshow_(mes, image):
    global __front_flag_for_opencv_problem__
    image = image[..., ::-1]
    cv2.imshow(mes, image)
    ret = cv2.waitKey(1)
    if __front_flag_for_opencv_problem__ is False:
        __front_flag_for_opencv_problem__ = True
        if platform.system() == "Darwin":
            os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
            cv2.moveWindow("", 0, 0)

    return ret


def is_notebook():  # @public
    try:
        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell":
            return True  # Jupyter notebook or qtconsole
        elif shell == "TerminalInteractiveShell":
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False  # Probably standard Python interpreter


def show(image, console=False):  # @public
    image = np.array(image, dtype=np.uint8)
    if console:
        return _cshow_(image)
    else:
        if "DISPLAY" in os.environ or platform.system() == "Darwin":
            return _gshow_(image)
        else:
            return _cshow_(image)


def wait(w=0):  # @public
    if "DISPLAY" in os.environ or platform.system() == "Darwin":
        return cv2.waitKey(w)
    else:
        time.sleep(w)
        return None


def clear_output():  # @public
    if is_notebook():
        import IPython
        IPython.display.clear_output()
    else:
        print("\033[0;0f")


class _key_observer_:
    try:
        import termios
    except Exception as e:
        print(e)
        print("pip3 install termios")
    def __th_observe_key__(q):
        @contextlib.contextmanager
        def raw_mode(file):
            old_attrs = termios.tcgetattr(file.fileno())
            new_attrs = old_attrs[:]
            new_attrs[3] = new_attrs[3] & ~(termios.ECHO | termios.ICANON)
            try:
                termios.tcsetattr(file.fileno(), termios.TCSADRAIN, new_attrs)
                yield
            finally:
                termios.tcsetattr(file.fileno(), termios.TCSADRAIN, old_attrs)

        with raw_mode(sys.stdin):
            try:
                while True:
                    n = ord(sys.stdin.read(1))
                    q.put(n)
            except Exception as e:
                print("Error:" + str(e))
                pass

    def __init__(self):
        q = queue.Queue()
        thread = threading.Thread(target=_key_observer_.__th_observe_key__, args=(q, ), daemon=True)
        thread.start()
        self.q = q
        self.th = thread

    def get(self):
        try:
            return self.q.get_nowait()
        except:
            return None


def make_key_observer():  # @public
    return _key_observer_()

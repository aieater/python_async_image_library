#!/usr/bin/env python3
from __future__ import print_function
import importlib
import os
def to_bool(s): return s in [1,"True","TRUE","true","1","yes","Yes","Y","y","t","on"]
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
            __builtin__.print("\033[47m%s@%s(%s):\033[0m "%(rpad(s[1][1],20), lpad(str(s[1][3]),10), rpad(str(s[1][2]),4)),end="")
            return __builtin__.print(*args, **kwargs)

_dopen = open
import platform,subprocess,sys,time,glob,multiprocessing,threading,traceback,pathlib,json,math,configparser,inspect,mimetypes
try:
    import queue
except ImportError:
    import Queue as queue
import numpy as np
import cv2

CRED = '\033[0;31m'
CCYAN = '\033[0;36m'
CGREEN = '\033[0;32m'
CRESET = '\033[0m'

def _opencv_decoder_(data):
    b = data
    nb = np.asarray(b,dtype=np.uint8)
    data = cv2.imdecode(nb,cv2.IMREAD_COLOR)
    data = cv2.cvtColor(data,cv2.COLOR_BGR2RGB)
    return data

def _opencv_encoder_(data,**kargs):
    quality = 90
    if "quality" in kargs:
        quality = kargs["quality"]
    data = cv2.cvtColor(data,cv2.COLOR_BGR2RGB)
    check,data = cv2.imencode(".jpg",data,[int(cv2.IMWRITE_JPEG_QUALITY), quality]) # quality 1-100
    if check == False:
        raise "Invalid image data"
    return data

def _cv2_imshow_(mes,image):
    image = cv2.cvtColor(image,cv2.COLOR_RGB2BGR)
    cv2.imshow(mes,image)
    return cv2.waitKey(1)

def _ipython_imshow_(image):
    import IPython.display
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    check,img = cv2.imencode(".png", image)
    decoded_bytes = img.tobytes()
    IPython.display.display(IPython.display.Image(data=decoded_bytes))
    return None

def _cshow_(image):
    if is_notebook():
        return _ipython_imshow_(image)
    else: import imgcat;return imgcat.imgcat(image)

def _gshow_(image):
    return _cv2_imshow_("",image)



def rgb2bgr(img): #@public
    if img.shape[2] != 3:
        raise "src image channel must be 3(RGB)"
    if img.dtype != np.uint8:
        raise "expected dtype is uint8."
    return cv2.cvtColor(img,cv2.COLOR_RGB2BGR)

def draw_image_alpha(img,img_rgba,sx,sy): #@public
    print("Does not support alpha channel.")
    return img

def is_image_ext(f): #@public
    e = f.split(".")[-1].lower()
    if e == "jpg":  return True
    if e == "jpeg": return True
    if e == "png":  return True
    if e == "tiff": return True
    if e == "gif":  return True
    return False

def decoder(data): #@public
    return _opencv_decoder_(data)

def encoder(data, **kargs): #@public
    return _opencv_encoder_(data,**kargs)

def load_image(path): #@public
    img = cv2.imread(path)
    img = cv2.cvtColor(img,cv2.COLOR_RGB2BGR)
    return img

def save_image(path, data, *, quality=90, format="jpg"): #@public
    data = cv2.cvtColor(data, cv2.COLOR_RGB2BGR)
    return cv2.imwrite(path, data, [cv2.IMWRITE_JPEG_QUALITY, quality])

def load(path): #@public
    t,ext = mimetypes.guess_type(path)[0].split("/")
    if t == "image":
        img = cv2.imread(path, 3)
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    else:
        print(path,"is not image file.")

def gamma(img,g): #@public
    lookUpTable = np.empty((1,256), np.uint8)
    for i in range(256): lookUpTable[0,i] = np.clip(pow(i / 255.0, g) * 255.0, 0, 255)
    img = cv2.LUT(img, lookUpTable)
    return img

def hue(img,h=0,s=0,v=0): #@public
    img = cv2.cvtColor(img,cv2.COLOR_RGB2HSV)
    if h != 0:img[:,:,1] += h
    if s != 0:img[:,:,1] += s
    if v != 0:img[:,:,2] += v
    img = cv2.cvtColor(img,cv2.COLOR_HSV2RGB)
    return img

def flip(img,t): #@public
    return np.flip(img,t)

def is_notebook(): #@public
    try:
        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell":
            return True   # Jupyter notebook or qtconsole
        elif shell == "TerminalInteractiveShell":
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter
        
def show(image,console=False): #@public
    image = np.array(image,dtype=np.uint8)
    if console:
        return _cshow_(image)
    else:
        if "DISPLAY" in os.environ or platform.system() == "Darwin":
            return _gshow_(image)
        else:
            return _cshow_(image)

def wait(w=0): #@public
    if "DISPLAY" in os.environ or platform.system() == "Darwin":
        return cv2.waitKey(w)
    else:
       time.sleep(w)
       return None

def clear_output(): #@public
    if is_notebook(): import IPython; IPython.display.clear_output()
    else: print("\033[0;0f")

def ratio_resize(img,ww,interpolation="fastest"): #@public
    s = 1
    if img.shape[0] < img.shape[1]:
        s = ww/img.shape[1]
    else:
        s = ww/img.shape[0]
    w = int(img.shape[1] * s)
    h = int(img.shape[0] * s)
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)

def crop(img,x,y,x2,y2): #@public
    return img[x:x2,y:y2]

def resize(img,w,h=None,interpolation="fastest"): #@public
    if h is None: return ratio_resize(img,w,interpolation)
    return cv2.resize(img, (w,h), interpolation=cv2.INTER_AREA)

def draw_rect(img,s,t,c=(255,0,0),line=2): #@public
    cv2.rectangle(img, (int(s[0]),int(s[1])), (int(t[0]),int(t[1])), c, line)

def draw_fill_rect(img,s,t,c=(255,0,0)): #@public
    cv2.rectangle(img, (int(s[0]),int(s[1])), (int(t[0]),int(t[1])), c, -1)




if importlib.util.find_spec("acapture"):
    import acapture
    class FastJpegCapture(acapture.BaseCapture):
        def __init__(self,fd):
            self.f = os.path.expanduser(fd)
            if self.f[-1] != os.sep: self.f += os.sep
            self.f += "**"+os.sep+"*"
            files = glob.glob(self.f,recursive=True)
            self.flist = []
            for f in files:
                filename, ext = os.path.splitext(f)
                ext = ext.lower()
                if ext == ".jpg" or ext == ".jpeg":
                    f = os.path.join(self.f, f)
                    self.flist += [f]
        def is_ended(self): return len(self.flist) == 0
        def destroy(self): pass
        def read(self):
            while len(self.flist) > 0:
                ff = self.flist.pop(0)
                img = load_image(ff)
                if img is not None:
                    return (True,img)
            return (False,None)
    class AsyncFastJpegCapture(acapture.BaseCapture):
        def __other_process__(self,fd,rq,wq):
            fpath = os.path.expanduser(fd)
            if fpath[-1] != os.sep: fpath += os.sep
            fpath += "**"+os.sep+"*"
            files = glob.glob(fpath,recursive=True)
            for f in files:
                filename, ext = os.path.splitext(f)
                ext = ext.lower()
                if ext == ".jpg" or ext == ".jpeg":
                    f = os.path.join(fpath, f)
                    exit_signal = wq.get_nowait()
                    if exit_signal is not None: break;
                    img = load_image(f)
                    rq.put_nowait((True,img))
            rq.put_nowait((False,None))

        def __init__(self,fd):
            self.rq = multiprocessing.Queue()
            self.wq = multiprocessing.Queue()
            self.th = multiprocessing.Process(target=self.__other_process__,args=(fd,self.rq,self.wq))
            self.th.start()
        def is_ended(self): return len(self.flist) == 0
        def destroy(self): pass
        def read(self): self.rq.get()
    acapture.DirImgFileStub = AsyncFastJpegCapture
    # acapture.DirImgFileStub = FastJpegCapture

    open = acapture.open #@public
else:
    print("pip3 install pygame acapture")


def file_type(d): #@public
    print("image_head: Does not support API.")
    return None

def image_head(d): #@public
    print("image_head: Does not support API.")
    return None

def generate_colors(C=200): #@public
    color_table = []
    color_table.append((0,0,255))
    color_table.append((0,255,0))
    color_table.append((255,0,255))
    color_table.append((255,255,0))
    color_table.append((0,255,255))
    color_table.append((255,0,0))
    for c in range(C-len(color_table)):
        CD = 0.1
        TPI = (math.pi*2)/3
        TT = 1.123
        d1 = 0.5+math.cos(CD+TPI+TT*c)*0.5
        d2 = 0.5+math.cos(CD+TPI*2+TT*c)*0.5
        d3 = 0.5+math.cos(CD+TPI*3+TT*c)*0.5

        cc = np.array([d3,d2,d1])

        TT = 1.371
        d1 = 0.5+math.cos(CD+TPI+TT*c)*0.5
        d2 = 0.5+math.cos(CD+TPI*2+TT*c)*0.5
        d3 = 0.5+math.cos(CD+TPI*3+TT*c)*0.5

        cc = cc + np.array([d1,d2,d3])

        cc = cc*(1.0-c/C)*255.0
        cc = np.array(cc,dtype=np.uint8)
        color_table.append((int(cc[0]),int(cc[1]),int(cc[2])))
    return color_table

def draw_box(image, box, color, caption=None): #@public
    if type(box) == np.ndarray:
        if len(box.shape) == 1 and len(box) == 4:
            pass
        elif len(box.shape) == 2 and box.shape[0] == 2 and box.shape[1] == 2:
            box = box.flatten()
        else:
            raise "Invalid shape."
    elif type(box) == list:
        if len(box) == 2:
            box = np.array([box[0][0],box[0][1],box[1][0],box[1][1]],np.int32)
        else:
            box = np.array([box[0],box[1],box[2],box[3]],np.int32)
    elif type(box) == tuple:
        if len(box) == 2:
            box = np.array([box[0][0],box[0][1],box[1][0],box[1][1]],np.int32)
        else:
            box = np.array([box[0],box[1],box[2],box[3]],np.int32)
    else:
        raise "Invalid type. box => " + type(box)

    box = np.array(box)
    image_h = image.shape[0]
    image_w = image.shape[1]
    box_thick = int(0.6 * (image_h + image_w) / 600.0)
    c1 = (int(box[0]), int(box[1]))
    c2 = (int(box[2]), int(box[3]))
    cr = (int(color[0]),int(color[1]),int(color[2]))
    cv2.rectangle(image,c1,c2,cr,box_thick)
    if caption:
        fontScale = 0.5
        t_size = cv2.getTextSize(caption, 0, fontScale, thickness=box_thick//2)[0]
        c3 = (int(c1[0]+t_size[0]),int(c1[1]-t_size[1] - 3))
        cv2.rectangle(image, c1, c3, cr, -1)  # filled
        cv2.putText(image, caption, (int(box[0]), int(box[1])-2), cv2.FONT_HERSHEY_SIMPLEX, fontScale, (0, 0, 0),box_thick//2, lineType=cv2.LINE_AA)


try:
    from aimage_native import *
    print(CCYAN+"========================================================"+CRESET)
    print(CCYAN+"Aggressive 3D image augmentation is available."+CRESET)
    print(CCYAN+"Fastest async image loader is available."+CRESET)
    print(CCYAN+"aimage loading speed is faster than Pillow/OpenCV/TensorFlow."+CRESET)
    print(CCYAN+"Event driven non blocking loader is available."+CRESET)
    print(CCYAN+"========================================================"+CRESET)
except:
    print(CRED+"==========================================================================="+CRESET)
    print(CRED+"WARN: Native async image library loading failed."+CRESET)
    print(CRED+" - Pillow/OpenCV/TensorFlow data loading speed is slower than aimage library."+CRESET)
    print(CRED+" - aimage is superior to the data augmentation systems built into DeepLearning frameworks such as TensorFlow and PyTorch."+CRESET)
    print(CRED+" If you want to get suport for paid license, please contact support@pegara.com."+CRESET)
    print(CRED+"==========================================================================="+CRESET)
    print("Using unoptimized aimage library.")
    pass


if __name__ == "__main__":
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    path = os.path.dirname(os.path.abspath(filename))
    img = load(os.path.join(path,"../sample.png"))
    draw_fill_rect(img,[100,120],[120,200],(255,0,0))
    show(img)
    wait(0)






############ HELP ##############

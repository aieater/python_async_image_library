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
        if img is None:
            print(CRED,"\n\nInvalid image file or invalid path. \"%s\"\n\n"%(path,),CRESET)
            raise "Invalid file or invalid path."
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    print(CRED,"\n\nInvalid image file or invalid path. \"%s\"\n\n"%(path,),CRESET)
    return None
    

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


class AggressiveImageGenerator:
    def __init__(self,**kwargs):
        entry = kwargs["entry"]
        if entry        == "/": raise "Can't specify root path"
        if entry[-1]    == '/': entry = entry[0:-1]
        if entry        == ".": raise "Invalid path"
        if os.path.exists(entry) == False: raise "Does not exist path"
        self.loss = "categorical_crossentropy"
        self.set(**kwargs)
        print(kwargs)

        self.q      = 0
        self.iindex = 0
        print("=============================================")
        self.oindex = 0
        self.STREAM_BATCH = 16

        self.label_name = os.path.basename(self.entry)
        self.build_classes()

        print(self.classes)

        data_aug_params = kwargs["data_aug_params"]
        def setd(k,v):
            if k not in data_aug_params:
                data_aug_params[k] = v
        setd("resize_interpolation","fastest")
        for k in data_aug_params:
            data_aug_params[k] = str(data_aug_params[k])
        self.data_aug_params = data_aug_params

        self.output_buffer = []
        self.datas = None
        self.is_tree = self.loss == "binary_crossentropy"
        self.sync_reset()

    def sync_reset(self):
        entry = self.entry
        if self.datas == None:
            self.datas = []
            self.prebatch = None
            class_index_table = {}
            table = {}
            for clazz in self.classes:
                c = self.classes[clazz]
                class_index_table[c["index"]] = {"name":clazz,"results":[],"total":0}
            for filename in pathlib.Path(entry).glob('**/*.jpg'):
                filename = str(filename)
                self.datas.append(filename)
                signals = self.make_signal(self.entry, filename, self.classes)
                if self.is_tree:
                    signals *= self.signal_mask
                idx_key = np.argmax(signals)
                if idx_key not in table:
                    table[idx_key] = []
                table[idx_key].append(filename)
                #if idx_key not in class_index_table:
                #    class_index_table[idx_key] = {"name":self.get_name(idx_key),"results":[],"total":0}
                class_index_table[idx_key]["total"] += 1
            vmax = 0
            for k in table:
                v = table[k]
                vlen = len(v)
                if vlen > vmax:
                    vmax = vlen
                print(self.get_name(k),":",vlen)
            print("Max => ",vmax)
            for k in table:
                v = table[k]
                i = 0
                vlen = len(v)
                ns = []
                for x in range(vmax):
                   ns.append(v[x % vlen])
                table[k] = ns
            new_datas = []
            for k in table:
                v = table[k]
                vlen = len(v)
                new_datas += v
            if self.data_align:
                print("Total",len(self.datas),"=>",vmax,"x",len(table),"=>",len(new_datas))
                self.datas = new_datas
                for i in class_index_table:
                    class_index_table[i]["total"] = vmax
            self.total = len(self.datas)
            self.class_index_table = class_index_table
        if self.shuffle:
            random.shuffle(self.datas)
        self.iindex = 0
        self.oindex = 0

    def build_classes(self):
        j={}
        try:
            import json
            j = json.loads(open(self.label_path).read())
        except:
            pass
        classes = self.make_class(entry=self.entry, loss=self.loss, class_dict=j)
        self.label_json = json.dumps(classes)
        with open(self.label_path,"w") as fp:
            fp.write(self.label_json)

        self.classes = classes
        if self.loss == "binary_crossentropy":
            signal_mask = np.zeros((len(classes),))
            tcnt = 0
            for clazz in classes:
                i = classes[clazz]["index"]
                if clazz[0] == "@":
                    signal_mask[i] = 1
                    tcnt += 1
            if tcnt <= 2:
                raise "Two or more target directories are required. Use @ to define it."
            self.signal_mask = signal_mask
        else:
            self.signal_mask = np.ones((len(classes),))
        return classes

    def get_classes(self):
        return self.clasess

    def get_batch(self,batch_size):
        block = self.get_data_block(batch_size)
        ret = [[],[],[]]
        if block:
            for d in block:
                ret[0].append(d["image"])
                ret[1].append(d["signals"])
                #d["points"])
            ret[0] = np.array(ret[0],dtype=np.float32)
            ret[1] = np.array(ret[1],dtype=np.float32)
            if self.rescale != 1.0:
                ret[0] *= self.rescale

        return ret
    def get_data_block(self,batch_size):
        print("get_data_block")
        if self.total == 0:
            raise "Zero length"
        while True:
            if self.q < 1024:
                if self.iindex < self.total:
                    ds      = self.datas[self.iindex : self.iindex + self.STREAM_BATCH]
                    dlen    = len(ds)
                    self.q  += dlen
                    stream  = list()
                    input   = dict()
                    input["data_aug_params"] = self.data_aug_params
                    for image_path in ds:
                        signals = self.make_signal(self.entry, image_path, self.classes)
                        d = dict()
                        d["image_path"]     = image_path
                        d["signals"]        = np.array(signals,dtype=np.float32)
                        d["points_table"]   = None
                        stream.append(d)
                    input["stream"] = stream
                        # //    {
                        # //      params:{
                        # //          data_aug_params:{}
                        # //      },
                        # //      stream: [{image_path:"",signals:[],points_table:[]},{},{},{},]
                        # //    }
                    native_module.async_image_loader_with_data_aug_input(str(hex(id(self))),input)
                    self.iindex += dlen
                else:
                    # random.shuffle(self.datas)
                    # self.iindex = 0
                    break
            else:
                break

        if self.iindex == self.oindex: return None
        if len(self.output_buffer) >= batch_size or self.iindex == self.oindex + len(self.output_buffer):
            buf = self.output_buffer[0:batch_size]
            self.output_buffer = self.output_buffer[batch_size:]
            self.oindex += len(buf)
            return buf
        while True:
            ret = native_module.async_image_loader_with_data_aug_output(str(hex(id(self))))
            if ret is not None and len(ret) > 0:
                self.q -= len(ret)
                self.output_buffer += ret
                if len(self.output_buffer) >= batch_size or self.iindex == self.oindex + len(self.output_buffer):
                    buf = self.output_buffer[0:batch_size]
                    self.output_buffer = self.output_buffer[batch_size:]
                    self.oindex += len(buf)
                    return buf
            else:
                time.sleep(0.1)
                if self.iindex == self.oindex: return None

    def find_index(self,class_dict):
        index = 0
        d = sorted(class_dict.items(),key=lambda x: x[1]["index"] )
        for obj in d:
            if index == int(obj[1]["index"]):
                index+=1
                continue
        return index

    def make_signal(self,entry,fpath,classes):
        sp = str(fpath)[len(entry):].split("/")
        signal = np.zeros((len(classes),),dtype=np.float32)
        for s in sp:
            if s in classes:
                signal[classes[s]["index"]] = 1
        return signal

    def register_class(self, class_name, class_dict, mark):
        if class_name not in class_dict:
            index = self.find_index(class_dict)
            class_dict[class_name] = {"index":index}

    def make_class(self, entry, *, loss="binary_crossentropy", class_dict={}):
        print("Entrypoint => ",entry)
        class_table_by_index    = {}
        class_table_by_name     = {}
        elen = len(entry)
        print(loss)
        if loss == "categorical_crossentropy":
            class_names = [os.path.basename(f) for f in glob.glob(os.path.join(entry,"*")) if os.path.isdir(f)]
            #print(class_names)
            for class_name in class_names:
                self.register_class(class_name,class_dict,"S")
        elif loss == "binary_crossentropy":
            for filename in pathlib.Path(entry).glob('**/'):
                filename = str(filename)
                # {}Attributs/{@}Target/{!}Ignore/{?}Unsupervised
                if "/!" in filename:
                    print("Ignore",filename)
                    continue
                if filename == entry:
                    continue
                class_name = os.path.basename(filename)
                if class_name not in class_dict:
                    if class_name[0] == '@':
                        self.register_class(class_name,class_dict,mark="S")
                    elif class_name[0] == '?':
                        self.register_class(class_name,class_dict,mark=" ")
                    else:
                        self.register_class(class_name,class_dict,mark="-")
        else:
            raise "Inbalid loss"
        return class_dict

    def get_name(self,index):
        for k in self.classes:
            if index == self.classes[k]["index"]:
                return k
        return None

    def find_by_name(self, p, label_name):
        if label_name in self.classes:
            return p[self.classes[label_name]["index"]]
        return None

    def find_top(self, p):
        index = np.argmax(p)
        for k in self.classes:
            c = self.classes[k]
            if c["index"] == index:
                return index,p[index],k
        return None,None,None



    def set(self,**kwargs):
        for k in kwargs: setattr(self,k,kwargs[k])


    def make_full_aug_params():
        class Dict:
            def __init__(self): self.d = dict()
            def set(self,k,v): self.d[k]=str(v)
        d = Dict()
        d.set("random_gaussian", 0.1);
        d.set("random_sharp", 0.1);
        d.set("random_median", 0.1);
        d.set("random_bilateral", 0.1);
        d.set("random_mosic", 0.1);
        d.set("mosic_shift_range", 1);
        d.set("random_equalization", 0.1);
        d.set("random_color_reduction", 0.1);
        d.set("random_cos", 0.1);
        d.set("random_hsv", 0.5);
        d.set("hue_range", 15);
        d.set("saturation_range", 0.05);
        d.set("lightness_range", 0.1);
        d.set("random_pow", 0.1);
        d.set("pow_min", 0.9);
        d.set("pow_max", 1.3);
        d.set("random_horizontal_flip", 0.15);
        d.set("random_vertical_flip", 0.25);
        d.set("random_shuffle_splitted_images", 0.1);
        d.set("random_resize_and_arrange_images", 0.1);
        d.set("random_crop", 0.25);
        d.set("crop_range", 0.2);
        d.set("random_noise",0.1);
        d.set("random_erase",0.2);
        d.set("background_type",5);
        d.set("affine_transform",0.5);
        d.set("aggressive_transform",0.5);
        d.set("random_x_shift",0.1);
        d.set("random_y_shift",0.1);
        d.set("random_x_scaling_range",0.1);
        d.set("random_y_scaling_range",0.1);
        d.set("random_x_rotate_range",10);
        d.set("random_y_rotate_range",10);
        d.set("random_z_rotate_range",10);
        d.set("random_distortion",0.5);
        d.set("random_mixup",0.1);
        d.set("mixup_alpha",0.1);
        return d.d

    def set_max_cache_size(size):
        pass


class AggressiveImageGeneratorForOD:
    def __init__(self,datas,classes,data_aug_params,shuffle=True):
        self.classes = classes
        self.total = len(datas)
        self.q = 0
        self.iindex = 0
        self.oindex = 0
        self.datas = datas
        self.STREAM_BATCH = 16
        self.data_aug_params = data_aug_params
        self.output_buffer = []
        self.shuffle = shuffle
        self.stub_buffer = []

    def get_data_block(self,batch_size):
        if self.total == 0:
            raise "Zero length"
        while True:
            if self.q < 1024:
                if self.iindex < self.total:
                    ds      = self.datas[self.iindex : self.iindex + self.STREAM_BATCH]
                    dlen    = len(ds)
                    self.q  += dlen
                    stream  = list()
                    input   = dict()
                    input["data_aug_params"] = self.data_aug_params
                    for d in ds:
                        dd = dict()
                        dd["image_path"]     = d["file_path"]
                        dd["image"]          = load(d["file_path"])
                        dd["points_table"]   = d["bounding_box_table"]
                        stream.append(dd)
                    input["stream"] = stream
                        # //    {
                        # //      params:{
                        # //          data_aug_params:{}
                        # //      },
                        # //      stream: [{image_path:"",signals:[],points_table:[]},{},{},{},]
                        # //    }
                    #native_module.async_image_loader_with_data_aug_input(str(hex(id(self))),input)
                    self.stub_buffer += stream
                    #self.stub_buffer += [input]
                    #native_module.image_data_augmentation(input)
                    self.iindex += dlen
                else:
                    # random.shuffle(self.datas)
                    # self.iindex = 0
                    break
            else:
                break

        if self.iindex == self.oindex: return None
        if len(self.output_buffer) >= batch_size or self.iindex == self.oindex + len(self.output_buffer):
            buf = self.output_buffer[0:batch_size]
            self.output_buffer = self.output_buffer[batch_size:]
            self.oindex += len(buf)
            return buf
        while True:
            #ret = native_module.async_image_loader_with_data_aug_output(str(hex(id(self))))
            ret = self.stub_buffer
            if ret is not None and len(ret) > 0:
                for d in ret:
                    if "points_table" in d:
                        points_table = d["points_table"]
                        del d["points_table"]
                        d["bounding_box_table"] = points_table
                    else:
                        d["bounding_box_table"] = {}
                self.q -= len(ret)
                self.output_buffer += ret
                if len(self.output_buffer) >= batch_size or self.iindex == self.oindex + len(self.output_buffer):
                    buf = self.output_buffer[0:batch_size]
                    self.output_buffer = self.output_buffer[batch_size:]
                    self.oindex += len(buf)
                    return buf
            else:
                time.sleep(0.1)
                if self.iindex == self.oindex: return None

    def make_full_aug_params():
            class Dict:
                def __init__(self): self.d = dict()
                def set(self,k,v): self.d[k]=str(v)
            d = Dict()
            FD=False
            if True:
                d.set("random_crop", 1 if FD else 0.25); #@@
                d.set("crop_range", 0.2); #@@
                d.set("random_median", 1 if FD else 0.1); #@@
                d.set("random_color_reduction", 1 if FD else 0.1); #@???
                d.set("random_equalization", 1 if FD else 0.1);

                d.set("random_bilateral", 1 if FD else 0.1);
                d.set("random_mosic", 1 if FD else 0.1);
                d.set("mosic_shift_range", 1);

                d.set("random_cos", 1 if FD else 0.1);
                d.set("random_hsv", 1 if FD else 0.5);
                d.set("hue_range", 15 if FD else 15);
                d.set("saturation_range", 0.05);
                d.set("lightness_range", 0.1);
                d.set("random_resize_and_arrange_images", 1 if FD else 0.1);
                d.set("random_horizontal_flip", 1 if FD else 0.15);
                d.set("random_vertical_flip", 1 if FD else 0.25);

                d.set("random_gaussian", 1 if FD else 0.1);
                d.set("random_sharp", 1 if FD else 0.1);
                d.set("random_pow", 1 if FD else 0.1);
                d.set("pow_min", 0.9);
                d.set("pow_max", 1.3);
                d.set("random_noise", 1 if FD else 0.1);
                d.set("random_erase", 1 if FD else 0.1);
                d.set("background_type", 3);
                d.set("affine_transform", 1);
                d.set("aggressive_transform", 0);
                d.set("random_z_rotate_range", 3);
                d.set("random_x_shift", 0.1);
                d.set("random_y_shift", 0.1);

            return d.d

    def sync_reset(self):
        if self.shuffle:
            random.shuffle(self.datas)
        self.iindex = 0
        self.oindex = 0
    def set_max_cache_size(size):
        pass


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
    print()
    print(CRED+"Using unoptimized aimage library."+CRESET)
    print()
    pass


if __name__ == "__main__":
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    path = os.path.dirname(os.path.abspath(filename))
    img = load(os.path.join(path,"../sample.png"))
    draw_fill_rect(img,[100,120],[120,200],(255,0,0))
    show(img)
    wait(0)






############ HELP ##############

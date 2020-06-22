#!/usr/bin/env python3

import math
import mimetypes

import numpy as np
import cv2

CRED = '\033[0;31m'
CCYAN = '\033[0;36m'
CGREEN = '\033[0;32m'
CRESET = '\033[0m'

FONT_TYPE = [cv2.FONT_HERSHEY_COMPLEX_SMALL, cv2.FONT_HERSHEY_SIMPLEX, cv2.FONT_HERSHEY_TRIPLEX]


def gamma(img, g):  # @public
    lookUpTable = np.empty((1, 256), np.uint8)
    for i in range(256):
        lookUpTable[0, i] = np.clip(pow(i / 255.0, g) * 255.0, 0, 255)
    img = cv2.LUT(img, lookUpTable)
    return img


def hue(img, h=0, s=0, v=0):  # @public
    img = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    if h != 0:
        img[:, :, 1] += h
    if s != 0:
        img[:, :, 1] += s
    if v != 0:
        img[:, :, 2] += v
    img = cv2.cvtColor(img, cv2.COLOR_HSV2RGB)
    return img


def flip(img, t):  # @public
    return np.flip(img, t)


def bchw2bhwc(ts):  # @public
    s = len(ts.size())
    return ts.transpose(s - 3, s - 2).transpose(s - 2, s - 1)


def bhwc2bchw(ts):  # @public
    s = len(ts.size())
    return ts.transpose(s - 2, s - 1).transpose(s - 3, s - 2)


def concat_bhwc_image(ts):
    ts = np.array(ts)
    bsize = len(ts)
    rt = int(math.ceil(math.sqrt(bsize)))
    i = 0
    row = None
    for y in range(rt):
        col = None
        for x in range(rt):
            if i >= bsize:
                break
            b = ts[i]
            if col is not None:
                col = cv2.hconcat([col, b])
            else:
                col = b
            i += 1
        if row is not None:
            try:
                row = cv2.vconcat([row, col])
            except:
                pass
        else:
            row = col
        if i == bsize - 1:
            break

    return row  #np.array(row * 255, dtype=np.uint8)


def rgb2bgr(img):  # @public
    if img.shape[2] != 3:
        raise "src image channel must be 3(RGB)"
    if img.dtype != np.uint8:
        raise "expected dtype is uint8."
    return img[..., ::-1]


def draw_image_alpha(img, img_rgba, sx, sy):  # @public
    print("Does not support alpha channel.")
    return img


def draw_footer(img, message, color=(255, 200, 55), bg=(55, 55, 55), font_scale=1, font_type=0):  # @public
    if isinstance(img, np.ndarray) is False: raise Exception("img must be numpy.")
    if img.dtype != np.uint8: raise Exception("img dtype must be np.uint8.")
    h, w, c = img.shape
    color = [int(c) for c in color]
    font_type = int(font_type)
    cv2.rectangle(img=img, pt1=(0, h), pt2=(w, h - 20), color=bg, thickness=-1)
    cv2.putText(img, message, (5, h - 4), FONT_TYPE[font_type], font_scale, color, 1, lineType=cv2.LINE_AA)


def draw_title(img, message, color=(255, 200, 55), bg=(55, 55, 55), font_scale=1, font_type=0):  # @public
    if isinstance(img, np.ndarray) is False: raise Exception("img must be numpy.")
    if img.dtype != np.uint8: raise Exception("img dtype must be np.uint8.")
    h, w, c = img.shape
    color = [int(c) for c in color]
    font_type = int(font_type)
    cv2.rectangle(img=img, pt1=(0, 0), pt2=(w, 20), color=bg, thickness=-1)
    cv2.putText(img, message, (5, 17), FONT_TYPE[font_type], font_scale, color, 1, lineType=cv2.LINE_AA)


def draw_text(img, message, x=5, y=17, color=(255, 200, 55), font_scale=1, font_type=0):  # @public
    if isinstance(img, np.ndarray) is False: raise Exception("img must be numpy.")
    if img.dtype != np.uint8: raise Exception("img dtype must be np.uint8.")
    color = [int(c) for c in color]
    font_type = int(font_type)
    cv2.putText(img, message, (int(x), int(y)), FONT_TYPE[font_type], font_scale, color, 1, lineType=cv2.LINE_AA)


def is_image_ext(f):  # @public
    e = f.split(".")[-1].lower()
    if e == "jpg":
        return True
    if e == "jpeg":
        return True
    if e == "png":
        return True
    if e == "tiff":
        return True
    if e == "gif":
        return True
    return False


def opencv_decoder(data):
    b = data
    if isinstance(data, np.ndarray):
        nb = data
    elif isinstance(data, bytes):
        nb = np.frombuffer(b, dtype=np.uint8)
    elif isinstance(data, bytearray):
        nb = np.frombuffer(b, dtype=np.uint8)
    else:
        raise Exception("Arg type must be bytes/bytearray/ndarray. Invalid arg:" + type(data))
    data = cv2.imdecode(nb, cv2.IMREAD_COLOR)
    data = data[..., ::-1]

    return data


def opencv_encoder(data, **kargs):
    quality = 90
    if "quality" in kargs:
        quality = kargs["quality"]
    data = data[..., ::-1]
    check, data = cv2.imencode(".jpg", data, [int(cv2.IMWRITE_JPEG_QUALITY), quality])  # quality 1-100
    if check is False:
        raise "Invalid image data"
    return data


def pillow_decoder(data):
    d = np.array(Image.open(BytesIO(data)))
    return d


def pillow_encoder(data, **kargs):
    image = Image.fromarray(data)
    d = BytesIO()
    image.save(d, format="jpeg")
    return d


def _opencv_decoder_(data):
    b = data
    nb = np.asarray(b, dtype=np.uint8)
    data = cv2.imdecode(nb, cv2.IMREAD_COLOR)
    data = data[..., ::-1]
    return data


def _opencv_encoder_(data, **kargs):
    quality = 90
    if "quality" in kargs:
        quality = kargs["quality"]
    data = data[..., ::-1]
    check, data = cv2.imencode(".jpg", data, [int(cv2.IMWRITE_JPEG_QUALITY), quality])  # quality 1-100
    if check is False:
        raise "Invalid image data"
    return data


def native_decoder(data):
    raise Exception("You must install aimage-native-ext")


def native_encoder(data, *, quality=90, format="jpg"):
    raise Exception("You must install aimage-native-ext")


def native_fast_decoder(data):
    raise Exception("You must install aimage-native-ext")


def native_fast_encoder(data, *, quality=90, format="jpg"):
    raise Exception("You must install aimage-native-ext")


def native_load_image(path):
    raise Exception("You must install aimage-native-ext")


def native_save_image(path, data, *, quality=90, format="jpg"):
    raise Exception("You must install aimage-native-ext")


def native_fast_load_image(path):
    raise Exception("You must install aimage-native-ext")


def native_fast_save_image(path, data, *, quality=90, format="jpg"):
    raise Exception("You must install aimage-native-ext")


def decoder(data):  # @public
    return _opencv_decoder_(data)


def encoder(data, **kargs):  # @public
    return _opencv_encoder_(data, **kargs)


def load_image(path):  # @public
    img = cv2.imread(path)
    img = img[..., ::-1]
    return img


def save_image(path, data, *, quality=90, format="jpg"):  # @public
    data = data[..., ::-1]
    return cv2.imwrite(path, data, [cv2.IMWRITE_JPEG_QUALITY, quality])


def load(path):  # @public
    t, ext = mimetypes.guess_type(path)[0].split("/")
    if t == "image":
        img = cv2.imread(path, 3)
        if img is None:
            print(CRED, "\n\nInvalid image file or invalid path. \"%s\"\n\n" % (path, ), CRESET)
            raise "Invalid file or invalid path."
        return img[..., ::-1]
    print(CRED, "\n\nInvalid image file or invalid path. \"%s\"\n\n" % (path, ), CRESET)
    return None


def ratio_resize(img, ww, interpolation="fastest"):  # @public
    s = 1
    if img.shape[0] < img.shape[1]:
        s = ww / img.shape[1]
    else:
        s = ww / img.shape[0]
    w = int(img.shape[1] * s)
    h = int(img.shape[0] * s)
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)


def crop(img, x, y, x2, y2):  # @public
    return img[x:x2, y:y2]


def resize(img, w, h=None, interpolation="fastest"):  # @public
    if h is None:
        return ratio_resize(img, w, interpolation)
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)


def draw_rect(img, s, t, c=(255, 0, 0), line=2):  # @public
    cv2.rectangle(img=img, pt1=(int(s[0]), int(s[1])), pt2=(int(t[0]), int(t[1])), color=(int(c[0]), int(c[1]), int(c[2])), thickness=line)


def draw_fill_rect(img, s, t, c=(255, 0, 0)):  # @public
    cv2.rectangle(img=img, pt1=(int(s[0]), int(s[1])), pt2=(int(t[0]), int(t[1])), color=(int(c[0]), int(c[1]), int(c[2])), thickness=-1)


def file_type(d):  # @public
    print("image_head: Does not support API.")
    return None


def image_head(d):  # @public
    img = cv2.imread(d)
    info = {}
    info["height"] = img.shape[0]
    info["width"] = img.shape[1]
    info["channel"] = img.shape[2]
    return info


def generate_colors(C=200):  # @public
    color_table = []
    color_table.append((0, 0, 255))
    color_table.append((0, 255, 0))
    color_table.append((255, 0, 255))
    color_table.append((255, 255, 0))
    color_table.append((0, 255, 255))
    color_table.append((255, 0, 0))
    for c in range(C - len(color_table)):
        CD = 0.1
        TPI = (math.pi * 2) / 3
        TT = 1.123
        d1 = 0.5 + math.cos(CD + TPI + TT * c) * 0.5
        d2 = 0.5 + math.cos(CD + TPI * 2 + TT * c) * 0.5
        d3 = 0.5 + math.cos(CD + TPI * 3 + TT * c) * 0.5

        cc = np.array([d3, d2, d1])

        TT = 1.371
        d1 = 0.5 + math.cos(CD + TPI + TT * c) * 0.5
        d2 = 0.5 + math.cos(CD + TPI * 2 + TT * c) * 0.5
        d3 = 0.5 + math.cos(CD + TPI * 3 + TT * c) * 0.5

        cc = cc + np.array([d1, d2, d3])

        cc = cc * (1.0 - c / C) * 255.0
        cc = np.array(cc, dtype=np.uint8)
        color_table.append((int(cc[0]), int(cc[1]), int(cc[2])))
    return color_table


COLOR_TABLE = generate_colors(1024)  # public


def draw_box(image, box, color, caption=None, fontScale=0.5):  # @public
    if isinstance(image, np.ndarray) is False: raise Exception("image must be numpy.")
    if image.dtype != np.uint8: raise Exception("image dtype must be np.uint8.")
    color = [int(c) for c in color]


    if type(box) == np.ndarray:
        if len(box.shape) == 1 and len(box) == 4:
            pass
        elif len(box.shape) == 2 and box.shape[0] == 2 and box.shape[1] == 2:
            box = box.flatten()
        else:
            raise "Invalid shape."
    elif type(box) == list:
        if len(box) == 2:
            box = np.array([box[0][0], box[0][1], box[1][0], box[1][1]], np.int32)
        else:
            box = np.array([box[0], box[1], box[2], box[3]], np.int32)
    elif type(box) == tuple:
        if len(box) == 2:
            box = np.array([box[0][0], box[0][1], box[1][0], box[1][1]], np.int32)
        else:
            box = np.array([box[0], box[1], box[2], box[3]], np.int32)
    else:
        raise "Invalid type. box => " + type(box)

    box = np.array(box)
    image_h = image.shape[0]
    image_w = image.shape[1]
    box_thick = int(0.6 * (image_h + image_w) / 600.0)
    c1 = (int(box[0]), int(box[1]))
    c2 = (int(box[2]), int(box[3]))
    cr = (int(color[0]), int(color[1]), int(color[2]))
    cv2.rectangle(img=image, pt1=c1, pt2=c2, color=cr, thickness=box_thick)
    if caption:
        t_size = cv2.getTextSize(caption, 0, fontScale, thickness=box_thick // 2)[0]
        c3 = (int(c1[0] + t_size[0]), int(c1[1] - t_size[1] - 3))
        cv2.rectangle(img=image, pt1=c1, pt2=c3, color=cr, thickness=-1)  # filled
        cv2.putText(image, caption, (int(box[0]), int(box[1]) - 2), cv2.FONT_HERSHEY_SIMPLEX, fontScale, (0, 0, 0), box_thick // 2, lineType=cv2.LINE_AA)

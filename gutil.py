#!/usr/bin/env python3

import aimage
import os
import numpy as np
import cv2

def plot_h2(canvas, hh, yy, ix, iy, gx, gy):
    hh2, ilist, colors = estimate_coord2d(canvas.shape, hh, yy, ix, iy, gx, gy)
    for i in range(len(hh2)):
        x, y = hh2[i]
        color = colors[i]
        aimage.draw_rect(canvas, (x, y), (x + 1, y + 1), color, 1)
        # aimage.draw_rect(canvas, (x, y), (x + 1, y + 1), (color[0],color[1],color[2]), 1)
        # aimage.draw_rect(canvas, (x, y), (x + 1, y + 1), color, 1)
    return hh2, ilist, colors


def estimate_coord2d(shape, hh, yy, ix, iy, gx, gy):
    if ix > gx:
        a = gx
        gx = ix
        ix = a
    if iy > gy:
        a = gy
        gy = iy
        iy = a
    one_dim = False
    if hh.shape[1] > 1:
        hh = hh[:, 0:2]
        x_nx, y_nx = np.max(hh, axis=0)
        x_nm, y_nm = np.min(hh, axis=0)
    else:
        one_dim = True
        x_nx = np.max(hh, axis=0)
        y_nx = 1
        x_nm = np.min(hh, axis=0)
        y_nm = 0

    sx = x_nx - x_nm
    sy = y_nx - y_nm

    cw, ch, cc = shape

    if len(yy.shape) == 2: yy = np.argmax(yy, axis=1)
    hh2 = []
    ilist = []
    colors = []
    if sx > 0 and sy > 0:
        i = 0
        for i in range(len(hh)):
            x = hh[i][0]
            x = (x - x_nm) / sx
            x *= 0.90
            x += 0.05
            x = int(x * cw)

            if one_dim:
                y = 0.5
            else:
                y = hh[i][1]
            y = (y - y_nm) / sy
            y *= 0.90
            y += 0.05
            y = int(y * ch)

            if yy is not None and len(yy) > 0 and yy[i] >= 0:
                if ix <= x and x < gx and iy <= y and y < gy:
                    ilist.append(i)
                    colors.append((255, 255, 255))
                else:
                    colors.append(aimage.COLOR_TABLE[yy[i]])
            else:
                colors.append((200, 200, 200))
            i += 1
            hh2 += [[x, y]]
    return np.int32(hh2), np.int32(ilist), np.int32(colors)


def generate(shape, entry):
    INPUT_SHAPE = shape
    rescale = 1 / 255.0
    dparam = {}
    dparam["resize_width"] = INPUT_SHAPE[0]
    dparam["resize_height"] = INPUT_SHAPE[1]
    label_path = "output.label"
    loss = "list"

    t_generator = aimage.AggressiveImageGenerator(
        entry=entry,
        label_path=label_path,
        loss=loss,
        target_size=INPUT_SHAPE,
        data_align=0.0,  # adjust data length for each classes
        rescale=rescale,
        shuffle=True,
        verbose=False,
        batch_size=128,
        progress_bar=True,
        data_aug_params=dparam.copy()
    )

    t_x_data = []
    t_y_data = []
    t_f_data = []
    for b in t_generator:
        t_x_data.append(b.images)
        if b.signals is not None and len(b.signals) > 0:
            t_y_data.append(b.signals)
        if b.file_paths is not None:
            t_f_data += b.file_paths
    if len(t_x_data) == 0:
        print("Does not exist data in " + entry)
        exit(0)
    t_x_data = np.concatenate(t_x_data)
    t_y_data = np.concatenate(t_y_data)
    t_f_data = t_f_data
    x_vectors = t_x_data
    y_vectors = t_y_data
    f_paths = t_f_data
    return x_vectors, y_vectors, f_paths


def plot(embedding, x_vectors, y_vectors, f_paths):
    import pyperclip
    drawing = False  # true if mouse is pressed
    ix, iy = -1, -1
    event = None
    gx = 0
    gy = 0

    def draw_rect(e, x, y, flags, param):
        nonlocal gx, gy, ix, iy, drawing, img, event
        gx = x
        gy = y
        event = e
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            ix, iy = x, y
        elif event == cv2.EVENT_MOUSEMOVE:
            pass
        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False

    cv2.namedWindow('')
    cv2.setMouseCallback('', draw_rect)
    canvas = np.zeros((512, 512, 3), dtype=np.uint8)
    plot_h2(canvas, embedding, y_vectors, 0, 0, 0, 0)

    while (1):
        img = canvas.copy()
        if event == cv2.EVENT_MOUSEMOVE:
            if drawing is True:
                cv2.rectangle(img, (ix, iy), (gx, gy), (0, 255, 0), 1)
        elif event == cv2.EVENT_LBUTTONUP:
            cv2.rectangle(img, (ix, iy), (gx, gy), (0, 255, 0), 1)
            hh3, ilist, colors = plot_h2(canvas, embedding, y_vectors, ix, iy, gx, gy)
            event = None
            if len(ilist) > 0:
                plot_x = x_vectors[ilist]
                plot_x = plot_x[0:256]
                pyperclip.copy("\n".join([f_paths[i] for i in ilist]))
                cv2.imshow("list", cv2.cvtColor(aimage.concat_bhwc_image(plot_x), cv2.COLOR_BGR2RGB))
        aimage.show(img)
        k = cv2.waitKey(1) & 0xFF
        if k == 27:
            break
    cv2.destroyAllWindows()

#!/usr/bin/env python3
import os
import sys

import acapture
import pyglview

import evaluator

basepath = os.getcwd()
sys.path.append(basepath)

if len(sys.argv) > 1:
    f = sys.argv[1]
cap = acapture.open(f)
view = pyglview.Viewer(keyboard_listener=cap.keyboard_listener)
model = evaluator.Evaluator()


def loop():
    try:
        check, frame = cap.read()
        if check:
            frame = model.render(frame)
            view.set_image(np.array(frame))
    except Exception as e:
        print(e)
        exit(9)

view.set_loop(loop)
view.start()
print("Main thread ended")

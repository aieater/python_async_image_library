#!/usr/bin/env python3
import os
import acapture
import pyglview
import sys
import traceback

import importlib
import eater_bridge_server as ebs
import os, sys
basepath = os.getcwd()
sys.path.append(basepath)

if len(sys.argv) > 1:
    f = sys.argv[1]
cap = acapture.open(f)
view = pyglview.Viewer(keyboard_listener=cap.keyboard_listener)
import evaluator
model = evaluator.Evaluator()
def loop():
    try:
        check,frame = cap.read()
        if check:
            frame = model.render(frame)
            view.set_image(np.array(frame))
    except:
        traceback.print_exc()
        exit(9)
    pass
view.set_loop(loop)
view.start()
print("Main thread ended")

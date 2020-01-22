#!/usr/bin/env python3

import os,sys
import unicodedata


def get_char_width(c):
    data = unicodedata.east_asian_width(c)
    if data == 'Na' or data == 'H':
        return 1
    return 2

def str_len(string):
    width = 0
    for c in string:
        width += get_char_width(c)
    return width

def ljust(s,mx):
    rest = mx-str_len(s)
    if rest > 0:
        return s + rest * ' '
    return s

def yes_or_no(question, default="yes"):
    CRED='\033[0;31m'
    CCYAN='\033[0;36m'
    CGREEN='\033[0;32m'
    CRESET='\033[0m'
    valid_table = {"yes": True, "y": True, "no": False, "n": False, "1":True, "0":False}
    if default is None:
        prompt = " [y/n] "
    elif default in valid_table:
        if valid_table[default]: prompt = " (default: yes)[Y/n] > "
        else: prompt = " (default: no)[y/N] > "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        print("\033[0;36m" + question + prompt, end="")
        choice = input().lower()
        if default is not None and choice == '':
            if valid_table[default]:
                print("\033[2A")
                print("%s\033[0;32mYes\033[0m"%(question + prompt,),flush=True)
            else:
                print("\033[2A")
                print("%s\033[0;31mNo\033[0m"%(question + prompt,),flush=True)
            return valid_table[default]
        elif choice in valid_table:
            if valid_table[choice]:
                print("\033[2A")
                print("%s\033[0;32mYes\033[0m"%(question + prompt,),flush=True)
            else:
                print("\033[2A")
                print("%s\033[0;31mNo\033[0m"%(question + prompt,),flush=True)
            return valid_table[choice]
        else:
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').")


def selector(options,title="Select an item."):
    if len(options) == 0: return None
    if len(options) == 1: return (0,options[0])
    def pre():print("\033[2A",flush=True)
    import sys
    import time
    import termios
    import contextlib
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
    current = 0
    def dd(i):
        print(" ",title.ljust(20),flush=True,end = '\n')
        index = 0
        for o in options:
            if index == i:
                print("  => ",o.ljust(10),flush=True,end = '\n')
            else:
                print("     ",o.ljust(10),flush=True,end = '\n')
            index+=1
    dd(current)
    with raw_mode(sys.stdin):
        try:
            while True:
                n = ord(sys.stdin.read(1))
                if n == 0x1b:
                    n = ord(sys.stdin.read(1))
                    if n == 0x5b:
                        n = ord(sys.stdin.read(1))
                        if n == 0x41:
                            # top
                            current -= 1
                            current = max(current,0)
                            current = min(current,len(options)-1)
                            for o in range(len(options)+1): pre()
                            dd(current)
                        elif n == 0x42:
                            # bottom
                            current += 1
                            current = max(current,0)
                            current = min(current,len(options)-1)
                            for o in range(len(options)+1): pre()
                            dd(current)
                        elif n == 0x43:
                            pass
                            # right
                        elif n == 0x44:
                            pass
                            # left
                elif n == 0x0a: # Enter
                    return (current,options[current])
        except (KeyboardInterrupt, EOFError):
            pass

def multi_selector(options,title="Select items.",min_count=1,split=10,all=None,preview=None,padding=True,preview_console=False):
    def pre():print("\033[2A",flush=True)
    import sys
    import time
    import termios
    import contextlib
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
    options2d = [[]]
    if all is not None:
        options = [all] + options
    for o in options:
        if len(options2d[-1]) >= split:
            options2d.append([])
        options2d[-1].append(o)
    multi_selected = []
    for o in options:
        multi_selected.append(0)

    current = 0
    page = 0
    max_page = int(len(options)/split)
    list_max = len(options2d[0])

    if len(options) % split > 0:
        max_page += 1

    max_width = 0
    for p in options2d:
        for o in p:
            max_width = max(max_width,str_len(o))
    if padding == False:
        max_width = 0

    def _update_display_(i,ignore=False):
        print("\b\r ",title.ljust(20),flush=True,end = '\n')
        index = 0

        for o in options2d[page]:
            CH = ""
            if i == index and ignore == False:
                #CH = "\033[7m"
                #CH = "\033[4m"
                CH = "\033[4;32m"
                #\033[0;32m
            if multi_selected[page*list_max+index] == 1:
                #"\033[m"
                print(CH,"\r  [*] ",ljust(o,max_width),"\033[0m",flush=True,end = '\n')
            else:
                print(CH,"\r  [ ] ",ljust(o,max_width),"\033[0m",flush=True,end = '\n')
            index += 1
        while index<list_max:
            print("".ljust(max_width+9))
            index += 1
        G = "\033[4;32m"
        R = "\033[0m"
        p = "  "
        if max_page > 1:
            for i in range(max_page):
                if i == page:
                    p += G+str(i+1)+R
                else:
                    p += str(i+1)
                p += " "
        print(p.ljust(max_width+9))

    _update_display_(current)

    with raw_mode(sys.stdin):
        try:
            while True:
                n = ord(sys.stdin.read(1))
                if n == 0x1b:
                    n = ord(sys.stdin.read(1))
                    if n == 0x5b:
                        n = ord(sys.stdin.read(1))
                        if n == 0x41:
                            # top
                            current -= 1
                            current = max(current,0)
                            current = min(current,len(options2d[page])-1)
                            for o in range(list_max+2): pre()
                            _update_display_(current)
                        elif n == 0x42:
                            # bottom
                            current += 1
                            current = max(current,0)
                            current = min(current,len(options2d[page])-1)
                            for o in range(list_max+2): pre()
                            _update_display_(current)
                        elif n == 0x43:
                            # right
                            page += 1
                            page = max(page,0)
                            page = min(page,max_page-1)
                            current = max(current,0)
                            current = min(current,len(options2d[page])-1)
                            for o in range(list_max+2): pre()
                            _update_display_(current)
                        elif n == 0x44:
                            # left
                            page -= 1
                            page = max(page,0)
                            page = min(page,max_page-1)
                            current = max(current,0)
                            current = min(current,len(options2d[page])-1)
                            for o in range(list_max+2): pre()
                            _update_display_(current)
                elif n == 0x0a: # Enter
                    if sum(multi_selected) >= min_count:
                        for o in range(list_max+2): pre()
                        _update_display_(current,True)
                        ret = []
                        if all is not None:
                            multi_selected.pop(0)
                            options.pop(0)
                        i = 0
                        for f in multi_selected:
                            if f == 1: ret += [(i,options[i])]
                            i+=1
                        return ret
                    else:
                        for o in range(list_max+2): pre()
                        _update_display_(current)

                elif n == 0x20: # Space
                    if all and current == 0 and page == 0:
                        if multi_selected[current] == 0:
                            for i in range(len(multi_selected)):
                                multi_selected[i] = 1
                        else:
                            for i in range(len(multi_selected)):
                                multi_selected[i] = 0
                    else:
                        if multi_selected[page*list_max+current] == 0:
                            multi_selected[page*list_max+current] = 1
                        else:
                            multi_selected[page*list_max+current] = 0
                            multi_selected[0] = 0
                    for o in range(list_max+2): pre()
                    _update_display_(current)
                elif n == 0x40: # @
                    try:
                        import aimage
                        if preview:
                            if preview[page*list_max+current] is not None:
                                for i in range(100): print("\b")
                                if aimage.isnotebook(): import IPython; IPython.display.clear_output()
                                else: print("\b\033[0;0f",end="")
                                print("Previewing...\b")
                                aimage.show(preview[page*list_max+current],preview_console)
                                aimage.clear_output()
                    except:
                        pass
        except (KeyboardInterrupt, EOFError):
            pass

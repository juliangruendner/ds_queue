"""
  Copyright notice
  ================

  Copyright (C) 2018
      Julian Gruendner    <juliangruendner@googlemail.com>

"""

import threading

COLOR_RED = 31
COLOR_GREEN = 32
COLOR_YELLOW = 33
COLOR_BLUE = 34
COLOR_PURPLE = 35

def colorize(s, color=COLOR_RED):
    return (chr(0x1B) + "[0;%dm" % color + str(s) + chr(0x1B) + "[0m")

class Logger:
    def __init__(self, log_level=0):
        self.log_level = log_level

    def __out(self, msg, head, color):
        tid = threading.current_thread().ident & 0xffffffff
        tid = " %s " % colorize("<%.8x>" % tid, COLOR_PURPLE)
        print(colorize(head, color) + tid + msg)

    def info(self, msg):
        self.__out(msg, "[*]", COLOR_GREEN)

    def warning(self, msg):
        self.__out(msg, "[#]", COLOR_YELLOW)

    def error(self, msg):
        self.__out(msg, "[!]", COLOR_RED)

    def debug(self, msg):
        if self.log_level > 0:
            self.__out(msg, "[D]", COLOR_BLUE)

    def printMessages(self, req):
        if self.log_level > 0:

            if not req.isResponse():
                print("#########REQUEST##########\n")
            else:
                print("=========RESPONSE=========")

            print(req)

            if req.body:
                print("----------body---------")
                print(req.body)
                print("----------body---------\n")
                print("----------------END---------------\n")

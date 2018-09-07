#!/usr/bin/env python

"""
  Copyright notice
  ================
  
  Copyright (C) 2011
      Roberto Paleari     <roberto.paleari@gmail.com>
      Alessandro Reina    <alessandro.reina@gmail.com>
  
  This program is free software: you can redistribute it and/or modify it under
  the terms of the GNU General Public License as published by the Free Software
  Foundation, either version 3 of the License, or (at your option) any later
  version.
  
  HyperDbg is distributed in the hope that it will be useful, but WITHOUT ANY
  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
  A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License along with
  this program. If not, see <http://www.gnu.org/licenses/>.
  
"""

import sys
import getopt

import sys
sys.path.append('../ds_common')
from core import *

def show_help():
    print("""\
Syntax: python %s <options>
 -a <addr>         listen address (default 0.0.0.0)
 -d <filename>     on termination, dump requests & responses to file
 -h                show this help screen
 -p <port>         listen port  (default 8080)
 -r <host:[port]>  redirect HTTP traffic to target host (default port: 80)
 -v                be more verbose
 -x <filename>     load a ProxPy plugin
 -i                activate queue-poll
 -s                activate https
 -t <requestTimeout:responseTimeout> set requst and response timeout note "None" is for no timeout
""" % sys.argv[0])

def parse_options():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "a:d:hp:r:vx:ist:")
    except getopt.GetoptError as e:
        print(str(e))
        show_help()
        exit(1)

    opts = dict([(k.lstrip('-'), v) for (k,v) in opts])

    if 'h' in opts:
        show_help()
        exit(0)

    ps = ProxyState()

    if 'v' in opts:
        ps.log.verbosity += 1

    if 'd' in opts:
        ps.dumpfile = opts['d']

    if 'p' in opts:
        ps.listenport = int(opts['p'])
        
    if 'a' in opts:
        ps.listenaddr = opts['a']

    # Check and parse redirection host
    if 'r' in opts:
        h = opts['r']
        if ':' not in h:
            p = 80
        else:
            h,p = h.split(':')
            p = int(p)
        ps.redirect = (h, p)

    if 't' in opts:
        timeouts = opts['t']
        req_t,res_t = timeouts.split(':')
        
        if req_t != "None":
            ps.requestTimeout = int(req_t)

        if res_t != "None":
            ps.responseTimeout = int(res_t)

    if 'i' in opts:
        ps.activateQp = True
    else:
        ps.activateQp = False

    ps.https = True if 's' in opts else False

    # Load an external plugin
    if 'x' in opts:
        ps.plugin = ProxyPlugin(opts['x'])


    return ps

def main():
    global proxystate
    proxystate = parse_options()
    proxyServer = ProxyServer(proxystate)
    proxyServer.startProxyServer()

if __name__ == "__main__":
    global proxystate
    try:
        main()
    except KeyboardInterrupt as e:
        nreq, nres = proxystate.history.count()
        proxystate.log.info("Terminating... [%d requests, %d responses]" % (nreq, nres))
        if proxystate.dumpfile is not None:
            data = proxystate.history.dumpXML()
            f = open(proxystate.dumpfile, 'w')
            f.write(data)
            f.close()



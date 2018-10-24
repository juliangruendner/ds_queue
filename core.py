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
import queue
import socketserver
import http.server
import socket
import threading
import http.client
import time
import os
import urllib.request, urllib.parse, urllib.error
import ssl
import copy
import sys

from history import *
from ds_http import *
from ds_https import *
from logger import Logger

DEFAULT_CERT_FILE = "./cert/ncerts/proxpy.pem"

proxystate = None

class ProxyHandler(socketserver.StreamRequestHandler):
    def __init__(self, request, client_address, server):
        self.peer = True
        self.keepalive = False
        self.target = None

        # Just for debugging
        self.counter = 0
        self._host = None
        self._port = 0

        socketserver.StreamRequestHandler.__init__(self, request, client_address, server)
    
    def createConnection(self, host, port):
        global proxystate

        if self.target and self._host == host:
            return self.target

        try:
            # If a SSL tunnel was established, create a HTTPS connection to the server
            if self.peer:
                # FIXME - change to verify context
                defContext = ssl._create_unverified_context()
                conn = http.client.HTTPSConnection(host, port, context=defContext)
            else:
                # HTTP Connection
                conn = http.client.HTTPConnection(host, port)
        except HTTPException as e:
            proxystate.log.debug(e.__str__())

        # If we need a persistent connection, add the socket to the dictionary
        if self.keepalive:
            self.target = conn

        self._host = host
        self._port = port
            
        return conn

    def sendResponse(self, res):
        self.wfile.write(res.encode('latin-1'))

    def finish(self):
        if not self.keepalive:
            if self.target:
                self.target.close()
            return socketserver.StreamRequestHandler.finish(self)

        # Otherwise keep-alive is True, then go on and listen on the socket
        return self.handle()

    def handle(self):
        global proxystate

        if self.keepalive:
            if self.peer:
                HTTPSUtil.wait_read(self.request)
            else:
                HTTPUtil.wait_read(self.request)

            # Just debugging
            if self.counter > 0:
                proxystate.log.debug(str(self.client_address) + ' socket reused: ' + str(self.counter))
            self.counter += 1

        try:
            req = HTTPRequest.build(self.rfile)
        except Exception as e:
            proxystate.log.debug(e.__str__() + ": Error on reading request message")
            return
            
        if req is None:
            return

        # Delegate request to plugin
        #req = ProxyPlugin.delegate(ProxyPlugin.EVENT_MANGLE_REQUEST, req.clone())
        req = req.clone()
        #proxystate.log.printMessages(req)

        # if you need a persistent connection set the flag in order to save the status
        if req.isKeepAlive():
            self.keepalive = True
        else:
            self.keepalive = False

        if proxystate.activateQp:
            self.handleQpRequest(req)
        else:
            # Target server host and port
            host, port = ProxyState.getTargetHost(req)
            self.execRequest(host, port, req)

    def _request(self, conn, method, path, params, headers):
        global proxystate
        conn.putrequest(method, path, skip_host = True, skip_accept_encoding = True)

        for header,v in headers.items():
            # auto-fix content-length
            if header.lower() == 'content-length':
                conn.putheader(header, str(len(params)))
            else:
                for i in v:
                    conn.putheader(header, i)
        
        conn.endheaders()
        if len(params) > 0:
            conn.send(params)

    def doRequest(self, conn, method, path, params, headers):
        global proxystate
        try:
            self._request(conn, method, path, params, headers)
            return True
        except IOError as e:
            proxystate.log.error("%s: %s:%d" % (e.__str__(), conn.host, conn.port))
            return False


    def execRequest(self, host, port, req):
        conn = self.createConnection(host, port)
        if not self.doRequest(conn, req.getMethod(), req.getPath(), req.getBody(), req.headers): return ''
        res = self._getresponse(conn)
        data = res.serialize()
        self.sendResponse(data)

    def handleQpRequest(self, req):
        #TODO handle qp request
        queryParams = req.getQueryParams()

        if 'getQueuedRequest' in queryParams: 
            self.getQueuedRequest()
        elif 'setQueuedResponse' in queryParams: 
            self.setQueuedResponse(req)
        elif 'resetQueue' in queryParams:
            self.resetQueue()
        else: 
            self.execQueueRequest(req)

    # resets the request and response queues
    def resetQueue (self):
        proxystate.reqQueue.queue.clear()
        proxystate.resQueue.queue.clear()

        res = HTTPResponse('HTTP/1.1', 200, 'OK')
        res.body ="queue reset"
        self.sendResponse(res.serialize())
    
    # gets the next queued request and sends it back
    def execQueueRequest(self, req):
        self.setQueuedRequest(req)
        self.getQueuedResponse()

    # sets the a queued request
    def setQueuedRequest(self, req):

        try:
            proxystate.reqQueue.put(req)
        except queue.Full as e:
            proxystate.log.debug(e.__str__())
            return
        
    # gets the next queued request and sends it back
    def getQueuedRequest(self):
        
        try:
            req = proxystate.reqQueue.get(timeout=proxystate.requestTimeout)
        except queue.Full as e:
            proxystate.log.debug(e.__str__())
            return
        except queue.Empty:
            res = HTTPResponse('HTTP/1.1', 204, 'NO CONTENT')
            self.sendResponse(res.serialize())
            return

        res = HTTPResponse('HTTP/1.1', 200, 'OK')
        res.body = req.serialize()

        self.sendResponse(res.serialize())
        
    def setQueuedResponse(self, req):

        try:
            proxystate.resQueue.put(req.getBody())
        except queue.Full as e:
            proxystate.log.debug(e.__str__())
            return

        res = HTTPResponse('HTTP/1.1', 200, 'OK')
        self.sendResponse(res.serialize())

    def getQueuedResponse(self):
        res = proxystate.resQueue.get(timeout=proxystate.responseTimeout)

        #TODO tidy up if no resposne => empty request queue as well
        # proxystate.reqQueue.
        
        #proxystate.log.printMessages(res)
        self.sendResponse(res)

    #this method is not needed in our case as our proxy is not a ssh tunnel
    def doCONNECT(self, host, port, req):

        global proxystate

        socket_req = self.request
        certfilename = DEFAULT_CERT_FILE
        socket_ssl = ssl.wrap_socket(socket_req, server_side = True, certfile = certfilename, 
                                     ssl_version = ssl.PROTOCOL_SSLv23, do_handshake_on_connect = False)

        HTTPSRequest.sendAck(socket_req)
        
        host, port = socket_req.getpeername()
        proxystate.log.debug("Send ack to the peer %s on port %d for establishing SSL tunnel" % (host, port))

        while True:
            try:
                socket_ssl.do_handshake()
                break
            except (ssl.SSLError, IOError):
                # proxystate.log.error(e.__str__())
                return

        # Switch to new socket
        self.peer    = True
        self.request = socket_ssl
        self.setup()
        self.handle()

    def _getresponse(self, conn):
        try:
            res = conn.getresponse()
        except http.client.HTTPException as e:
            proxystate.log.debug(e.__str__() + ": Error getting response")
            # FIXME: check the return value into the do* methods
            return None

        body = res.read().decode('latin-1')
        if res.version == 10:
            proto = "HTTP/1.0"
        else:
            proto = "HTTP/1.1"

        code = res.status
        msg = res.reason
        headers = res.getheaders()
        headers = dict((x, y) for x, y in headers)
        res = HTTPResponse(proto, code, msg, headers, body)

        if 'Transfer-Encoding' in headers.keys():
            res.removeHeader('Transfer-Encoding')
            res.addHeader('Content-Length', str(len(body)))        

        #proxystate.log.printMessages(res)

        return res

class ThreadedHTTPProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

    def verify_request(self, request, client_address):

        if not proxystate.allowed_ips:
            return True

        if client_address[0] in proxystate.allowed_ips:
            return True

        print("rejecting: " + client_address[0] )
        return False


class ProxyServer():    
    def __init__(self, init_state):
        global proxystate
        proxystate = init_state
        self.proxyServer_port = proxystate.listenport
        self.proxyServer_host = proxystate.listenaddr
        

    def startProxyServer(self):
        global proxystate
        
        self.proxyServer = ThreadedHTTPProxyServer((self.proxyServer_host, self.proxyServer_port), ProxyHandler)

        #start https server
        if proxystate.https == True:
            print("activating https", file=sys.stderr)
            self.proxyServer.socket = ssl.wrap_socket(self.proxyServer.socket, certfile=DEFAULT_CERT_FILE, server_side=True)

        # Start a thread with the server (that thread will then spawn a worker
        # thread for each request)
        server_thread = threading.Thread(target = self.proxyServer.serve_forever)
    
        # Exit the server thread when the main thread terminates
        server_thread.setDaemon(True)
        proxystate.log.info("Server %s listening on port %d" % (self.proxyServer_host, self.proxyServer_port))
        server_thread.start()

        while True:
            time.sleep(0.1)

    def stopProxyServer(self):
        self.proxyServer.shutdown()

class ProxyState:
    def __init__(self, port = 8080, addr = "0.0.0.0"):
        # Configuration options, set to default values
        self.plugin     = ProxyPlugin()
        self.listenport = port
        self.listenaddr = addr
        self.dumpfile   = None

        # Internal state
        self.log        = Logger()
        self.history    = HttpHistory()
        self.redirect   = None
        self.reqQueue = queue.Queue()
        self.resQueue = queue.Queue()
        self.responseTimeout = None
        self.requestTimeout = None
        self.allowed_ips = None

    @staticmethod
    def getTargetHost(req):
        global proxystate
        # Determine the target host (check if redirection is in place)
        if proxystate.redirect is None:
            target = req.getHost()
        else:
            target = proxystate.redirect

        return target

class ProxyPlugin:
    EVENT_MANGLE_REQUEST  = 1
    EVENT_MANGLE_RESPONSE = 2

    __DISPATCH_MAP = {
        EVENT_MANGLE_REQUEST:  'proxy_mangle_request',
        EVENT_MANGLE_RESPONSE: 'proxy_mangle_response',
        }

    def __init__(self, filename = None):
        self.filename = filename
    
        if filename is not None:
            import imp
            assert os.path.isfile(filename)
            self.module = imp.load_source('plugin', self.filename)
        else:
            self.module = None

    def dispatch(self, event, *args):
        if self.module is None:
            # No plugin
            return None

        assert event in ProxyPlugin.__DISPATCH_MAP
        try:
            a = getattr(self.module, ProxyPlugin.__DISPATCH_MAP[event])
        except AttributeError:
            a = None

        if a is not None:
            r = a(*args)
        else:
            r = None
            
        return r

    @staticmethod
    def delegate(event, arg):
        global proxystate

        # Allocate a history entry
        hid = proxystate.history.allocate()

        if event == ProxyPlugin.EVENT_MANGLE_REQUEST:
            proxystate.history[hid].setOriginalRequest(arg)
            # Process this argument through the plugin
            mangled_arg = proxystate.plugin.dispatch(ProxyPlugin.EVENT_MANGLE_REQUEST, arg.clone())

        elif event == ProxyPlugin.EVENT_MANGLE_RESPONSE:
            proxystate.history[hid].setOriginalResponse(arg)

            # Process this argument through the plugin
            mangled_arg = proxystate.plugin.dispatch(ProxyPlugin.EVENT_MANGLE_RESPONSE, arg.clone())

        if mangled_arg is not None:
            if event == ProxyPlugin.EVENT_MANGLE_REQUEST:
                proxystate.history[hid].setMangledRequest(mangled_arg)
            elif event == ProxyPlugin.EVENT_MANGLE_RESPONSE:
                proxystate.history[hid].setMangledResponse(mangled_arg)

            # HTTPConnection.request does the dirty work :-)
            ret = mangled_arg
        else:
            # No plugin is currently installed, or the plugin does not define
            # the proper method, or it returned None. We fall back on the
            # original argument
            ret = arg

        return ret


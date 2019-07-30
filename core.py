"""
  Copyright notice
  ================

  Copyright (C) 2018
      Julian Gruendner     <juliangruendner@googlemail.com>

"""
import queue
import socketserver
import http.server
import threading
import http.client
import time
import ssl
import uuid
import os
import logging
import socket

from ds_http.ds_http import HTTPUtil, HTTPRequest, HTTPResponse
from logger import Logger

DEFAULT_CERT_FILE = "./cert/do_cert/queue.pem"
CACERT = "./cert/do_cert/queuecacert.pem"

proxystate = None

class ProxyHandler(socketserver.StreamRequestHandler):
    def __init__(self, request, client_address, server):
        self.peer = True
        self.keepalive = False
        self.target = None

        # Just for debugging
        self._host = None
        self._port = 0

        socketserver.StreamRequestHandler.__init__(self, request, client_address, server)

    def handle(self):

        global proxystate

        if self.keepalive:
            if self.peer:
                HTTPSUtil.wait_read(self.request)
            else:
                HTTPUtil.wait_read(self.request)

        try:
            req = HTTPRequest.build(self.rfile)
        except Exception as e:
            proxystate.log.debug(e.__str__() + ": Error on reading request message")
            return

        if req is None:
            return

        req = req.clone()
        orig_ip = req.getHeader("X-Real-IP")

        if len(orig_ip) > 0:
            orig_ip = orig_ip[0]

        if proxystate.allowed_ips and orig_ip not in proxystate.allowed_ips:
            print("rejecting ip : "+ str(orig_ip))
            return
        
        if req.isKeepAlive():
            self.keepalive = True
        else:
            self.keepalive = False

        if proxystate.activateQp:
            self.handleQpRequest(req)
        else:
            host, port = ProxyState.getTargetHost(req)
            self.execRequest(host, port, req)

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
        if not self.doRequest(conn, req.getMethod(), req.getPath(), req.getBody(), req.headers):
            return ''

        res = self._getresponse(conn)
        self.sendResponse(res.serialize())

    def handleQpRequest(self, req):

        queryParams = req.getQueryParams()

        if 'getQueuedRequest' in queryParams:
            self.getQueuedRequest()
        elif 'setQueuedResponse' in queryParams:
            self.setQueuedResponse(req)
        elif 'resetQueue' in queryParams:
            self.resetQueue()
        elif 'ping' in queryParams:
            self.ping()
        else:
            self.execQueueRequest(req)

    def execQueueRequest(self, req):
        reqUu = str(uuid.uuid4())
        self.setQueuedRequest(req, reqUu)
        self.getQueuedResponse(reqUu)

    def setQueuedRequest(self, req, reqUu):

        try:
            req.addHeader('reqId', reqUu)
            proxystate.reqQueue.put(req)
            proxystate.resQueueList[reqUu] = queue.Queue()
        except queue.Full as e:
            proxystate.log.debug(e.__str__())
            return

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
            reqId = req.getQueryParams()['reqId'][0]
            res = req.getBody()
            proxystate.resQueueList[reqId].put(res)
        except queue.Full as e:
            proxystate.log.debug(e.__str__())
            return

        res = HTTPResponse('HTTP/1.1', 200, 'OK')
        self.sendResponse(res.serialize())

    def getQueuedResponse(self, reqId):
        res = proxystate.resQueueList[reqId].get(timeout=proxystate.responseTimeout)
        del proxystate.resQueueList[reqId]

        # proxystate.log.printMessages(res)
        self.sendResponse(res)

    def resetQueue(self):
        proxystate.reqQueue.queue.clear()
        res = HTTPResponse('HTTP/1.1', 200, 'OK', body="queue reset \n")
        self.sendResponse(res.serialize())

    def ping(self):
        res = HTTPResponse('HTTP/1.1', 200, 'OK', body="queue is still alive \n")
        self.sendResponse(res.serialize())

    def createConnection(self, host, port):
        global proxystate

        if self.target and self._host == host:
            return self.target

        try:
            if self.peer:
                defContext = ssl._create_unverified_context()
                conn = http.client.HTTPSConnection(host, port, context=defContext)
            else:
                # HTTP Connection
                conn = http.client.HTTPConnection(host, port)
        except http.client.HTTPException as e:
            proxystate.log.debug(e.__str__())

        #  presistend connection? , add the socket to the dictionary
        if self.keepalive:
            self.target = conn

        self._host = host
        self._port = port

        return conn

    def sendResponse(self, res):
        self.wfile.write(res.encode('latin-1'))
        self.wfile.flush()  # see if flushing improves performance

    def _request(self, conn, method, path, params, headers):

        conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)

        for header, v in headers.items():
            if header.lower() == 'content-length':
                conn.putheader(header, str(len(params)))
            else:
                for i in v:
                    conn.putheader(header, i)

        conn.endheaders()

        if len(params) > 0:
            conn.send(params.encode('latin-1'))

    def _getresponse(self, conn):
        try:
            res = conn.getresponse()
        except http.client.HTTPException as e:
            proxystate.log.debug(e.__str__() + ": Error getting response")
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

        return res


class ThreadedHTTPProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class ProxyServer():
    def __init__(self, init_state):
        global proxystate
        proxystate = init_state
        self.proxyServer_port = proxystate.listenport
        self.proxyServer_host = proxystate.listenaddr



    def startProxyServer(self):
        global proxystate

        self.proxyServer = ThreadedHTTPProxyServer((self.proxyServer_host, self.proxyServer_port), ProxyHandler)

        if proxystate.https:

            if os.path.isfile(CACERT):
                self.proxyServer.socket = ssl.wrap_socket(self.proxyServer.socket, certfile=DEFAULT_CERT_FILE, ca_certs=CACERT, server_side=True)
            else:
                self.proxyServer.socket = ssl.wrap_socket(self.proxyServer.socket, certfile=DEFAULT_CERT_FILE, server_side=True)

        server_thread = threading.Thread(target=self.proxyServer.serve_forever)

        server_thread.setDaemon(True)
        proxystate.log.info("Server %s listening on port %d" % (self.proxyServer_host, self.proxyServer_port))
        server_thread.start()

        while True:
            time.sleep(0.1)

    def stopProxyServer(self):
        self.proxyServer.shutdown()


class ProxyState:
    def __init__(self, port=8001, addr="0.0.0.0"):
        self.listenport = port
        self.listenaddr = addr

        # Internal state
        self.log = Logger()
        self.log_level = logging.ERROR
        self.redirect = None
        self.reqQueue = queue.Queue()
        self.resQueueList = {}
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

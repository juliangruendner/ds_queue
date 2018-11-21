#!/bin/sh
openssl req -config openssl.cnf -extensions v3_ca -days 3650 -new -x509 -keyout ./ca_cert/queue.key -out ./ca_cert/queueca.crt -nodes
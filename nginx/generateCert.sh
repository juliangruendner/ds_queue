openssl req -nodes -config openssl.cnf -x509 -newkey rsa:4096 -keyout pollkey.pem -out pollcert.pem -days 99999
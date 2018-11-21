
rm ./ca_cert/*
rm ./do_cert/*
echo "01" >> ./ca_cert/serial
touch ./ca_cert/index.txt

./createCA.sh
./createCert.sh do_cert/queue

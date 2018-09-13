#python3 ds_queue.py -a 127.0.0.1 -p 8001 -r localhost:8843 -d proxyLog.logs -v -s
#python3 ds_queue.py -a 127.0.0.1 -p 8001 -r localhost:8843 -d proxyLog.logs -v -i -s
python3 ds_queue.py -a 0.0.0.0 -p 8001 -r localhost:8843 -d proxyLog.logs -v -i -s -t 10:10
#python3 ds_queue.py -a 127.0.0.1 -p 8001 -r localhost:8843 -d proxyLog.logs -i -s
#python ds_queue.py -a 127.0.0.1 -p 8001 -r localhost:8880 -d proxyLog.logs -v -x plugins/changeagent.py
# nohup python3 ds_queue.py -a 0.0.0.0 -p 80 -r localhost:80 -d proxyLog.logs -v -i -t 10:10 &  # start on server
# start in docker container
#python3 /root/ds_queue/ds_queue.py -a 0.0.0.0 -p 8001 -r datashield_opal:8443 -d proxyLog.logs -v -i -s 
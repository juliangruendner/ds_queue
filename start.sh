# python proxpy.py -a 127.0.0.1 -p 8001 -r localhost:8843 -d proxyLog.logs -v -s
# python proxpy.py -a 127.0.0.1 -p 8001 -r localhost:8843 -d proxyLog.logs -v -i -s
python proxpy.py -a 127.0.0.1 -p 8001 -r localhost:8843 -d proxyLog.logs -i -s
#python proxpy.py -a 127.0.0.1 -p 8001 -r localhost:8880 -d proxyLog.logs -v -x plugins/changeagent.pys
FROM python:3

ADD . /root/ds_queue
RUN cd /root/ds_queue/cert && ./generateNewProdCert.sh
RUN pip install ds-common

CMD bash -c '/root/ds_queue/q_admin.sh start "$TIMEOUT_QUEUE_AND_POLL" "$ALLOWED_IPS" "$LOG_LEVEL"'
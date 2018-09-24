# uncomment the next to lines to configure your queue

# TIMEOUT_QUEUE_AND_POLL='-t 10:10'
#ALLOWED_IPS='-c 140.0.0.1,140.0.0.1'


if [[ $(which docker) ]]; then
    echo "docker already installled, version is: "
    docker -v
else
    echo "docker not installed, installing docker:"
    ../install_docker.sh
fi

docker-compose -f docker-compose.prod.yml up -d

printf "Starting queue in background"
docker exec -d queue_server_prod bash -c "cd /root/ds_queue && ./q_admin.sh start $TIMEOUT_QUEUE_AND_POLL"

printf "Checking if queue is running ... \n "
docker exec queue_server_prod bash -c "cd /root/ds_queue && ./q_admin.sh status"

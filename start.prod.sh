# uncomment the next to lines to configure your queue

TIMEOUT_QUEUE_AND_POLL=${TIMEOUT_QUEUE_AND_POLL:-"-t 10:10"}
ALLOWED_IPS=${ALLOWED_IPS:-""}


if [[ $(which docker) ]]; then
    echo "docker already installled, version is: "
    docker -v
else
    echo "docker not installed, installing docker:"
    ../install_docker.sh
fi

docker-compose -f docker-compose.prod.yml up -d

printf "Starting queue in background \n"
docker exec -d queue_server_prod bash -c "cd /root/ds_queue && ./q_admin.sh start '$TIMEOUT_QUEUE_AND_POLL' '$ALLOWED_IPS' "

printf "Checking if queue is running ... \n "
docker exec queue_server_prod bash -c "cd /root/ds_queue && ./q_admin.sh status"

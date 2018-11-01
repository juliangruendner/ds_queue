docker exec queue_server_prod bash -c "cd /root/ds_queue && ./q_admin.sh stop"
docker-compose -f docker-compose.prod.yml stop

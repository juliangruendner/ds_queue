COMMAND=$1
TIMEOUT_QUEUE_AND_POLL=${2:-"-t 10:10"}
ALLOWED_IPS=${3:-""}

function getQueueStatus() {

    if [ "" == "$(pgrep -f queue.py)" ]; then 
        echo "Queue Stopped"
    else
        echo "Queue Running"
    fi
}

case "$COMMAND" in
            start )
            echo "Starting queue on port 443 with timeout $TIMEOUT_QUEUE_AND_POLL"
            cd /root/ds_queue && python3 ds_queue.py -a 0.0.0.0 -p 443 -r localhost:8843 -d proxyLog.logs -v -i -s $TIMEOUT_QUEUE_AND_POLL $ALLOWED_IPS
            ;;
        
        stop )
            echo "Stopping queue ..."
            kill $(pgrep -f queue)
            ;;

        status )
            getQueueStatus
            ;;
        
        * )
            echo $"Usage: $0 {start|stop|status|}"
            exit 1

esac

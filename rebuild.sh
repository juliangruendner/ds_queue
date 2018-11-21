docker build -f Dockerfile.queue -t ds_queue .
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
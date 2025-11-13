echo "Starting api server"
cd /var/ossec/wodles/api/
uvicorn api:app --host 0.0.0.0 --port 9001



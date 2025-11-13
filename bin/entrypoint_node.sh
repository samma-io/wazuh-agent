#!/bin/bash

#Generae random agent name
RANDOM_NAME=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 10)



export MANAGER_URL="${MANAGER_URL:-localhost}"
export MANAGER_PORT="${MANAGER_PORT:-1516}"
export SERVER_URL="${SERVER_URL:-localhost}"
export SERVER_PORT="${SERVER_PORT:-1515}"
export NAME="${NAME:-agent}-${RANDOM_NAME}"
echo $NAME
export GROUP="${GROUP:-default}"
export ENROL_TOKEN="${ENROL_TOKEN:-PASSWORD}"

echo "Setup register key"
echo $ENROL_TOKEN > /var/ossec/etc/authd.pass

echo "Setup Config"
envsubst < "/opt/ossec/ossec.tpl" > "/var/ossec/etc/ossec.conf"




echo "Startin up Wazuh Client"
/var/ossec/bin/wazuh-control start
echo "Starting Health and Ready"
cd /web && ./ready.sh &



tail -f /var/ossec/logs/*


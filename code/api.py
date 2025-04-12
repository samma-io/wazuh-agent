
import socket
import sqlite3
import sys

try:
    import boto3
except ImportError:
    print('ERROR: boto3 module is required.')
    sys.exit(4)


import configparser
import copy
import gzip
import io
import json
import operator
import re
import zipfile
import zlib

import time

from botocore import config, exceptions
from datetime import datetime
from datetime import timezone
from os import path


from typing import Union

from fastapi import Request, FastAPI

app = FastAPI()




    
def send_msg(msg):
        """
        Sends an event to the Wazuh Queue

        :param msg: JSON message to be sent.
        :param dump_json: If json.dumps should be applied to the msg
        """
        
        #use defult decoder else use from json
        MESSAGE_HEADER = "1:Wazuh-AWS:" 
        if 'decoder' in msg:
            MESSAGE_HEADER = "1:{0}:".format(msg['decoder'])
        else:
            MESSAGE_HEADER = "1:Wazuh-AWS:"


        print("Message head "+MESSAGE_HEADER)
        msg['ingest']="api"
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            s.connect("/var/ossec/queue/sockets/queue")
            testMessage='1:/var/log/syslog:localhost salute: Hello world.'
            messgage = "{header}{msg}".format(header=MESSAGE_HEADER,
                                                 msg=json.dumps(msg))
            print(messgage)
            encoded_msg = messgage.encode()

            s.send(encoded_msg)
            s.close()
            return {"reply":"saved"}
        except socket.error as e:
            if e.errno == 111:
                print("Wazuh must be running.")
                return {"reply":"Wazuh must be running."}
            elif e.errno == 90:
                print("Message too long to send to Wazuh.  Skipping message...")
                print('+++ ERROR: Message longer than buffer socket for Wazuh. Consider increasing rmem_max. '
                                'Skipping message...', 1)
            else:
                print("Error sending message to wazuh: {}".format(e))
                return {"reply":"Error sending message to wazuh"}
        except Exception as e:
            print("Error sending message to wazuh: {}".format(e))
            return {"reply":"Error sending message to wazuh"}




@app.put("/")
async def read_root(request: Request):
    try:
        jsonData = await request.json()
    except:
        return {"reply":"Datas was not valid json try again"}
    return send_msg(jsonData)


@app.put("/batch")
async def read_root(request: Request):
    try:
        jsonData = await request.json()
    except:
        return {"reply":"Datas was not valid json try again"}
    for data in jsonData:
        send_msg(data)
    
    return {"reply":"batch data has bean added"}


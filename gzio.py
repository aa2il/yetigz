###############################################################################

# Class to communitated witht eh Yeti Goal Zero

###############################################################################

from datetime import datetime
import requests
import json

HEADER = {
    "Content-Type": "application/json",
    "User-Agent": "YetiApp/1340 CFNetwork/1125.2 Darwin/19.4.0",
    "Connection": "keep-alive",
    "Accept": "application/json",
    "Accept-Language": "en-us",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
}

###############################################################################

# Object to communicate with the yeti gz
class YetiGZ():

    def __init__(self,ADDR):

        self.URL='http://'+ADDR
        self.now=datetime.now()
        
        # Open connection to yeti gz
        self.session = requests.Session()

    # Function to query sysinfo
    def get_sysinfo(self,TimeOut=10):
        print('\n=========== GET SYSINFO ==============\n')
        self.now=datetime.now()
        print('now=',self.now)
        try:
            resp = self.session.get(self.URL+'/sysinfo',timeout=TimeOut)
        except requests.exceptions.Timeout:
            print("GET_SYSINFO: GET Timed out :-(")
            return None
        self.sysinfo = resp.json()
        print('sysinfo=',json.dumps(self.sysinfo,indent=4))
        print('Status=',resp.status_code)
        return self.sysinfo

    # Get state
    def get_state(self,TimeOut=10):
        print('\n=========== GET STATE ==============\n')
        #print(URL)
        try:
            resp = self.session.get(self.URL+'/state',timeout=TimeOut)
        except requests.exceptions.Timeout:
            print("GET_STATE: GET Timed out :-(")
            return None
        
        self.state = resp.json()
        print('state=',json.dumps(self.state,indent=4))
        print('Status=',resp.status_code)
        print('Headers=',resp.headers)
        print('Request url=',resp.request.url)
        print('Request Headers=',resp.request.headers)
        print('Request body=',resp.request.body)
    
        self.now=datetime.now()
        print(self.now)
        return self.state

    def set_state(self,key,onoff):
        print('\n=========== SET STATE ==============\n')
        self.now=datetime.now()
        print('now=',self.now)

        payload = { key : onoff }
        try:
            resp = self.session.post(self.URL+'/state',headers=HEADER,json=payload)
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            print("SET_STATE: SET Timed out :-(")
            return None
    
        post = resp.json()
        print('post=',json.dumps(post,indent=4))
        print('Status=',resp.status_code)

        return post


###############################################################################

"""
# Get available WiFi nets - this works
print('\n=========== GET WIFI NETS ==============\n')
resp = session.get(URL+'/wifi')
#wifi = json.loads(resp.text)
wifi = resp.json()
print('wifi=',json.dumps(wifi,indent=4))
print('Status=',resp.status_code)

#sys.exit(0)

# Join wlan - this doesnt work
print('\n=========== JOIN WiFi ==============\n')
payload = None
payload = {
    "wifi": {
        "name": "LDVALPACAS2",
        "pass": "????????????"y
    },
    "iot": {
        "env": "prod",
        "hostname": "a1xyddj5i8k7t5-ats.iot.us-east-1.amazonaws.com",
        "endpoint": "https://yeti-prod.goalzeroapp.com/v1/thing"
    }
}

resp = session.post(URL+'/join',headers=HEADER,json=payload)
resp.raise_for_status()
#post2 = json.loads(resp.text)
post2 = resp.json()
print('post2=',json.dumps(post2,indent=4))
print('Status=',resp.status_code)

"""

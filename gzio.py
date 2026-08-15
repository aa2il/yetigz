################################################################################
#
# gzio.py - Rev 1.0
# Copyright (C) 2026 by Joseph B. Attili, joe DOT aa2il AT gmail DOT com
#
# Classes to communitate with the Yeti GoalZero Battery and Renergy Wanderer
# Charge Controller.  
#
################################################################################
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
################################################################################

from datetime import datetime
import requests
import json

import sys,os,time
from utilities import list_all_serial_devices,error_trap, \
    find_serial_device,find_serial_device_by_serial_id
import serial

################################################################################

HEADER = {
    "Content-Type": "application/json",
    "User-Agent": "YetiApp/1340 CFNetwork/1125.2 Darwin/19.4.0",
    "Connection": "keep-alive",
    "Accept": "application/json",
    "Accept-Language": "en-us",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
}

DEVICE_ID='CP2102 USB to UART'
BAUD=115200

###############################################################################

# Object to communicate directly with the yeti gz via http/wifi
class YetiGZ():

    def __init__(self,ADDR):

        self.URL='http://'+ADDR
        self.now=datetime.now()
        self.sysinfo = None
        self.state = None
        self.name = 'Yeti'
        
        # Open connection to yeti gz
        self.session = requests.Session()

        # Name of output file
        self.fname='gz.dat'

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
        #print('Headers=',resp.headers)
        #print('Request url=',resp.request.url)
        #print('Request Headers=',resp.request.headers)
        #print('Request body=',resp.request.body)
    
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

# Object to communicate with the yeti gz via esp32 interface
# NO LONGER NEEDED - USE CHARGE_CONTROLLER CLASS BELOW
class Yeti_ESP32():

    def __init__(self):

        self.now=datetime.now()
        self.sysinfo = None
        self.state = None
        self.name = 'Yeti'
        
        # Name of output file
        self.fname='gz.dat'

        # Open connection to esp32 web client
        #list_all_serial_devices(True)
        device,vid_pid=find_serial_device(DEVICE_ID,0) 
        print('\tdevice=',device,'\tvid_pid=',vid_pid)

        self.ser = serial.Serial(device,BAUD,timeout=1) 
        print('\tser=',self.ser,'\n')
        time.sleep(5)

        self.read_text()

    # Function to read any resdidual text in the serial port
    def read_text(self):
        txt=''
        while self.ser and self.ser.in_waiting>0:
            txt1 = self.ser.read_all().decode("utf-8",'ignore')
            txt += txt1
            time.sleep(1)
        #print('txt=',txt)

        return txt

    def send_command(self,cmd):
        self.ser.write((cmd+'\n').encode())
        self.ser.flush()
        time.sleep(.1)

        txt=''
        cnt=0
        while '<EOR>' not in txt:
            txt=self.read_text()
            #print('txt=',txt)
            cnt+=1
            if cnt>5:
                print('No response')
                break
            else:
                time.sleep(1)
        #print('txt=',txt)

        return txt
        
    def quit(self):
        print('\nQuitting ...\n')
        self.ser.close()
        sys.exit(0)
    
        
    # Function to query sysinfo
    def get_sysinfo(self,TimeOut=10):
        print('\n=========== GET SYSINFO ==============\n')
        self.now=datetime.now()
        print('now=',self.now)
        
        txt=self.send_command('sysinfo')
        b=txt.split('data=')[1].split('<EOR>')[0].strip()
        #print('b=',b,type(b))
        self.sysinfo=eval(b)
        #self.sysinfo = resp.json()
        print('sysinfo=',json.dumps(self.sysinfo,indent=4))
        return self.sysinfo

    # Get state
    def get_state(self,TimeOut=10):
        print('\n=========== GET STATE ==============\n')

        txt=self.send_command('state')
        try:
            b=txt.split('data=')[1].split('<EOR>')[0].strip()
            #print('b=',b,type(b))
            self.state=eval(b)
            print('state=',json.dumps(self.state,indent=4))
        except Exception as e:
            print("GET STATE: An error occurred:", e)
            return None

        self.now=datetime.now()
        print(self.now)
        return self.state

    # Change state of some attribute, e.g. toggle 12V port
    def set_state(self,key,onoff):
        print('\n=========== SET STATE ==============\n')

        cmd='SET '+key+' '+str(onoff)
        txt=self.send_command(cmd)
        b=txt.split('post=')[1].split('<EOR>')[0].strip()
        #print('b=',b,type(b))
        self.state=eval(b)
        print('state=',json.dumps(self.state,indent=4))
        
        self.now=datetime.now()
        print(self.now)
        return self.state

        return self.state


###############################################################################

# Object to communicate with the Renogy Wanderer via esp32 interface
# NO LONGER NEEDED - USE CHARGE_CONTROLLER CLASS BELOW
class Renogy_ESP32():

    def __init__(self):

        self.now=datetime.now()
        self.sysinfo = None
        self.state = None
        self.name = 'Renogy'
        
        # Name of output file
        self.fname='wanderer.dat'

        # Open connection to esp32 web client
        #list_all_serial_devices(True)
        device,vid_pid=find_serial_device(DEVICE_ID,0) 
        print('\tdevice=',device,'\tvid_pid=',vid_pid)

        self.ser = serial.Serial(device,BAUD,timeout=1)  #,
        #xonxoff=False,dsrdtr=False,rtscts=False)
        print('\tser=',self.ser,'\n')
        time.sleep(5)

        self.read_text()

    # Function to read any resdidual text in the serial port
    def read_text(self):
        txt=''
        while self.ser and self.ser.in_waiting>0:
            txt1 = self.ser.read_all().decode("utf-8",'ignore')
            txt += txt1
            time.sleep(1)
        #print('txt=',txt)

        return txt

    def send_command(self,cmd):
        self.ser.write((cmd+'\n').encode())
        self.ser.flush()
        time.sleep(.1)

        txt=''
        cnt=0
        while '<EOR>' not in txt:
            txt=self.read_text()
            #print('txt=',txt)
            cnt+=1
            if cnt>5:
                print('No response')
                break
            else:
                time.sleep(1)
        #print('txt=',txt)

        return txt
        
    def quit(self):
        print('\nQuitting ...\n')
        self.ser.close()
        sys.exit(0)
    
        
    # Function to query sysinfo
    def get_sysinfo(self,TimeOut=10):
        print('\n=========== GET SYSINFO ==============\n')
        self.now=datetime.now()
        print('now=',self.now)
        
        txt=self.send_command('reninfo')
        print('===txt=',txt)
        b=txt.split('data=')[1].split('<EOR>')[0].strip()
        #print('b=',b,type(b))
        self.sysinfo=eval(b)
        #self.sysinfo = resp.json()
        print('sysinfo=',json.dumps(self.sysinfo,indent=4))
        return self.sysinfo

    # Get state
    def get_state(self,TimeOut=10):
        print('\n=========== GET STATE ==============\n')

        txt=self.send_command('renstate')
        try:
            b=txt.split('data=')[1].split('<EOR>')[0].strip()
            #print('b=',b,type(b))
            self.state=eval(b)
            print('state=',json.dumps(self.state,indent=4))
        except Exception as e:
            print("GET STATE: An error occurred:", e)
            return None

        self.now=datetime.now()
        print(self.now)
        return self.state

    # Change state of some attribute, e.g. toggle 12V port
    def set_state(self,key,onoff):
        print('\n=========== SET STATE ==============\n')

        cmd='SET '+key+' '+str(onoff)
        txt=self.send_command(cmd)
        b=txt.split('post=')[1].split('<EOR>')[0].strip()
        #print('b=',b,type(b))
        self.state=eval(b)
        print('state=',json.dumps(self.state,indent=4))
        
        self.now=datetime.now()
        print(self.now)
        return self.state

        return self.state


###############################################################################

# Object to communicate with the yeti gz or renogy wander via esp32 interface
class CHARGER_IO():

    def __init__(self,name):

        self.now=datetime.now()
        self.sysinfo = None
        self.state = None
        if name in ['Yeti','Renogy']:
            self.name = name
        else:
            print('\nCHARGER_IO *** ERROR *** Unknwo Device Name ***',name)
            sys.exit(0)
        
        # Name of output file
        if self.name=='Yeti':
            self.fname='gz.dat'
        else:
            self.fname='wanderer.dat'

        # Open connection to esp32 web client
        #list_all_serial_devices(True)
        device,vid_pid=find_serial_device(DEVICE_ID,0) 
        print('\tdevice=',device,'\tvid_pid=',vid_pid)

        self.ser = serial.Serial(device,BAUD,timeout=1) 
        print('\tser=',self.ser,'\n')
        time.sleep(5)

        self.read_text()

    # Function to read any resdidual text in the serial port
    def read_text(self):
        txt=''
        while self.ser and self.ser.in_waiting>0:
            txt1 = self.ser.read_all().decode("utf-8",'ignore')
            txt += txt1
            time.sleep(1)
        #print('txt=',txt)

        return txt

    def send_command(self,cmd):
        self.ser.write((cmd+'\n').encode())
        self.ser.flush()
        time.sleep(.1)

        txt=''
        cnt=0
        while '<EOR>' not in txt:
            txt=self.read_text()
            #print('txt=',txt)
            cnt+=1
            if cnt>5:
                print('No response')
                break
            else:
                time.sleep(1)
        #print('txt=',txt)

        return txt
        
    def quit(self):
        print('\nQuitting ...\n')
        self.ser.close()
        sys.exit(0)
    
        
    # Function to query sysinfo
    def get_sysinfo(self,TimeOut=10):
        print('\n=========== GET SYSINFO ==============\n')
        self.now=datetime.now()
        print('now=',self.now)
        
        if self.name=='Yeti':
            txt=self.send_command('sysinfo')
        else:
            txt=self.send_command('reninfo')
        b=txt.split('data=')[1].split('<EOR>')[0].strip()
        #print('b=',b,type(b))
        self.sysinfo=eval(b)
        #self.sysinfo = resp.json()
        print('sysinfo=',json.dumps(self.sysinfo,indent=4))
        return self.sysinfo

    # Get state
    def get_state(self,TimeOut=10):
        print('\n=========== GET STATE ==============\n')

        if self.name=='Yeti':
            txt=self.send_command('state')
        else:
            txt=self.send_command('renstate')
        try:
            b=txt.split('data=')[1].split('<EOR>')[0].strip()
            #print('b=',b,type(b))
            self.state=eval(b)
            print('state=',json.dumps(self.state,indent=4))
        except Exception as e:
            print("GET STATE: An error occurred:", e)
            return None

        self.now=datetime.now()
        print(self.now)
        return self.state

    # Change state of some attribute, e.g. toggle 12V port
    def set_state(self,key,onoff):
        print('\n=========== SET STATE ==============\n')

        if self.name=='Yeti':
            cmd='SET '+key+' '+str(onoff)
        else:
            print('*** SET STATE *** Not yet implemented for',name)
            return
        txt=self.send_command(cmd)
        b=txt.split('post=')[1].split('<EOR>')[0].strip()
        #print('b=',b,type(b))
        self.state=eval(b)
        print('state=',json.dumps(self.state,indent=4))
        
        self.now=datetime.now()
        print(self.now)
        return self.state

        return self.state


###############################################################################

# Some additional test code for the Yeti - some things work and some don't!

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

#!/usr/bin/env -S uv run --script
################################################################################
#
# read_esp32.py - Rev 1.0
# Copyright (C) 2026 by Joseph B. Attili, joe DOT aa2il AT gmail DOT com
#
# Experiments with reading yeti via an esp32 - linux side
# Simple program to read esp32 http/json packets
#
# NOTE - THIS PROGRAM WAS A STEPPING STONE AND IS NO LONGER USED OR MAINTAINED!
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

import sys,os,time
from utilities import list_all_serial_devices,error_trap, \
    find_serial_device,find_serial_device_by_serial_id
import serial

################################################################################

DEVICE_ID='CP2102 USB to UART'
BAUD=115200

################################################################################

# Function to read any resdidual text in the serial port
def read_text(ser):
    txt=''
    while ser and ser.in_waiting>0:
        txt1 = ser.read_all().decode("utf-8",'ignore')
        txt += txt1
        time.sleep(1)
    print('txt=',txt)

    return txt

def send_command(cmd):
    ser.write((cmd+'\n').encode())
    ser.flush()
    time.sleep(.1)

def quit(ser):
    print('\nQuitting ...\n')
    ser.close()
    sys.exit(0)
    
################################################################################

print("\nHello World!\n")

#list_all_serial_devices(True)
device,vid_pid=find_serial_device(DEVICE_ID,0) 
print('\tdevice=',device,'\tvid_pid=',vid_pid)

ser = serial.Serial(device,BAUD,timeout=1)  #,
#xonxoff=False,dsrdtr=False,rtscts=False)
print('\tser=',ser,'\n')
time.sleep(5)

read_text(ser)

# Probe ESP32 to see what state it is in
"""
send_command('1+2')
txt=read_text(ser)
if ">>>" in txt:
    send_command('import yeti_client')
txt=read_text(ser)

#sys.exit(0)
"""

# Loop to process user commands
while True:

    try:
        cmd=input('\nEnter command to send to ESP32: ')
    except:
        quit(ser)
        
    print('cmd=',cmd)
    if cmd.upper() in ['EXIT','QUIT']:
        quit(ser)
    else:
        send_command(cmd)

    txt=''
    cnt=0
    while '<EOR>' not in txt:
        #line=ser.readline()
        #line=ser.read_until()
        #txt+=line.decode()
        txt=read_text(ser)
        print('txt=',txt)
        cnt+=1
        if cnt>5:
            print('No response')
            break
        else:
            time.sleep(1)
    #print('txt=',txt)

    if cmd.upper() in ['SYSINFO','STATE']:
        try:
            b=txt.split('data=')[1].split('<EOR>')[0].strip()
            #print('b=',b,type(b))
            data=eval(b)
            print('\ndata=',data,'\n')
            #print('data=',json.dumps(data,indent=4))
        except:
            print('Unable to decode response')
        

ser.close()


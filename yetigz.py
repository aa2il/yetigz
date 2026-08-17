#!/usr/bin/env -S uv run --script
#
################################################################################
#
# yetigz.py - Rev 1.0
# Copyright (C) 2026 by Joseph B. Attili, joe DOT aa2il AT gmail DOT com
#
# Control and Monitoring GUI for Yeti GoalZero Battery.
# I had a lot of trouble getting goalzero library to work and its probably
# overkill.  It turns out it is very simple to use requests for this thing.
#
# NOTE - THIS PROGRAM WAS A STEPPING STONE AND IS NO LONGER USED OR MAINTAINED!
#        USE solar_mon.py INSTEAD
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

from gzio import *
import sys
import time
from datetime import timedelta,datetime,timezone
import functools

from widgets_qt import QTLIB
exec('from '+QTLIB+'.QtWidgets import QMainWindow,QWidget,QGridLayout,QPushButton,QLabel,QApplication,QComboBox')
exec('from '+QTLIB+'.QtCore import Qt,QTimer')

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import math

###############################################################################

YETI_ADDR='10.1.1.1'

###############################################################################

class theCanvas(FigureCanvas):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig   = Figure(figsize=(width, height), dpi=dpi)
        self.axes  = self.fig.add_subplot(111)
        self.axes2 = self.axes.twinx()
        super().__init__(self.fig)

        self.lines = None
        self.xdata = []
        self.ydata = []

    def stuffData(self,xdata,ydata):
        self.xdata = xdata
        self.ydata = ydata

    def updatePlots(self,xdata,ydata,dt):

        if xdata==None:
            return
        if self.xdata==None or len(self.xdata)==0:
            self.xdata = [xdata]
            if self.ydata==None:
                self.ydata = []
            for i in range(len(ydata)):
                self.ydata.append([ydata[i]])
        else:            
            self.xdata.append(xdata)
            for i in range(len(ydata)):
                self.ydata[i].append(ydata[i])
        #self.xmin=min(self.xdata)
        self.xmax=max(self.xdata)
        self.xmin=max( min(self.xdata) , self.xmax-timedelta(hours=dt) )

        if self.lines==None:
            line,=self.axes.plot(xdata, ydata[0], 'r',label='Power In')
            self.lines=[line]
            line,=self.axes.plot(xdata, ydata[1], 'b',label='Power Out')
            self.lines.append(line)
            line,=self.axes2.plot(xdata, ydata[2], 'g',label='% Charged')
            self.lines.append(line)
            line,=self.axes2.plot(xdata, ydata[3], 'k',label='Temperature')
            self.lines.append(line)
            
            self.fig.autofmt_xdate()
            self.axes.legend(loc='upper left')
            self.axes2.legend(loc='upper right')
        else:
            for i in range(len(self.lines)):
                self.lines[i].set_xdata(self.xdata)
                self.lines[i].set_ydata(self.ydata[i])

        # Axes control
        self.axes.set(xlim=(self.xmin,self.xmax),xlabel='Time Stamp',
                      ylim=(0,100.5),ylabel='Power (W)')
        self.axes2.set(xlim=(self.xmin,self.xmax),xlabel='Time Stamp',
                       ylim=(0,100.5),ylabel='Percent Charge (%), Temp (deg C)')
        
###############################################################################

class MainWindow(QMainWindow):

    def __init__(self,ADDR):
        super().__init__()

        #self.FirstTime=True
        self.state   = None
        
        # Open connection to yeti
        #self.yeti    = YetiGZ(ADDR)          # Poll Yeti GZ directly via wifi
        #self.yeti    = Yeti_ESP32(ADDR)     # Poll Yeti GZ directly via ESP32 interface
        self.yeti    = Renogy_ESP32()       # Poll YRenogy Wanderer via ESP32 interface
        self.state   = self.yeti.state
        self.sysinfo = self.yeti.sysinfo

        # Open log file - read in past telemtry
        [xdata,ydata]=self.parse_log_file(self.yeti.fname)
        self.fp = open(self.yeti.fname,'a+')

        if 0:
            # Put log file on a diet
            fname2='gz2.dat'
            self.fp2 = open(fname2,'w')
            print(len(xdata),len(ydata))
            Pin=ydata[0]
            Pout=ydata[1]
            Pct=ydata[2]
            temp=ydata[3]
            charging=ydata[4]
            for i in range(len(xdata)):
                t=xdata[i]
                self.fp2.write('%s,%3.1f,%3.1f,%i,%3.0f,%i\n' % \
                              (t,Pin[i],Pout[i],Pct[i],temp[i],charging[i]))
            self.fp2.close()

        # Get basic info
        ntries=0
        while ntries<20:
            ntries+=1
            self.sysinfo=self.yeti.get_sysinfo()
            if self.sysinfo:
                break
            time.sleep(10)
        else:
            print('Unable to read Yeti sys info - giving up :-(')
            sys.exit(0)
        #print(self.sysinfo.keys())
        #print('model=',self.sysinfo['model'])

        # Create main window
        self.win  = QWidget()
        self.setCentralWidget(self.win)
        self.setWindowTitle('Yeti GoalZero Monitor')

        # Use a grid layout
        self.grid = QGridLayout(self.win)
        nrows=6
        ncols=5
        for row in range(nrows):
            self.grid.setRowStretch(row,0)
        for col in range(ncols):
            self.grid.setColumnStretch(col,1)

        # Put up info boxes & control buttons
        row = 0
        col = 0
        lab = QLabel('Model:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)
        self.grid.setRowStretch(row,1)

        col+=1
        self.Model = QLabel(self.sysinfo['model'])
        self.Model.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Model,row,col,1,1)

        col+=1
        lab = QLabel('Power In:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)

        col+=1
        self.Pin = QLabel() 
        self.Pin.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Pin,row,col,1,1)

        col+=1
        self.Btn12V = QPushButton('12 Volt Ports')
        self.grid.addWidget(self.Btn12V,row,col,1,1)
        self.Btn12V.setToolTip('Click to turn 12V Ports on/off')
        self.Btn12V.clicked.connect( functools.partial( self.ToggleButton,button=self.Btn12V,iopt=1 ))
        self.Btn12V.setCheckable(True)
        
        row+=1
        col = 0
        lab = QLabel('Battery Voltage:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)

        col+=1
        self.Voltage = QLabel() 
        self.Voltage.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Voltage,row,col,1,1)

        col+=1
        lab = QLabel('Power Out:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)

        col+=1
        self.Pout = QLabel()  
        self.Pout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Pout,row,col,1,1)

        col+=1
        self.BtnUSB = QPushButton('USB Ports')
        self.grid.addWidget(self.BtnUSB,row,col,1,1)
        self.BtnUSB.setToolTip('Click to turn USB Ports on/off')
        self.BtnUSB.clicked.connect( functools.partial( self.ToggleButton,button=self.BtnUSB,iopt=1 ))
        self.BtnUSB.setCheckable(True)
        
        row+=1
        col = 0
        lab = QLabel('Charge:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)
        col+=1
        self.Charge = QLabel()   
        self.Charge.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Charge,row,col,1,1)

        col+=1
        lab = QLabel('Charging:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)
        
        col+=1
        self.Charging = QLabel() 
        self.Charging.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Charging,row,col,1,1)

        col+=1
        self.BtnAC = QPushButton('AC Ports')
        self.grid.addWidget(self.BtnAC,row,col,1,1)
        self.BtnAC.setToolTip('Click to turn AC Ports on/off')
        self.BtnAC.clicked.connect( functools.partial( self.ToggleButton,button=self.BtnAC,iopt=1 ))
        self.BtnAC.setCheckable(True)
        
        row+=1
        col = 0
        lab = QLabel('Temperature:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)
        
        col+=1
        self.Temp = QLabel() # txt)
        self.Temp.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Temp,row,col,1,1)

        col+=1
        self.WHin = QLabel() # txt)
        self.WHin.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.WHin,row,col,1,1)

        col+=1
        self.WHout = QLabel() # txt)
        self.WHout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.WHout,row,col,1,1)

        col+=1
        if 0:
            self.BtnTime = QPushButton('All Time')
            self.grid.addWidget(self.BtnTime,row,col,1,1)
            self.BtnTime.setToolTip('Select Time Period for Graph')
            self.BtnTime.clicked.connect( self.ToggleTimePeriod )
            self.time_delta=99999
        else:
            self.Durations=['24 Hours','48 Hours','1 Week','All Time']
            self.TimeDeltas=[24*1,24*2,24*7,24*365]
            self.TimeBox = QComboBox()
            self.TimeBox.addItems(self.Durations)
            self.grid.addWidget(self.TimeBox,row,col,1,1)
            self.TimeBox.setToolTip('Select Time Period for Graph')
            self.TimeBox.currentIndexChanged.connect(self.TimePeriodSelect )
            self.TimeBox.setCurrentIndex(0)
            self.time_delta=self.TimeDeltas[0]
        
        # Create canvas to hold the plot
        row+=1
        col=0
        self.canvas = theCanvas(self, width=5, height=4)
        self.grid.addWidget(self.canvas,row,col,1,ncols)
        self.grid.setRowStretch(row,1)

        # Create toolbar, passing canvas as first parament, parent (self, the MainWindow) as second.
        row += 1
        toolbar = NavigationToolbar(self.canvas, self)
        self.grid.addWidget(toolbar,row,col,1,ncols)

        # Create initial data arrays & plot data
        self.canvas.stuffData(xdata,ydata)
        self.update_plot()

        # Ready to roll!
        self.show()

        # Setup a timer to trigger the redraw by calling update_plot every n secconds
        self.timer = QTimer()
        self.timer.setInterval(1000*15)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

    # Function to select time period for graph
    def TimePeriodSelect(self,i):
        txt=self.Durations[i]    #.split(" ")
        self.time_delta=self.TimeDeltas[i]
        print('TIME PERIOD SELECT: i=',i,
              '\ttxt=',txt,
              '\tTime Delta=',self.time_delta)
        self.update_plot(QUERY=False)
        
        
    # Function to toggle button statte
    def ToggleTimePeriod(self):
        # Decode which button we're working with
        txt=self.BtnTime.text()
        
        if txt=='All Time':
            self.BtnTime.setText('24 Hours')
            self.time_delta=24*1
        elif txt=='24 Hours':
            self.BtnTime.setText('48 Hours')
            self.time_delta=24*2
        elif txt=='48 Hours':
            self.BtnTime.setText('1 Week')
            self.time_delta=24*7
        else:
            self.BtnTime.setText('All Time')
            self.time_delta=24*365

        self.update_plot(QUERY=False)
        
            
    # Function to toggle button statte
    def ToggleButton(self,button=None,iopt=0):

        # Decode which button we're working with
        txt=button.text()
        #print('Toggle Button: txt=',txt,'\tiopt=',iopt)

        if txt==self.Btn12V.text():
            key='v12PortStatus'
        elif txt==self.BtnUSB.text():
            key='usbPortStatus'
        elif txt==self.BtnAC.text():
            key='acPortStatus'
        else:
            return

        # Get current state of gz for this button
        status=self.state[key]
        #print('\tkey=',key,'status=',status)

        # Toggle the button
        if iopt==1:
            # Toggle the button
            status=1-status
            self.state=self.yeti.set_state(key,status)
            self.update_plot(QUERY=False)

        # Color button depending on state
        if status==1:
            button.setStyleSheet('QPushButton { \
            background-color: red; \
            border :1px inset ; \
            border-radius: 5px; \
            border-color: gray; \
            font: bold 14px; \
            padding: 4px; \
            }')
        else:
            button.setStyleSheet('QPushButton { \
            background-color: limegreen; \
            border :1px outset ; \
            border-radius: 5px; \
            border-color: gray; \
            font: bold 14px; \
            padding: 4px; \
            }')

    def compute_energy(self,xdata,ydata,dhours):
        
        if xdata==None:
            return 0,0
        else:
            t=xdata
            Pin=ydata[0]
            Pout=ydata[1]

        Ein=0
        Eout=0
        t0=t[-1] - timedelta(hours=dhours)

        Pin1=0
        Pout1=0
        t1=t[0]
        t2=t[0]
        for i in range(1,len(t)):
            if t[i]>=t0:
                if not math.isnan(Pin[i]):
                    dt    = (t[i]-t1).total_seconds()
                    Ein  += dt*(Pin[i]+Pin1)/2
                    t1=t[i]
                    Pin1=Pin[i]
                if not math.isnan(Pout[i]):
                    dt    = (t[i]-t2).total_seconds()
                    Eout += dt*(Pout[i]+Pout1)/2
                    t2=t[i]
                    Pout1=Pout[i]
            else:
                t1=t[i]
                t2=t[i]

        """
        # Faster but doesn't handle nan's
        i0 =bisect.bisect(t, t0)
        for i in range(i0,len(t)):
            dt    = (t[i]-t[i-1]).total_seconds()
            Ein  += dt*(Pin[i]+Pin[i-1])/2
            Eout += dt*(Pout[i]+Pout[i-1])/2
        """
        Ein /=3600.
        Eout /=3600.

        return round(Ein),round(Eout)

            
    # Routine to update plot with latest data
    def update_plot(self,QUERY=True):

        # Query the yeti gz
        now=datetime.now()
        if QUERY:
            self.state=self.yeti.get_state()
        if not self.state:
            print('Unable to read Yeti state - Try again ... :-(')
            self.fp.write('%s Unable to read Yeti State\n' % \
                          (now.strftime('%Y-%m-%d %H:%M:%S')))
            self.fp.flush()
            return

        # Extract values of interest and update gui text boxes
        PWRin   = self.state['wattsIn']
        PWRout  = self.state['wattsOut']
        Pct     = self.state['socPercent']
        #print('PWR in=',PWRin,'W\tPWR out=',PWRout,'W\tCharge %=',Pct,'%')

        self.Pin.setText(str(PWRin)+' W')
        self.Pout.setText(str(PWRout)+' W')
        self.Voltage.setText(str(self.state['volts'])+' V')
        self.Charge.setText(str(self.state['socPercent'])+' %')

        # There can be hiccups in the temperature read
        deg_c=self.state['temperature']
        if deg_c>50 or deg_c==0.0:
            deg_c=float('nan')
        else:
            deg_f=round(9.*deg_c/5.+32.)
            txt=str(deg_f)+' F / '+str(deg_c)+' C'
            self.Temp.setText(txt)

        if self.state['isCharging']:
            txt='Yes'
        else:
            txt='No'
        self.Charging.setText(txt)

        Ein,Eout=self.compute_energy(self.canvas.xdata,
                                     self.canvas.ydata,
                                     self.time_delta)
        #print(Ein,Eout)
        txt=str(Ein)+' Wh in'
        self.WHin.setText(txt)
        txt=str(Eout)+' Wh out'
        self.WHout.setText(txt)

        # The time stamp is nonsense - circa 1970!
        if 0:
            ts=self.state['timestamp']
            ts2 = datetime.fromtimestamp(ts,tz=timezone.utc)
            print('ts=',ts,'\tts2=',ts2)
            print('now=',now,'\t=',now.timestamp())
            #self.yeti.set_state('timestamp',int(now.timestamp()))   # Doesnt work

        self.ToggleButton(button=self.Btn12V,iopt=0)
        self.ToggleButton(button=self.BtnUSB,iopt=0)
        self.ToggleButton(button=self.BtnAC,iopt=0)
                           
        # Save data to log file
        self.fp.write('%s,%3.1f,%3.1f,%i,%.0f,%i\n' % \
                      (now.strftime('%Y-%m-%d %H:%M:%S'),
                       PWRin,PWRout,
                       Pct,deg_c,
                       self.state['isCharging'] ))
        self.fp.flush()

        # Plot the latest and greatest readings and redraw the canvas
        self.canvas.updatePlots(now,[PWRin,PWRout,Pct,deg_c],self.time_delta)
        self.canvas.draw()

    # Function to parse old log file so we can plot all available data
    def parse_log_file(self,fname):

        try:
            fp = open(fname,'r')
        except:
            return None,None
            
        nfaults=0

        timestamp=[]
        PWRin=[]
        PWRout=[]
        Pct=[]
        temp=[]
        charging=[]
        
        for line in fp:
            #print("Line{}: {}".format(count, line.strip()))

            if 'Unable' in line:
                print(line)
                nfaults += 1
                continue
            elif 'thingName' in line:
                b=line.split('}')
                state=eval(b[0]+'}')
                continue
            else:
                a=line.split(',')
                #print(a)
                
                dt = datetime.strptime( a[0],'%Y-%m-%d %H:%M:%S')
                timestamp.append(dt)

                p1=float(a[1])
                if p1>100:
                    p1=float('nan')
                    nfaults += 1
                    print(line)
                PWRin.append(p1)

                p2=float(a[2])
                if p2>100 or p2==0.0:
                    p2=float('nan')
                    nfaults += 1
                    print(line)
                PWRout.append(p2)
                
                Pct.append(int(float(a[3])))

                t=float(a[4])
                if t>50 or t==0.0:
                    t=float('nan')
                    nfaults += 1
                    print(line)
                temp.append(t)
                
                charging.append(int(a[5]))

        fp.close()
        print('nfaults=',nfaults)

        return timestamp,[PWRin,PWRout,Pct,temp,charging]
    

###############################################################################
        
# Let the beatings begin!
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow(YETI_ADDR)
    app.exec()


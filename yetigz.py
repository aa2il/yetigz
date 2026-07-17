#!/usr/bin/env -S uv run --script

###############################################################################

# Simple test program showing how to talk to Yeti Goal Zero using Requests.
# I had a lot of trouble getting goalzero library to work and its probably
# overkill.  It turns out it is very simple to use requests for this thing.

###############################################################################

from gzio import YetiGZ
import sys
import time
from datetime import datetime
import functools
import json

from widgets_qt import QTLIB
exec('from '+QTLIB+'.QtWidgets import QMainWindow,QWidget,QGridLayout,QPushButton,QLabel,QApplication')
exec('from '+QTLIB+'.QtCore import Qt,QTimer')

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

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

    def updatePlots(self,xdata,ydata):

        if len(self.xdata)==0:
            self.xdata = [xdata]
            for i in range(len(ydata)):
                self.ydata.append([ydata[i]])
        else:            
            self.xdata.append(xdata)
            for i in range(len(ydata)):
                self.ydata[i].append(ydata[i])
        #self.xmin=min(self.xmin,xdata)
        #self.xmax=max(self.xmin,xdata)
        self.xmin=min(self.xdata)
        self.xmax=max(self.xdata)

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
                      ylim=(0,100),ylabel='Power (W)')
        self.axes2.set(xlim=(self.xmin,self.xmax),xlabel='Time Stamp',
                       ylim=(0,100),ylabel='Percent Charge (%), Temp (deg C)')
        
class MainWindow(QMainWindow):

    def __init__(self,ADDR):
        super().__init__()

        self.FirstTime=True
        
        # Open connection to yeti
        self.yeti = YetiGZ(ADDR)

        # Open log file
        fname='gz.dat'
        [xdata,ydata]=self.parse_log_file(fname)
        #sys.exit(0)
        
        #self.fp = open(fname,'w')
        self.fp = open(fname,'a+')

        # Get basic info
        ntries=0
        self.sysinfo = None
        while ntries<20:
            ntries+=1
            self.sysinfo = self.yeti.get_sysinfo()
            if self.sysinfo:
                break
            time.sleep(10)
        else:
            print('Unable to read Yeti sys info - giving up :-(')
            sys.exit(0)
        print(self.sysinfo.keys())
        print('model=',self.sysinfo['model'])

        # Get sys state
        #self.state=self.yeti.get_state()
        
        # Create main window
        self.win  = QWidget()
        self.setCentralWidget(self.win)
        self.setWindowTitle('Embedded Plotting Demo')

        # Use a grid layout
        self.grid = QGridLayout(self.win)
        nrows=6
        ncols=5
        self.grid.setRowStretch(nrows,ncols)

        # Put up info boxes & control buttons
        row = 0
        col = 0
        lab = QLabel('Model:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)
        self.grid.setColumnStretch(col,1)

        col+=1
        self.Model = QLabel(self.sysinfo['model'])
        self.Model.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Model,row,col,1,1)
        self.grid.setColumnStretch(col,1)

        col+=1
        lab = QLabel('Power In:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)
        self.grid.setColumnStretch(col,1)

        col+=1
        self.Pin = QLabel()   # str(self.state['wattsIn'])+' W')
        self.Pin.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Pin,row,col,1,1)
        self.grid.setColumnStretch(col,1)

        col+=1
        self.Btn12V = QPushButton('12 Volt Ports')
        self.grid.addWidget(self.Btn12V,row,col,1,1)
        self.Btn12V.setToolTip('Click to turn 12V Ports on/off')
        self.Btn12V.clicked.connect( functools.partial( self.ToggleButton,button=self.Btn12V,iopt=1 ))
        self.Btn12V.setCheckable(True)
        #self.ToggleButton(button=self.Btn12V,iopt=0)
        self.grid.setColumnStretch(col,1)
        
        row+=1
        col = 0
        lab = QLabel('Battery Voltage:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)
        self.grid.setColumnStretch(col,1)

        col+=1
        self.Voltage = QLabel()   # str(self.state['volts'])+' V')
        self.Voltage.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Voltage,row,col,1,1)
        self.grid.setColumnStretch(col,1)

        col+=1
        lab = QLabel('Power Out:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)
        self.grid.setColumnStretch(col,1)

        col+=1
        self.Pout = QLabel()     #str(self.state['wattsOut'])+' W')
        self.Pout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Pout,row,col,1,1)
        self.grid.setColumnStretch(col,1)

        col+=1
        self.BtnUSB = QPushButton('USB Ports')
        self.grid.addWidget(self.BtnUSB,row,col,1,1)
        self.BtnUSB.setToolTip('Click to turn USB Ports on/off')
        self.BtnUSB.clicked.connect( functools.partial( self.ToggleButton,button=self.BtnUSB,iopt=1 ))
        self.BtnUSB.setCheckable(True)
        #self.ToggleButton(button=self.BtnUSB,iopt=0)
        self.grid.setColumnStretch(col,1)
        
        row+=1
        col = 0
        lab = QLabel('Charge:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)
        col+=1
        self.Charge = QLabel()    # str(self.state['socPercent'])+' %')
        self.Charge.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Charge,row,col,1,1)
        self.grid.setColumnStretch(col,1)

        col+=1
        lab = QLabel('Charging:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)
        self.grid.setColumnStretch(col,1)
        
        col+=1
        #if self.state['isCharging']:
        #    txt='Yes'
        #else:
        #    txt='No'
        self.Charging = QLabel()   #txt)
        self.Charging.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Charging,row,col,1,1)
        self.grid.setColumnStretch(col,1)

        col+=1
        self.BtnAC = QPushButton('AC Ports')
        self.grid.addWidget(self.BtnAC,row,col,1,1)
        self.BtnAC.setToolTip('Click to turn AC Ports on/off')
        self.BtnAC.clicked.connect( functools.partial( self.ToggleButton,button=self.BtnAC,iopt=1 ))
        self.BtnAC.setCheckable(True)
        #self.ToggleButton(button=self.BtnAC,iopt=0)
        self.grid.setColumnStretch(col,1)
        
        row+=1
        col = 0
        lab = QLabel('Temperature:')
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(lab,row,col,1,1)
        self.grid.setColumnStretch(col,1)
        
        col+=1
        #deg_c=self.state['temperature']
        #deg_f=round(9.*deg_c/5.+32.)
        #txt=str(deg_f)+' F / '+str(deg_c)+' C'
        self.Temp = QLabel() # txt)
        self.Temp.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.grid.addWidget(self.Temp,row,col,1,1)
        self.grid.setColumnStretch(col,1)

        # Create canvas to hold the plot
        row+=1
        col=0
        self.canvas = theCanvas(self, width=5, height=4, dpi=100)
        self.grid.addWidget(self.canvas,row,col,1,ncols)
        #self.grid.setColumnStretch(col,1)

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
        self.timer.setInterval(1000*5)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

    # Function to toggle button statte
    def ToggleButton(self,button=None,iopt=0):

        # Decode which button we're working with
        txt=button.text()
        print('Toggle Button: txt=',txt,'\tiopt=',iopt)

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
            self.yeti.set_state(key,status)

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

    # Routine to update plot with latest data
    def update_plot(self):

        # Query the yeti gz
        now=datetime.now()
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
        print('PWR in=',PWRin,'W\tPWR out=',PWRout,'W\tCharge %=',Pct,'%')

        self.Pin.setText(str(PWRin)+' W')
        self.Pout.setText(str(PWRout)+' W')
        self.Voltage.setText(str(self.state['volts'])+' V')
        self.Charge.setText(str(self.state['socPercent'])+' %')

        deg_c=self.state['temperature']
        deg_f=round(9.*deg_c/5.+32.)
        txt=str(deg_f)+' F / '+str(deg_c)+' C'
        self.Temp.setText(txt)

        if self.state['isCharging']:
            txt='Yes'
        else:
            txt='No'
        self.Charging.setText(txt)

        self.ToggleButton(button=self.Btn12V,iopt=0)
        self.ToggleButton(button=self.BtnUSB,iopt=0)
        self.ToggleButton(button=self.BtnAC,iopt=0)
                           
        # Save data to log file
        #self.fp.write(str(self.state+'\n'))
        self.fp.write('%s,%f,%f,%f,%f,%i\n' % \
                      (now.strftime('%Y-%m-%d %H:%M:%S'),
                       PWRin,PWRout,Pct,deg_c,self.state['isCharging']))
        self.fp.flush()

        # Plot the latest and greatest readings and redraw the canvas
        self.canvas.updatePlots(now,[PWRin,PWRout,Pct,deg_c])
        self.canvas.draw()


    def parse_log_file(self,fname):

        fp = open(fname,'r')
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

        return timestamp,[PWRin,PWRout,Pct,temp]
    

###############################################################################
        
# Let the beatings begin!
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow(YETI_ADDR)
    app.exec()


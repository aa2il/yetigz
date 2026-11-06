#!/usr/bin/env -S uv run --script

# AISlop demo showing how to update a matplotlib canvas
# in a qt app and not block the gui.   

import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import QTimer

# Import the correct canvas backend for Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class LivePlotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Matplotlib Canvas Refresh Example")
        
        # 1. Create a central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 2. Setup Matplotlib Figure and Canvas
        self.fig = Figure(figsize=(5, 4))
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        layout.addWidget(self.canvas)
        
        # Initialize an empty line plot object
        xmax=10            # was 10
        npts=24*60*2           # was 100
        self.x_data = np.linspace(0, xmax, npts)
        self.y_data = np.sin(self.x_data)
        self.line, = self.ax.plot(self.x_data, self.y_data, 'r-')
        
        # 3. Add a trigger button
        self.btn = QPushButton("Randomize Data")
        self.btn.clicked.connect(self.update_plot)
        layout.addWidget(self.btn)
        
        # Optional: Auto-refresh every 100ms using a Qt Timer
        if 1:
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_plot)
            self.timer.start(100)

    def update_plot(self):
        """Callback to refresh data and redraw the canvas"""
        # Generate new data shifts
        shift = np.random.uniform(0, 2 * np.pi)
        new_y = np.sin(self.x_data + shift)

        self.xmin=0
        self.xmax=10
        self.ymin=1.1
        self.ymax=-1.1
        self.ax.set(xlim=(self.xmin,self.xmax),xlabel='Time',
                          ylim=(self.ymin,self.ymax),ylabel='Amplitude')
        
        # Update line data (Efficient approach)
        self.line.set_ydata(new_y)
        
        # Trigger the canvas refresh
        self.canvas.draw_idle()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LivePlotWindow()
    window.show()
    sys.exit(app.exec())

#!/usr/bin/env -S uv run --script

# AISlop demo showing how to properly incorporate slow http requests 
# into a qt app and not block the gui.
# Currently, I'm using a regular thread but this example if interesting bx
# it also shows how to handle errors and pass back data.

import sys
import requests
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QPushButton, QTextEdit, QVBoxLayout, QWidget


# 1. Define a Worker that handles the blocking 'requests' call
class NetworkWorker(QObject):
    finished = pyqtSignal(dict)  # Signal to pass data back safely
    error = pyqtSignal(str)

    def run(self):
        try:
            # This is blocking, but it's fine because it runs on a background thread
            #response = requests.get("https://httpbin.org")
      
            # Define the target URL and query parameters
            url = "https://httpbin.org/get"
            query_params = {
                "name": "Alice",
                "status": "active"
            }

            # Send the GET request
            response = requests.get(url, params=query_params)
            self.finished.emit(response.json())

            # Print request info
            print("Constructed URL:", response.url) 
            print("Status Code:", response.status_code)
            json_data = response.json()
            print("\nJSON Response:")
            print(json_data)
            
        except Exception as e:
            self.error.emit(str(e))

class ThreadedNetworkApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 + Threaded Requests Example")
        self.resize(400, 300)

        self.button = QPushButton("Fetch Data (QThread + Requests)", self)
        self.log_window = QTextEdit(self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.button)
        layout.addWidget(self.log_window)

        self.button.clicked.connect(self.start_network_thread)

    def start_network_thread(self):
        self.button.setEnabled(False)
        self.log_window.setText("Starting thread...")

        # 2. Set up the Thread and Worker
        self.thread = QThread()
        self.worker = NetworkWorker()
        self.worker.moveToThread(self.thread)

        # 3. Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.handle_success)
        self.worker.error.connect(self.handle_error)
        
        # Ensure cleanup happens when finished
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # 4. Start the thread
        self.thread.start()

    def handle_success(self, data):
        self.log_window.append(f"\nSuccess! Data fetched from: {data.get('url')}")
        self.button.setEnabled(True)

    def handle_error(self, err_msg):
        self.log_window.append(f"\nRequest failed: {err_msg}")
        self.button.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ThreadedNetworkApp()
    window.show()
    sys.exit(app.exec())

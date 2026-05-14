#!/usr/bin/env python3
import sys
from PyQt6.QtWidgets import QApplication
from ui_main import MainWindowUI
from ui_controller import MainWindowController

class MainWindow:
    def __init__(self):
        self.ui = MainWindowUI()
        self.window = None
    
    def run(self):
        app = QApplication(sys.argv)
        self.window = __import__('PyQt6.QtWidgets').QtWidgets.QMainWindow()
        self.ui.setup_ui(self.window)
        self.controller = MainWindowController(self.ui)
        self.window.show()
        sys.exit(app.exec())

if __name__ == "__main__":
    main_window = MainWindow()
    main_window.run()
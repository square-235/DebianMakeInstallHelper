from PyQt6.QtCore import QObject, pyqtSignal

class StreamSignals(QObject):
    output = pyqtSignal(str)
    finished = pyqtSignal(bool)
from PyQt5 import Qt

class TerribleEvalThreadManager(Qt.QObject):
    _evalSignal = Qt.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = TerribleEvalThreadWorker()
        self.thread = Qt.QThread(self)
        self.thread.finished.connect(self.thread.deleteLater, Qt.Qt.QueuedConnection)
        self.thread.start()
        self.worker.moveToThread(self.thread)
        self._evalSignal.connect(self.worker.evalSlot, Qt.Qt.QueuedConnection)

    def __del__(self):
        self.thread.quit()
        self.thread.wait()

    def terrify(self, evalStr):
        self._evalSignal.emit(evalStr)

class TerribleEvalThreadWorker(Qt.QObject):
    def __init__(self):
        super().__init__(None)

    def evalSlot(self, evalStr):
        exec(evalStr, {'self':self})

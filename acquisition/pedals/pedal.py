import serial
from PyQt5 import Qt

class WaitPedal(object):
    modes = {'high': b'H', 'low': b'L', 'change': b'C'}
    
    def __init__(self, port):
        self.ser = serial.Serial(port)
    
    def wait(self, mode="low"):
        """valid modes are 'high', 'low', or 'change'."""
        self.ser.write(b'w'+self.modes[mode]+b'\n')
        try:
            while self.ser.inWaiting() < 5:
                eventLoop = Qt.QEventLoop()
                timer = Qt.QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(eventLoop.quit)
                timer.start(10)
                eventLoop.exec_()
            self.ser.read(5) # read out 'done\n'
        except KeyboardInterrupt:
            self.reset()

    def reset(self):
        self.ser.write(b'r\n');
        self.ser.read(6) # read out 'reset\n'

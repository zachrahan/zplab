# The MIT License (MIT)
#
# Copyright (c) 2014 WUSTL ZPLAB
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Authors: Erik Hvatum

import enum
import re
from PyQt5 import QtCore, QtSerialPort
from acquisition.device import Device
from acquisition.device import DeviceException, DeviceTimeoutException

class Pedals(Device):
    pedalUpChanged = QtCore.pyqtSignal(int, bool)

    def __init__(self, parent=None, deviceName='Multiple Pedal Controller', serialPortDescriptor='/dev/ttyPedals'):
        super().__init__(parent)
        self._serialPort = QtSerialPort.QSerialPort(serialPortDescriptor)

        if not self._serialPort.open(QtSerialPort.QSerialPort.ReadWrite):
            raise DeviceException(self, 'Failed to open {}.'.format(serialPortDescriptor))

        if not self._serialPort.setBaudRate(QtSerialPort.QSerialPort.Baud115200):
            raise DeviceException(self, 'Failed to set serial port {} to 115200 baud.'.format(serialPortDescriptor))

        self._inBuffer = ''

        self._serialPort.error.connect(self._serialPortErrorSlot)
        self._serialPort.readyRead.connect(self._serialPortBytesReadySlot)

    def _serialPortErrorSlot(self, serialPortError):
        self._warn('Serial port error #{} ({}).'.format(serialPortError, self._serialPort.errorString()))

    def _serialPortBytesReadySlot(self):
        inba = self._serialPort.readAll()
        # Note: Serial port errors are handled by serialPortErrorSlot which has already been called during execution of the readAll
        # in the line above if an error occurred.  If an exception was thrown by serialPortErrorSlot, it passes through the readAll
        # and causes this function to exit (notice readAll is not in a try block).  If an exception was not thrown but the serial port
        # remains in a bad state, whatever is in the serial port buffer is assumed to be junk and is ignored (the condition of the if
        # statement below evaluates to false and inba goes out of scope without being parsed).
        if self._serialPort.error() == QtSerialPort.QSerialPort.NoError:
            self._inBuffer += inba.data().decode('utf-8')
            # Parse and act upon packets read into self._inBuffer from the from-device serial stream until no complete messages remain
            # in the buffer.  Each iteration of the while True loop processes one message, except for the last iteration which
            # detects that no complete messages remain.
            while True:
                if self._inBuffer.startswith('//'):
                    eolLoc = self._inBuffer.find('\r\n')
                    if eolLoc < 0:
                        # Reached end of buffer without encountering a carriage return; the content of the buffer represents
                        # the beginning of an incomplete warning or error line
                        break
                    message = self._inBuffer[:eolLoc]
                    self._inBuffer = self._inBuffer[eolLoc + 2:]
                    self._warn('Error or warning from device: "{}"'.format(message))
                elif self._inBuffer.startswith('/*'):
                    eomLoc = self._inBuffer.find('*/\r\n')
                    if eomLoc < 0:
                        # The buffer contains the beginning of an incomplete multiline error or warning
                        break
                    message = self._inBuffer[:eomLoc].replace('\r\n', '\n')
                    self._inBuffer = self._inBuffer[eomLoc + 4:]
                    self._warn('Error or warning from device: "{}"'.format(message))
                else:
                    eolLoc = self._inBuffer.find('\r\n')
                    if eolLoc < 0:
                        # Reached end of buffer without encountering a carriage return; the content of the buffer represents
                        # the beginning of an incomplete machine parsable normal response
                        break
                    message = self._inBuffer[:eolLoc]
                    self._inBuffer = self._inBuffer[eolLoc + 2:]
                    match = re.match('pedal (\d+) state changed to (down|up)', message)
                    if match is not None:
                        self.pedalUpChanged.emit(int(match.group(1)), match.group(2) == 'up')

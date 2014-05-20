# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import re
import serial
import time
from acquisition.device import Device, DeviceException

class BrightfieldLed(Device):
    '''This class is the API for communicating with an Arduino device programmed with the accompanying adafruit_atmega32u4.pde C++
    source file.  All BrightfieldLed does is provide a convenient interface for switching on/off a single Arduino analog out pin and
    controlling its voltage (which should be passed through a hardware lowpass filter).  So, nothing about this class is actually
    specific to controlling of LED drivers, and it could be broken into a voltage controller interface class and a more general LED
    controller class capable of sitting atop it.

    Use this class's ok, enabled, and power properties to interact with the LED controller:

    from acquisition.brightfield_led.brightfield_led import BrightfieldLed
    bfl = BrightfieldLed()
    print("ok? {}  enabled? {}  power: {}".format(bfl.ok, bfl.enabled, bfl.power))
    bfl.enabled = True
    bfl.power = 255
    print("ok? {}  enabled? {}  power: {}".format(bfl.ok, bfl.enabled, bfl.power))'''
    _responseErrorRe = re.compile(r'Error: (.+)')
    _splitResponseRe = re.compile(r'(.+)(==|<-)(.+)')

    def __init__(self, serialPortDescriptor='/dev/ttyBflCntrlr', name='Brightfield LED Driver Controller'):
        super().__init__(name)
        self._appendTypeName('BrightfieldLed')
        self._serialPort = serial.Serial(serialPortDescriptor, 9600, timeout=0.1)
        self._lineTimeout = 1.0
        if not self._serialPort.isOpen():
            raise DeviceException(self, 'Failed to open {}.'.format(serialPortDescriptor))
        self._buffer = ''
        if not self.ok:
            raise DeviceException(self, 'Failed to communicate with device.'.format())
        self._readEnabled()
        self._readPower()

    def _splitResponse(self, response):
        match = re.match(BrightfieldLed._responseErrorRe, response)
        if match is not None:
            raise DeviceException(self, 'Device reported error: {}'.format(match.group(1)))
        match = re.match(BrightfieldLed._splitResponseRe, response)
        if match is None:
            raise DeviceException(self, 'Failed to parse reponse from device: "{}".'.format(response))
        return (match.group(1), match.group(2), match.group(3))

    def _readLine(self):
        '''Reads from self._serialPort until CRLF is encountered, returning the line read.  A little more complexity is actually involved
        to handle buffering of any data beyond the CRLF, which is prepended to the beginning of the next line read.'''
        startTime = time.time()
        while True:
            elapsed = time.time() - startTime
            if elapsed >= self._lineTimeout:
                raise DeviceException(self, "Read line timeout expired ({}s elapsed; {}s timeout).".format(elapsed, self._lineTimeout))
            available = self._serialPort.inWaiting()
            if available > 0:
                prevBufLen = len(self._buffer)
                inBuf = self._serialPort.read(available)
                inBufLen = len(inBuf)
                if inBufLen < available:
                    raise DeviceException(self, "Failed to read all available data from input buffer.  Perhaps another thread took data from " +
                                                "the input buffer between when we queried the available amount and when we attempted to read it.")
                self._buffer += inBuf.decode('utf-8')
                # Note: we search one back from start of new data as crlf my straddle the end of the previous read and the start of the
                # current one
                crlfLoc = self._buffer.find('\r\n', max(prevBufLen - 1, 0))
                if crlfLoc < 0:
                    # No crlf yet
                    pass
                else:
                    ret = self._buffer[0:crlfLoc]
                    self._buffer = self._buffer[crlfLoc + 2:]
                    return ret

    def _readResponse(self, expectedResponseName=None, expectedResponseNameValueDelimeter=None):
        response = self._readLine()
        rs = self._splitResponse(response)
        if expectedResponseName is not None and rs[0] != expectedResponseName:
            raise DeviceException(self, 'Received response with incorrect response name (expected "{}", got "{}").'.format(expectedResponseName, rs[0]))
        if expectedResponseNameValueDelimeter is not None and rs[1] != expectedResponseNameValueDelimeter:
            raise DeviceException(self, 'Received response with incorrect name/value delimeter (expected "{}", got "{}").'.format(expectedResponseNameValueDelimeter, rs[1]))
        return rs

    def _parseBool(self, text):
        if text == 'true':
            return True
        if text == 'false':
            return False
        raise DeviceException(self, 'Received reponse with incorrect value ("{}", must be either "true" or "false").'.format(rv))

    def _write(self, out):
        if type(out) is str:
            out = out.encode('utf-8')
#       print(out.decode('utf-8'))
        byteCountWritten = self._serialPort.write(out)
        byteCount = len(out)
        if byteCountWritten != byteCount:
            raise DeviceException(self, 'Attempted to write {} bytes to Lumencor serial port, but only {} bytes were written.'.format(byteCount, byteCountWritten))

    def _readEnabled(self):
        self._write('isOn\n')
        rn, rd, rv = self._readResponse('on', '==')
        self._enabled = self._parseBool(rv)

    def _readPower(self):
        self._write('getPower\n')
        rn, rd, rv = self._readResponse('power', '==')
        self._power = int(rv)

    def forceComprehensiveObserverNotification(self, observer):
        try:
            observer.notifyBrightfieldLedEnablementChanged(self, self._enabled)
        except AttributeError:
            pass

        try:
            observer.notifyBrightfieldLedPowerChanged(self, self._power)
        except AttributeError:
            pass

        super().forceComprehensiveObserverNotification(observer)

    @property
    def ok(self):
        try:
            self._write('isOk\n')
            rn, rd, rv = self._readResponse('ok', '==')
        except DeviceException as e:
            return False
        return rv == 'true'

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, enabled):
        if enabled != self._enabled:
            if enabled:
                text = 'true'
            else:
                text = 'false'
            self._write('on={}\n'.format(text))
            rn, rd, rv = self._readResponse('on', '<-')
            nowEnabled = self._parseBool(rv)
            if nowEnabled != enabled:
                if enabled:
                    wantTo = 'enable'
                else:
                    wantTo = 'disable'
                raise DeviceException(self, 'Failed to {}.'.format(wantTo))
            self._enabled = nowEnabled
            for observer in self._observers:
                try:
                    observer.notifyBrightfieldLedEnablementChanged(self, self._enabled)
                except AttributeError:
                    pass

    @property
    def power(self):
        return self._power

    @power.setter
    def power(self, power):
        if power != self._power:
            self._write('power={}\n'.format(power))
            rn, rd, rv = self._readResponse('power', '<-')
            self._power = int(rv)
            for observer in self._observers:
                try:
                    observer.notifyBrightfieldLedPowerChanged(self, self._power)
                except AttributeError:
                    pass
            if power != self._power:
                raise DeviceException(self, 'Power did not change to requested value (wanted {}, got {}).'.format(power, self._power))

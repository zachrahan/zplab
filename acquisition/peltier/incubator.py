import serial

class Incubator(object):
    def __init__(self, port):
        self.ser = serial.Serial(port, baudrate=2400, timeout=0.1)
        
    def _read(self):
        line = b""
        while True:
            c = self.ser.read(1)
            if not c: # on timeout, an empty value is returned
                raise RuntimeError('Connection to incubator timed out.')
            elif c == b'\r':
                return line.decode('ascii')
            line += c

    def _write(self, val):
        self.ser.write(val.encode('ascii') + b'\r')
    
    def _call_response(self, input):
        self._write(input)
        return self._read()
    
    def get_current_temp(self):
        return float(self._call_response('a'))

    def get_timer(self):
        """return (hours, minutes, seconds) tuple"""
        timer = self._call_response('b')
        return int(timer[:2]), int(timer[2:4]), int(timer[4:])
        
    def get_auto_off_mode(self):
        """return true if auto-off mode is on"""
        return self._call_response('c').endswith('On')

    def get_target_temp(self):
        """return target temp as a float or None if no target is set."""
        temp = self._call_response('d')
        if temp == 'no target set':
            return None
        return float(temp)

    def _call_param(self, input, param=''):
        self._write(input + param)
        if not self._read().endswith('OK'):
            raise RuntimeError('Invalid command to incubator.')
    
    def set_target_temp(self, temp):
        self._call_param('A', '{:.1f}'.format(temp))
    
    def set_timer(self, hours, minutes, seconds):
        assert hours <= 99 and minutes <= 99 and seconds <= 99
        self._call_param('B', '{:02d}{:02d}{:02d}'.format(hours, minutes, seconds))
    
    def set_auto_off_mode(self, mode):
        mode_str = "ON" if mode else "OFF"
        self._call_param('C', mode_str)
    
    def show_temp(self):
        self._call_param('D')

    def show_timer(self):
        self._call_param('E')
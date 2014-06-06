# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from acquisition.device import DeviceException

class Packet:
    def __init__(self, funit, line=None, funitCode=None, cmdCode=None, parameter=None):
        if line is not None:
            # Parse a received packet
            if funitCode is not None or cmdCode is not None or parameter is not None:
                raise ValueError('It does not make sense to provide both line and additional parameters (funitCode, cmdCode, and parameter are parsed from line).')
            if len(line) < 5:
                e = 'Reponse from device is only {} characters long.  The minimum conceivably valid response '
                e+= 'length is 5 (2 for function unit code, 3 for command code).'
                raise TruncatedResponseException(funit, e.format(len(line)))

            funitCode = line[:2]
            if not funitCode.isdigit():
                raise InvalidPacketReceivedException(funit, 'Response from device is invalid; function unit field contains non-digit characters.')
            self.funitCode = int(funitCode)

            if not line[2:5].isdigit():
                raise InvalidPacketReceivedException(funit, 'Response from device is invalid; command field contains non-digit characters.')

            # NB: only responses make use of a status code.  The status code for a request is always zero; in a response,
            # the status code indicates whether the scope successfully acted on the associated request.
            self.statusCode = int(line[2:3])

            self.cmdCode = int(line[3:5])

            self.parameter = line[5:]
            # Parameter is separated from funitCode and cmdCode by a space; throw that space away
            if len(self.parameter) > 0 and self.parameter[0] == ' ':
                self.parameter = self.parameter[1:]
        else:
            # Construct a packet to be transmitted
            if funitCode is None:
                self.funitCode = funit._funitCode
            else:
                self.funitCode = funitCode
            self.cmdCode = cmdCode
            self.parameter = parameter

    def __str__(self):
        '''Serialize packet to be transmitted.'''
        if self.funitCode < 0 or self.funitCode > 99:
            raise ValueError('funitCode must be in the range [0, 99].')
        if self.cmdCode < 0 or self.cmdCode > 99:
            raise ValueError('cmdCode must be in the range [0, 99].')
        ret = '{:02}{:03}'.format(self.funitCode, self.cmdCode)
        if self.parameter is not None:
            ret += ' '
            if type(self.parameter) is str:
                ret += self.parameter
            else:
                ret += str(self.parameter)
        ret += '\r'
        return ret
        
class InvalidPacketReceivedException(DeviceException):
    pass

class TruncatedPacketReceivedException(InvalidPacketReceivedException):
    pass

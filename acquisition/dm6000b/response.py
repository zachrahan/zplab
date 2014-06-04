# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from acquisition.device import DeviceException

class Response:
    def __init__(self, dm6000b, line):
        if len(line) < 5:
            e = 'Reponse from device is only {} characters long.  The minimum conceivably valid response '
            e+= 'length is 5 (2 for function unit code, 3 for command code).'
            raise TruncatedResponseException(dm6000b, e.format(len(line)))

        id = line[:2]
        if not id.isdigit():
            raise InvalidResponseException(dm6000b, 'Response from device is invalid; ID field contains non-digit characters.')
        self.id = int(id)

        command = line[2:5]
        if not command.isdigit():
            raise InvalidResponseException(dm6000b, 'Response from device is invalid; command field contains non-digit characters.')
        self.command = int(command)

        self.parameter = line[5:]
        
class InvalidResponseException(DeviceException):
    pass

class TruncatedResponseException(InvalidResponseException):
    pass

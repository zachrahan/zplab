# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore
from acquisition.device import DeviceException
from acquisition.dm6000b.subdevices.subdevice import Subdevice
from acquisition.dm6000b.response import Response, InvalidResponseException, TruncatedResponseException

class Stage(Subdevice):
    '''This Device represents a combined interface to three separate DM6000B "function units" (in Leica terminology).
    These are the Z-DRIVE (ID 71), X-AXIS (ID 72), Y-AXIS (ID 73).  This Device is meant to act as a subdevice of
    Dm6000b and, as such, depends on its parent to send requests to the DM6000B and to deliver responses from it.'''
    def __init__(self, dm6000b, deviceName='Stage'):
        super().__init__(dm6000b, deviceName, [71, 72, 73])

    def _responseReceivedSlot(self, response):
        print("got response, id: {}, command: {}, parameter: {}".format(response.id, response.command, response.parameter))

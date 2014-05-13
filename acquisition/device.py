# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from acquisition.acquisition_exception import AcquisitionException

class Device:
    def __init__(self, name=''):
        self._name = name
        self._typeName = 'Device'
        self._subDevices = []

    def _appendTypeName(self, typeName):
        self._typeName += '.' + typeName

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def fancyName(self):
        return '"{}"({})'.format(self.name, self.typeName)

    @property
    def typeName(self):
        return self._typeName

    @property
    def subDevices(self):
        return self._subDevices

    def _addSubDevice(self, subDevice):
        if subDevice in self.subDevices:
            raise DeviceException(self, '_addSubDevice(self, subDevice): {} is already a sub-device of {}.'.format(self.fancyName, subDevice.fancyName))

class DeviceException(AcquisitionException):
    def __init__(self, device, description):
        self.device = device
        self.description = description

    def __str__(self):
        return repr('{}: {}'.format(self.device.fancyName, self.description))

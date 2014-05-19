# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from acquisition.acquisition_exception import AcquisitionException

class Device:
    def __init__(self, name=''):
        self._name = name
        self._typeName = 'Device'
        self._subDevices = []
        self._observers = set()

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
        return self._subDevices.copy()

    def _addSubDevice(self, subDevice):
        if subDevice in self.subDevices:
            raise DeviceException(self, '_addSubDevice(self, subDevice): {} is already a sub-device of {}.'.format(self.fancyName, subDevice.fancyName))

    @property
    def observers(self):
        return self._observers.copy()

    def observerIsAttached(self, observer):
        return observer in self._observers

    def attachObserver(self, observer):
        if observer in self._observers:
            raise DeviceException(self, 'The specified Observer instance is already in this Device\'s set of Observers.')
        self._observers.add(observer)
        # The observer does not necessarily care to know if it was attached.  If we try to tell it that it was and it replies that we should go to heck,
        # we don't let that get us down.  We continue doing our thing, and we don't even hold a grudge against the observer, even if it was sort of a
        # jerk to us.  This is our general policy when proferring information to Observer instances and also to tetchy human teenager instances.
        try:
            observer.notifyAttached(self)
        except AttributeError as e:
            pass

    def detachObserver(self, observer):
        if observer not in self._observers:
            raise DeviceException(self, 'The specified Observer instance is not in this Device\'s set of Observers.')
        self._observers.remove(observer)

    # Useful to initialize a new observer's idea of a Device's state.  For example, a GUI with controls representing elements of a Device's state
    # that updates those controls upon receipt of observer notifications can cause the relevant updates to be sent (and thus the controls to update)
    # by calling forceComprehensiveObserverNotification(..).
    def forceComprehensiveObserverNotification(self, observer):
        for subDevice in self._subDevices:
            subDevice.forceComprehensiveObserverNotification(observer)

class DeviceException(AcquisitionException):
    def __init__(self, device, description):
        super().__init__(description)
        self.device = device

    def __str__(self):
        return repr('{}: {}'.format(self.device.fancyName, self.description))

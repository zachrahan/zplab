# Copyright 2014 WUSTL ZPLAB

import copy
import serial
import time
from acquisition.device import Device
from acquisition.lumencor.lumencor_exception import LumencorException

class Lumencor(Device):
    class LampState:
        def __init__(self, enabled, power, idx):
            self.enabled = enabled
            self.power = power
            self._idx = idx

        def __str__(self):
            return 'enabled={} power={}'.format(self._enabled, self._power)

        def __repr__(self):
            return 'Lumencor.LampState(enabled={}, power={}, idx={})'.format(self._enabled, self._power, self._idx)

        @property
        def enabled(self):
            return self._enabled

        @enabled.setter
        def enabled(self, enabled):
            self._enabled = bool(enabled)

        @property
        def power(self):
            return self._power

        @power.setter
        def power(self, power):
            if power < 0 or power > 255:
                raise ValueError('power argument must be in the range [0, 255].')
            self._power = int(power)

        @property
        def idx(self):
            return self._idx

    _lampNames = [
        'red',
        'green',
        'cyan',
        'UV',
        'blue',
        'teal' ]
    _lampDisableMasks = bytearray((0x01, 0x02, 0x04, 0x08, 0x20, 0x40))
    _lampDisableCommandBase = bytearray((0x4f, 0x00, 0x50))
    _lampPowerMasks = bytearray((0x08, 0x04, 0x02, 0x01, 0x01, 0x02))
    _lampRgcuPowerCommandBase = bytearray((0x53, 0x18, 0x03, 0x00, 0xF0, 0x00, 0x50))
    _lampBtPowerCommandBase = bytearray((0x53, 0x1A, 0x03, 0x00, 0xF0, 0x00, 0x50))

    def __init__(self, serialPortDescriptor='/dev/ttySptrx', name='Lumencor Spectra-X'):
        super().__init__(name)
        self._appendTypeName('Lumencor')
        self._serialPort = serial.Serial(serialPortDescriptor, 9600, timeout=1)
        if not self._serialPort.isOpen():
            raise LumencorException('Failed to open {}.'.format(serialPortDescriptor))
        # RS232 Lumencor docs state: "The [following] two commands MUST be issued after every power cycle to properly configure controls for further commands."
        # "Set GPIO0-3 as open drain output"
        self._write(bytearray((0x57, 0x02, 0xFF, 0x50)))
        # "Set GPI05-7 push-pull out, GPIO4 open drain out"
        self._write(bytearray((0x57, 0x03, 0xAB, 0x50)))
        # The lumencor box replies with nonsense to the first get temperature request.  We issue a get temperature request and ignore the result so that the next
        # get temperature request returns useful data.
        ignored = self.temperature
        del ignored
        self._lampStates = {name : Lumencor.LampState(False, 0, idx) for idx, name in enumerate(Lumencor._lampNames)}
        self._disablement = 0x0f
        # We don't know what state the Lumencor box was when we started, and we have no way of querying it.  However, we want its state to match our idea of its
        # state, which is all lamps disabled and at zero power, as set by the previous line of code.
        # First, all red, green, cyan, and UV lamps are set to zero power.
        c = Lumencor._lampRgcuPowerCommandBase.copy()
        c[3] = 0x0F
        self._applyPower(c, 0)
        self._write(c)
        # Next, blue and teal are set to zero power
        c = Lumencor._lampBtPowerCommandBase.copy()
        c[3] = 0x03
        self._applyPower(c, 0)
        self._write(c)
        # Finally, all lamps are disabled
        c = Lumencor._lampDisableCommandBase.copy()
        c[1] |= 0x7f
        self._write(c)

    def _write(self, byteArray):
#       print(''.join('{:02x} '.format(x) for x in byteArray))
        byteCountWritten = self._serialPort.write(byteArray)
        byteCount = len(byteArray)
        if byteCountWritten != byteCount:
            raise LumencorException('Attempted to write {} bytes to Lumencor serial port, but only {} bytes were written.'.format(byteCount, byteCountWritten))

    def _applyPower(self, command, power):
        if power < 0 or power > 0xff:
            raise ValueError('power < 0 or power > 0xff.')
        power = 0xff - power
        command[4] |= (power & 0xf0) >> 4
        command[5] |= (power & 0x0f) << 4

    def _updateDisablement(self):
        disablement = self._disablement
        for lampName, lampState in self._lampStates.items():
            if not lampState.enabled:
                disablement |= Lumencor._lampDisableMasks[lampState.idx]
            else:
                disablement &= 0x7f ^ Lumencor._lampDisableMasks[lampState.idx]
        # Only issue disablement command if disablement state has changed
        if disablement != self._disablement:
            c = Lumencor._lampDisableCommandBase.copy()
            c[1] = disablement
            self._write(c)
            self._disablement = disablement

    @property
    def temperature(self):
        self._write(bytearray((0x53, 0x91, 0x02, 0x50)))
        r = self._serialPort.read(2)
        if len(r) == 2:
            return ((r[0] << 3) | (r[1] >> 5)) * 0.125

    def enable(self, lampName=None, power=255):
        '''lampName: If None or [], all lamps are disabled.  If a string, the named lamp is enabled, and all others are disabled.  If a list, the named
        lamps are enabled, and all others are disabled.

        power: If a single value, all named lamps are set to it.  If a list, then each element represents the power value for corresponding element of
        lampName (so, if power is a list, then lampName must be a list with the same number of elements).'''
        lampStates = self.lampStates

        if lampName is None or (type(lampName) is not str and len(lampName) == 0):
            # Empty lampName argument.  Disable all lamps.
            for ln, ls in lampStates.items():
                ls.enabled = False
        elif type(lampName) is str:
            # Single string lampName argument.  Enable the specified lamp and set its power; disable all other lamps.
            if lampName not in lampStates:
                raise ValueError('"{}" is not a valid lamp name.'.format(lampName))
            for ln, ls in lampStates.items():
                if lampName == ln:
                    ls.enabled = True
                    ls.power = power
                else:
                    ls.enabled = False
        else:
            # lampName is a list of lamp names.  All lamps not appearing in the list are disabled.  If power is a single value rather than a list,
            # all named lamps powers are set to power.
            for ln, ls in lampStates.items():
                ls.enabled = False

            powers = power
            try:
                lampNameCount = len(lampName)
            except TypeError as e:
                raise TypeError('lampName is neither a string, nor None, nor an empty indexable, nor an indexable container of strings.  ' +
                                'Whatever it is, this function can not understand it.')
            try:
                if lampNameCount != len(powers):
                    raise ValueError('If the lampName and power arguments are both lists, then they must have the same number of elements.')
            except TypeError as e:
                powers = [power for x in range(lampNameCount)]

            for ln, lp in zip(lampName, powers):
                ls = lampStates[ln]
                ls.enabled = True
                ls.power = lp
            
        self.lampStates = lampStates

    def power(self, lampName, power=255):
        '''The same idea as enable(..), except without enabling or disabling lamps.  Thus, if None or an empty list is supplied for lampName,
        this function is a no-op.'''
        lampStates = self.lampStates

        if lampName is None or (type(lampName) is not str and len(lampName) == 0):
            # Empty lampName argument.  Do nothing.
            pass
        elif type(lampName) is str:
            # Single string lampName argument.  Set the specified lamp's power.
            lampStates[lampName].power = power
        else:
            # lampName is a list of lamp names.  If power is a single value rather than a list, all named lamps powers are set to power.  Otherwise,
            # each named lamp is set to the corresponding power element.
            powers = power
            try:
                lampNameCount = len(lampName)
            except TypeError as e:
                raise TypeError('lampName is neither a string, nor None, nor an empty indexable, nor an indexable container of strings.  ' +
                                'Whatever it is, this function can not understand it.')
            try:
                if lampNameCount != len(powers):
                    raise ValueError('If the lampName and power arguments are both lists, then they must have the same number of elements.')
            except TypeError as e:
                powers = [power for x in range(lampNameCount)]

            for ln, lp in zip(lampName, powers):
                ls = lampStates[ln]
                ls.power = lp
            
        self.lampStates = lampStates

    def disable(self, lampName=None):
        '''If lampName is None or an empty list, all lamps are disabled.  If lampName is a string or a non-empty list, then only the named lamp(s)
        are disabled.'''
        lampStates = self.lampStates

        if lampName is None or (type(lampName) is not str and len(lampName) == 0):
            # Empty lampName argument.  Disable all lamps.
            for ln, ls in lampStates.items():
                ls.enabled = False
        elif type(lampName) is str:
            # Single string lampName argument.  Disable the specified lamp.
            lampStates[lampName].enabled = False
        else:
            # List of lampNames.  Disable specified lamps.
            for ln in lampName:
                lampStates[ln].enabled = False

        self.lampStates = lampStates

    @property
    def lampStates(self):
        '''Returns a copy of the dict containing lamp names -> current lamp states.'''
        return copy.deepcopy(self._lampStates)

    @lampStates.setter
    def lampStates(self, lampStates):
        '''Apply new lamp states contained in the lampStates argument, which should be a dict of lamp names to LampState objects.  The state of any lamp
        not appearing in the lampStates argument dict is not modified.  So, lumencoreinstance.lampStates = {} is a no-op.  The specified state changes
        are consolidated into the fewest number of serial commands required before being dispatched to the Lumencor hardware.'''
        lampStateChangesForObserver = {}
        power_rgcu = {}
        power_bt = {}
        for lampName, newLampState in lampStates.items():
            curLampState = self._lampStates[lampName]
            curPower = curLampState.power
            newPower = newLampState.power
            if newPower != curPower:
                lampStateChangesForObserver[lampName] = {'power' : newPower}
                if curLampState.enabled != newLampState.enabled:
                    lampStateChangesForObserver[lampName]['enabled'] = newLampState.enabled
                #if lampName in ['red', 'green', 'cyan', 'uv']:
                if newLampState.idx in range(4): # Same effect as line above but faster
                    powerdict = power_rgcu
                else:
                    powerdict = power_bt

                if newPower in powerdict:
                    lampIdxs = powerdict[newPower]
                    lampIdxs.append(newLampState.idx)
                else:
                    powerdict[newPower] = [newLampState.idx]
            elif curLampState.enabled != newLampState.enabled:
                lampStateChangesForObserver[lampName] = {'enabled' : newLampState.enabled}
            curLampState.enabled = newLampState.enabled
            curLampState.power = newLampState.power

        def updatePowers(commandBase, powerdict):
            if len(powerdict) > 0:
                c = commandBase.copy()
                for power, lampIdxs in powerdict.items():
                    self._applyPower(c, power)
                    for lampIdx in lampIdxs:
                        c[3] |= Lumencor._lampPowerMasks[lampIdx]
                self._write(c)

        updatePowers(Lumencor._lampRgcuPowerCommandBase, power_rgcu)
        updatePowers(Lumencor._lampBtPowerCommandBase, power_bt)
        self._updateDisablement()

        for observer in self._observers:
            try:
                observer.notifyLumencorLampStatesChanged(self, lampStateChangesForObserver)
            except AttributeError as e:
                pass

    def forceComprehensiveObserverNotification(self, observer):
        lampStateChangesForObserver = {}
        for ln, ls in self._lampStates.items():
            lampStateChangesForObserver[ln] = {'enabled' : ls.enabled, 'power' : ls.power}
        try:
            observer.notifyLumencorLampStatesChanged(self, lampStateChangesForObserver)
        except AttributeError as e:
            pass
        super().forceComprehensiveObserverNotification(observer)

    @property
    def redEnabled(self):
        return self._lampStates['red'].enabled

    @redEnabled.setter
    def redEnabled(self, enabled):
        scur = self.lampStates['red']
        self.lampStates = {'red' : Lumencor.LampState(enabled, scur.power, scur.idx)}

    @property
    def redPower(self):
        return self._lampStates['red'].power

    @redPower.setter
    def redPower(self, power):
        scur = self.lampStates['red']
        self.lampStates = {'red' : Lumencor.LampState(scur.enabled, power, scur.idx)}

    @property
    def greenEnabled(self):
        return self._lampStates['green'].enabled

    @greenEnabled.setter
    def greenEnabled(self, enabled):
        scur = self.lampStates['green']
        self.lampStates = {'green' : Lumencor.LampState(enabled, scur.power, scur.idx)}

    @property
    def greenPower(self):
        return self._lampStates['green'].power

    @greenPower.setter
    def greenPower(self, power):
        scur = self.lampStates['green']
        self.lampStates = {'green' : Lumencor.LampState(scur.enabled, power, scur.idx)}

    @property
    def cyanEnabled(self):
        return self._lampStates['cyan'].enabled

    @cyanEnabled.setter
    def cyanEnabled(self, enabled):
        scur = self.lampStates['cyan']
        self.lampStates = {'cyan' : Lumencor.LampState(enabled, scur.power, scur.idx)}

    @property
    def cyanPower(self):
        return self._lampStates['cyan'].power

    @cyanPower.setter
    def cyanPower(self, power):
        scur = self.lampStates['cyan']
        self.lampStates = {'cyan' : Lumencor.LampState(scur.enabled, power, scur.idx)}

    @property
    def UVEnabled(self):
        return self._lampStates['UV'].enabled

    @UVEnabled.setter
    def UVEnabled(self, enabled):
        scur = self.lampStates['UV']
        self.lampStates = {'UV' : Lumencor.LampState(enabled, scur.power, scur.idx)}

    @property
    def UVPower(self):
        return self._lampStates['UV'].power

    @UVPower.setter
    def UVPower(self, power):
        scur = self.lampStates['UV']
        self.lampStates = {'UV' : Lumencor.LampState(scur.enabled, power, scur.idx)}

    @property
    def blueEnabled(self):
        return self._lampStates['blue'].enabled

    @blueEnabled.setter
    def blueEnabled(self, enabled):
        scur = self.lampStates['blue']
        self.lampStates = {'blue' : Lumencor.LampState(enabled, scur.power, scur.idx)}

    @property
    def bluePower(self):
        return self._lampStates['blue'].power

    @bluePower.setter
    def bluePower(self, power):
        scur = self.lampStates['blue']
        self.lampStates = {'blue' : Lumencor.LampState(scur.enabled, power, scur.idx)}

    @property
    def tealEnabled(self):
        return self._lampStates['teal'].enabled

    @tealEnabled.setter
    def tealEnabled(self, enabled):
        scur = self.lampStates['teal']
        self.lampStates = {'teal' : Lumencor.LampState(enabled, scur.power, scur.idx)}

    @property
    def tealPower(self):
        return self._lampStates['teal'].power

    @tealPower.setter
    def tealPower(self, power):
        scur = self.lampStates['teal']
        self.lampStates = {'teal' : Lumencor.LampState(scur.enabled, power, scur.idx)}

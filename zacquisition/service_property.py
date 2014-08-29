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

import threading
import weakref

class ServiceProperty:
    '''A Python new-style-class descriptor.  Python object properties are another example of descriptors.
    Descriptors are extremely confusing in that descriptor instances must reside as class objects and not
    class instance member variables - and yet masquerade as instance member variables.  The masquerade
    is accomplished by __getattr__ implementing The Descriptor Protocol wherein set, get, del, and other statements
    are transformed into descriptor.__set__(descriptor_self, instance_self, new_value),
    descriptor.__get__(descriptor_self, instance_self, instance_cls), descriptor.__delete__(descriptor_self,
    instance_self), and etc calls.  The calls always include an instance_self argument - information that is
    essential if the static descriptor instance is to know what the hell actual object's variable instance
    or underlying represented state it is to manipulate when a set, get, del, or etc operation is performed.

    The descriptor mechanism is particularly useful when used to provide a generalized abstraction for
    getters and setters that require similar constraints and produce similar side effects: rather than
    each getter and setter reproducing constraint checking and side effect propagation code,
    the entire getter/setter/membervariable blob acting as a property common to all instances of a
    class is represented by a single class instance of a descriptor.  Note that, although ServiceProperty
    descriptors are not meant to be used through the member function decorator syntax, the benefit of
    the .property syntactic sugar offered by using @property member function decorators is preserved.'''

    def __init__(self, default, name, validators=None):
        '''Validators may be None, a function or some other kind of callable, or an iterable of callables.
        The return value from a validator is ignored - if it returns at all rather than raising an exception,
        the validator is assumed to have confirmed the validity of the value to be __set__.  Additionally, the
        first argument fed to the validator is the instance holding the property to be assigned in case validity
        depends on other aspect of its owner's instance's state (the second argument being the value to be
        assigned).  For example, if a Season class has a designation property containing a value in the
        set {'Spring', 'Summer', 'Fall', 'Winter'} and a meanTemperature property containing a centigrade value,
        meanTemperature's validator must know if the Season class instance's designation value is 'Summer' in
        order to determine that -28 is invalid for meanTemperature.'''
        self.default = default
        self.name = name
        self._validators = validators
        self._instanceToValue = weakref.WeakKeyDictionary()
        self._instanceToCallbacks = weakref.WeakKeyDictionary()
        self._instanceToLock = weakref.WeakKeyDictionary()

    def _getLock(self, instance):
        if instance not in self._instanceToLock:
            lock = threading.Lock()
            self._instanceToLock[instance] = lock
            return lock
        else:
            return self._instanceToLock[instance]

    def __get__(self, instance, owner):
        if instance is None:
            '''Allow descriptor instance to be accessed through owner at class level.  This is useful, for example,
            to access the addCallback and removeCallback methods.'''
            return self
        else:
            with self._getLock(instance):
                return self._instanceToValue.get(instance, self.default)

    def __set__(self, instance, value):
        '''Note that setting a property for the first time on the client end always results in the transmission of
        a property change request, even if the value assigned is identical to the property's default value.
        Likewise, setting a property for the first time on the daemon end always results in the transmission of a
        property change notification, even if the value assigned is identical to the property's default value.'''
        if self._validators is not None:
            if callable(self._validators):
                self._validators(instance, value)
            else:
                for validator in self._validators:
                    validator(instance, value)

        def getcurrval():
            with self._getLock(instance):
                return self._instanceToValue[instance]

        if instance not in self._instanceToValue or value != getcurrval():
            if instance.instanceType == instance.InstanceType.Client:
                instance._sendChangePropCommand(self.name, value)
            else:
                with self._getLock(instance):
                    self._instanceToValue[instance] = value
                instance._sendPropChangeNotification(self.name, value)
                if instance in self._instanceToCallbacks:
                    for callback in self._instanceToCallbacks[instance]:
                        callback(instance, value)

    def setWithoutValidating(self, instance, value):
        '''Replace stored value without executing validators.  Useful for initializing or updating a property
        that is not directly user modifiable.'''
        if instance not in self._instanceToValue or value != self._instanceToValue[instance]:
            with self._getLock(instance):
                self._instanceToValue[instance] = value
            if instance in self._instanceToCallbacks:
                for callback in self._instanceToCallbacks[instance]:
                    callback(instance, value)

    def addCallback(self, instance, callback):
        '''Add callback to execute upon modification of the property value represented by this descriptor and
        instance combination.  Returns For example:
        FooClass.serviceProperty.addCallback(fooClassInstance, callbackFunction)'''
        with self._getLock(instance):
            if instance in self._instanceToCallbacks:
                # In debug mode, detect attempts to add duplicate callbacks
                assert(callback not in self._instanceToCallbacks[instance])
                self._instanceToCallbacks[instance].append(callback)
            else:
                self._instanceToCallbacks[instance] = [callback]

    def removeCallback(self, instance, callback):
        '''Note that it is not necessary to explicitly remove callbacks before deleting an instance containing
        properties: because the instanceToCallbacks dictionary uses weak keys, the relevant entry and its list
        of callbacks will be removed automatically.'''
        with self._getLock(instance):
            callbackList = self._instanceToCallbacks[instance]
            del callbackList[callbackList.index(callback)]

    def removeAllCallbacks(self, instance):
        '''Note that it is not necessary to explicitly remove callbacks before deleting an instance containing
        properties: because the instanceToCallbacks dictionary uses weak keys, the relevant entry and its list
        of callbacks will be removed automatically.'''
        with self._getLock(instance):
            if instance in self._instanceToCallbacks:
                del self._instanceToCallbacks[instance]

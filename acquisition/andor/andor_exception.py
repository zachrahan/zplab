# Copyright 2014 WUSTL ZPLAB

from acquisition.acquisition_exception import AcquisitionException

class AndorException(AcquisitionException):
    def __init__(self, description, errorCode = None, errorName = None):
        self.description = description
        self.errorCode = errorCode
        self.errorName = errorName

    def __str__(self):
        if self.errorCode is not None and self.errorName is not None:
            return '{}.  Andor SDK error code: {} ({}).'.format(self.description, self.errorCode, self.errorName)
        else:
            return self.description

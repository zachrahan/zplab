# Copyright 2014 WUSTL ZPLAB

from acquisition.acquisition_exception import AcquisitionException

class LumencorException(AcquisitionException):
    def __init__(self, description):
        self.description = description

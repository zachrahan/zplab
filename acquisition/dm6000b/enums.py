# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import enum

@enum.unique
class ImmersionOrDry(enum.Enum):
    Dry = 0
    Immersion = 1

@enum.unique
class Method(enum.IntEnum):
    '''Leica DM6000B "method" as described in reference for 70 026 in "The serial interface documentation
    for the stands DM4000, DM5000, DM6000; Version 1.5; August 2010 (DM456K_SER_REF.pdf).'''
    TL_BF = 0
    TL_PH = 1
    TL_DF = 2
    TL_DIC = 3
    TL_POL = 4
    IL_BF = 5
    IL_OBL = 6
    IL_DF = 7
    IL_DIC = 8
    IL_POL = 9
    FLUO = 10
    FLUOslashPH = 11
    FLUOslashDIC = 12
    BFslashBF = 13
    UNUSED0 = 14
    UNUSED1 = 15

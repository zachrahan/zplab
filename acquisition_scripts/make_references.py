from pathlib import Path
import freeimage

SLIDE_WIDTH = 1
SLIDE_HEIGHT = 1

def make_references(dpath, prefix):
    '''Position stage at min x and y coordinates of slide.'''
    dpath = Path(dpath)


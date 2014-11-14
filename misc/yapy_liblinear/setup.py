import os, numpy

def configuration(parent_package='',top_path=None):
    from numpy.distutils.misc_util import Configuration
    config = Configuration('liblinear',parent_package,top_path)
    config.add_data_files('liblinear.dylib')
    config.add_data_files('liblinear-poly2.dylib')
    config.add_extension('_fast_linear_classify', ['_fast_linear_classify.pyx'])
    return config

if __name__ == '__main__':
    from numpy.distutils.core import setup
    setup(**configuration(top_path='').todict())

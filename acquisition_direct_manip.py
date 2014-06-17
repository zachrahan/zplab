#!/usr/bin/env python3
# Copyright 2014 WUSTL ZPLAB

import argparse
parser = argparse.ArgumentParser('acquisition_direct_manip.py')
parser.add_argument('module', choices=['andor', 'lumencor', 'brightfield_led', 'root'])
parser.add_argument('module_args', metavar='module-arg', nargs=argparse.REMAINDER)
args = parser.parse_args()

exec('from acquisition.{} import direct_manip'.format(args.module))
direct_manip.show(launcherDescription='acquisition_direct_manip.py {}'.format(args.module), moduleArgs=args.module_args)


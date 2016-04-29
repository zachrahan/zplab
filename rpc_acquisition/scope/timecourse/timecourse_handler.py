# The MIT License (MIT)
#
# Copyright (c) 2014-2015 WUSTL ZPLAB
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
# Authors: Erik Hvatum <ice.rikh@gmail.com>, Zach Pincus <zpincus@wustl.edu>

import numpy
import logging
import time

from . import base_handler
from ..client_util import autofocus
from ..client_util import calibrate

from ..util.threaded_image_io import COMPRESSION

class BasicAcquisitionHandler(base_handler.TimepointHandler):
    """Base class for most timecourse acquisition needs.

    To create a new timepoint acquisition, the user MUST subclass this class
    from a file that resides INSIDE the desired data-acquisition directory. An
    'experiment_metadata.json' file MUST be created in the same directory,
    containing a dict with keys 'positions', 'z_max', and
    'reference_positions'. The value of 'positions' MUST be a dict mapping
    position names to (x,y,z) stage coords for data acquisition. 'z_max' MUST
    be an single number representing the highest the stage can go during
    autofocus. 'reference_positions' MUST be a list of one or more (x,y,z)
    stage coords to obtain brightfield and fluorescence flatfield reference
    data from.

    The python file implementing the subclass MUST have the following stanza
    at the bottom:
        if __name__ == '__main__':
            MySubclass.main()
    where 'MySubclass' is replaced with whatever the name of the subclass is.

    The subclass MUST set the FILTER_CUBE attribute. In addition, if
    fluorescent flat-field images are desired the subclass MAY set
    FLUORESCENCE_FLATFIELD_LAMP to the name of a spectra X lamp that is
    compatible with the selected filter cube.

    The subclass MUST override the get_next_run_interval() method to return
    the desired time interval between the beginning of the current run and
    the beginning of the next. To control the interpretation of this interval,
    the subclass MAY set the INTERVAL_MODE attribute to one of 'scheduled
    start', 'actual start', 'end'. This selects what the starting time for the
    interval before the next run should be: when the job was scheduled to start,
    when it actually started, or when the job ends, respectively.

    The subclass MAY override configure_additional_acquisition_steps() to
    add additional image acquisitions (after the initial default brightfield
    acquisition). The base class docstring shows an example of adding a 200 ms
    GFP exposure, which also requires adding the name of the image file to save
    out to the self.image_names attribute.
    """

    # Attributes and functions subclasses MUST or MAY override are here:
    # First: Really important attributes to override
    FILTER_CUBE = 'Choose a filter cube!'
    FLUORESCENCE_FLATFIELD_LAMP = None # MAKE SURE THIS IS COMPATIBLE WITH THE FILTER CUBE!!!

    # Next: Potentially useful attributes to override
    OBJECTIVE = 10
    COARSE_FOCUS_RANGE = 1
    COARSE_FOCUS_STEPS = 50
    # 1 mm distance in 50 steps = 20 microns/step. So we should be somewhere within 20-40 microns of the right plane after the above autofocus.
    # We want to get within 1-2 microns, so sweep over 100 microns with 75 steps.
    FINE_FOCUS_RANGE = 0.1
    FINE_FOCUS_STEPS = 75
    PIXEL_READOUT_RATE = '100 MHz'
    USE_LAST_FOCUS_POSITION = True
    INTERVAL_MODE = 'scheduled start'
    IMAGE_COMPRESSION = COMPRESSION.DEFAULT # useful options include PNG_FAST, PNG_NONE, TIFF_NONE
    LOG_LEVEL = logging.INFO
    # Set the following to have the script set the microscope apertures as desired:
    TL_FIELD_DIAPHRAGM = None
    TL_APERTURE_DIAPHRAGM = None
    IL_FIELD_WHEEL = None
    VIGNETTE_PERCENT = 5 # 5 is a good number when using a 1x optocoupler. If 0.7x, use 35.

    def configure_additional_acquisition_steps(self):
        """Add more steps to the acquisition_sequencer's sequence as desired,
        making sure to also add corresponding names to the image_name attribute.
        For example, to add a 200 ms GFP acquisition, a subclass may override
        this as follows:
            def configure_additional_acquisition_steps(self):
                self.scope.camera.acquisition_sequencer.add_step(exposure_ms=200, lamp='cyan')
                self.image_names.append('gfp.png')
        """
        pass

    def get_next_run_interval(self, experiment_hours):
        """Return the delay interval, in hours, before the experiment should be
        run again.

        The interval will be interpreted according to the INTERVAL_MODE attribute,
        as described in the class documentation. Returning None indicates that
        timepoints should not be acquired again.

        Parameters:
            experiment_hours: number of hours between the start of the first
                timepoint and the start of this timepoint.
        """
        raise NotImplementedError()

    def should_skip(self, position_dir, position_metadata, images):
        """Return whether this position should be skipped for future timepoints.

        Parameters:
            position_dir: pathlib.Path object representing the directory where
                position-specific data files and outputs are written. Useful for
                reading previous image data.
            position_metadata: list of all the stored position metadata from the
                previous timepoints, in chronological order.
            images: list of images acquired at this timepoint.

        Returns: True if the position should be skipped in future runs, False
            if not.
        """
        # TODO: determine appropriate thresholds for deciding if a worm is dead...
        return False


    # Internal implementation functions are below. Override with care.
    def configure_timepoint(self):
        t0 = time.time()
        self.logger.info('Configuring acquisitions')
        self.scope.async = False
        # in 'TL BF' mode, condenser auto-retracts for 5x objective, and field/aperture get set appropriately
        # on objective switch. That gives a sane-ish default. Then allow specific customization of
        # these values later.
        self.scope.stand.active_microscopy_method = 'TL BF'
        self.scope.nosepiece.magnification = self.OBJECTIVE
        self.scope.il.shutter_open = True
        self.scope.il.spectra_x.lamps(**{lamp+'_enabled':False for lamp in self.scope.il.spectra_x.lamp_specs})
        self.scope.tl.shutter_open = True
        self.scope.tl.lamp.enabled = False
        self.scope.tl.condenser_retracted = self.OBJECTIVE == 5 # only retract condenser for 5x objective
        if self.TL_FIELD_DIAPHRAGM is not None:
            self.scope.tl.field_diaphragm = self.TL_FIELD_DIAPHRAGM
        if self.TL_APERTURE_DIAPHRAGM is not None:
            self.scope.tl.aperture_diaphragm = self.TL_APERTURE_DIAPHRAGM
        if self.IL_FIELD_WHEEL is not None:
            self.scope.il.field_wheel = self.IL_FIELD_WHEEL
        self.scope.il.filter_cube = self.FILTER_CUBE
        self.scope.camera.sensor_gain = '16-bit (low noise & high well capacity)'
        self.scope.camera.readout_rate = self.PIXEL_READOUT_RATE
        self.scope.camera.shutter_mode = 'Rolling'
        self.configure_calibrations() # sets self.bf_exposure and self.tl_intensity
        self.scope.camera.acquisition_sequencer.new_sequence() # internally sets all spectra x intensities to 255, unless specified here
        self.scope.camera.acquisition_sequencer.add_step(exposure_ms=self.bf_exposure,
            lamp='TL', tl_intensity=self.tl_intensity)
        self.image_names = ['bf.png']
        self.configure_additional_acquisition_steps()
        t1 = time.time()
        self.logger.debug('Configuration done ({:.1f} seconds)', t1-t0)

    def configure_calibrations(self):
        self.dark_corrector = calibrate.DarkCurrentCorrector(self.scope)
        ref_positions = self.experiment_metadata['reference_positions']

        # go to a data-acquisition position and figure out the right brightfield exposure
        data_positions = self.experiment_metadata['positions']
        some_pos = list(data_positions.values())[0]
        self.scope.stage.position = some_pos
        self.bf_exposure, self.tl_intensity = calibrate.meter_exposure_and_intensity(self.scope, self.scope.tl.lamp,
            max_exposure=32, min_intensity_fraction=0.2, max_intensity_fraction=0.5)

        # calculate the BF flatfield image and reference intensity value
        self.scope.stage.position = ref_positions[0]
        with self.scope.tl.lamp.in_state(enabled=True):
            exposure = calibrate.meter_exposure(self.scope, self.scope.tl.lamp,
            max_exposure=32, min_intensity_fraction=0.3, max_intensity_fraction=0.85)
            exposure_ratio = self.bf_exposure / exposure
            bf_avg = calibrate.get_averaged_images(self.scope, ref_positions,
                self.dark_corrector, frames_to_average=2)
        self.vignette_mask = calibrate.get_vignette_mask(bf_avg, VIGNETTE_PERCENT)
        bf_flatfield, ref_intensity = calibrate.get_flat_field(bf_avg, self.vignette_mask)
        ref_intensity *= exposure_ratio
        cal_image_names = ['vignette_mask.png', 'bf_flatfield.tiff']
        cal_images = [self.vignette_mask.astype(numpy.uint8)*255, bf_flatfield]

        # calculate a fluorescent flatfield if requested
        if self.FLUORESCENCE_FLATFIELD_LAMP:
            self.scope.stage.position = ref_positions[0]
            lamp = getattr(self.scope.il.spectra_x, self.FLUORESCENCE_FLATFIELD_LAMP)
            with lamp.in_state(enabled=True):
                calibrate.meter_exposure_and_intensity(self.scope, lamp, max_exposure=400,
                    min_intensity_fraction=0.1)
                fl_avg = calibrate.get_averaged_images(self.scope, ref_positions,
                    self.dark_corrector, frames_to_average=5)
            fl_flatfield, fl_intensity = calibrate.get_flat_field(fl_avg, self.vignette_mask)
            cal_image_names.append('fl_flatfield.tiff')
            cal_images.append(fl_flatfield)

        # save out calibration information
        calibration_dir = self.data_dir / 'calibrations'
        if not calibration_dir.exists():
            calibration_dir.mkdir()
        cal_image_paths = [calibration_dir / (self.timepoint_prefix + ' ' + name) for name in cal_image_names]
        if self.write_files:
            self.image_io.write(cal_images, cal_image_paths)
        metering = self.experiment_metadata.setdefault('brightfield metering', {})
        metering[self.timepoint_prefix] = dict(exposure=self.bf_exposure, intensity=self.tl_intensity, ref_intensity=ref_intensity)
        self.scope.camera.exposure_time = self.bf_exposure

    def get_next_run_time(self):
        interval_mode = self.INTERVAL_MODE
        assert interval_mode in {'scheduled start', 'actual start', 'end'}
        timestamps = self.experiment_metadata['timestamps']
        elapsed_sec = timestamps[-1] - timestamps[0]# time since beginning of timecourse
        elapsed_hours = elapsed_sec / 60**2
        interval_hours = self.get_next_run_interval(elapsed_hours)
        interval_seconds = interval_hours * 60**2
        if interval_hours is None:
            return None
        if interval_mode == 'scheduled start':
            seconds_delayed = self.start_time - self.scheduled_start
            if seconds_delayed > interval_seconds:
                # we've fallen more than a full cycle behind!
                # keep the relative phase of the cycle, but skip all the
                # cycles that we've lost.
                phase = seconds_delayed % interval_seconds
                start = self.start_time - phase
            else:
                start = self.scheduled_start

        elif interval_mode == 'actual start':
            start = self.start_time
        else:
            start = self.end_time
        return start + interval_seconds

    def acquire_images(self, position_name, position_dir, position_metadata):
        t0 = time.time()
        if self.USE_LAST_FOCUS_POSITION and position_metadata:
            z_start = position_metadata[-1]['fine_z']
        else:
            z_start = self.positions[position_name][2]
        z_max = self.experiment_metadata['z_max']
        self.scope.camera.exposure_time = self.bf_exposure
        self.scope.tl.lamp.intensity = self.tl_intensity
        with scope.tl.lamp.in_state(enabled=True), scope.stage.in_state(z_speed=1):
            coarse_z, fine_z = autofocus.coarse_fine_autofocus(self.scope, z_start, z_max,
                self.COARSE_FOCUS_RANGE, self.COARSE_FOCUS_STEPS,
                self.FINE_FOCUS_RANGE, self.FINE_FOCUS_STEPS)
        t1 = time.time()
        self.logger.debug('Autofocused ({:.1f} seconds)', t1-t0)
        self.logger.info('Autofocus z: {}', fine_z)
        images = self.scope.camera.acquisition_sequencer.run()
        t2 = time.time()
        self.logger.debug('Acquisition sequence run ({:.1f} seconds)', t2-t1)
        exposures = self.scope.camera.acquisition_sequencer.exposure_times
        images = [self.dark_corrector.correct(image, exposure) for image, exposure in zip(images, exposures)]
        timestamps = numpy.array(self.scope.camera.acquisition_sequencer.latest_timestamps)
        timestamps = (timestamps - timestamps[0]) / self.scope.camera.timestamp_hz
        metadata = dict(coarse_z=coarse_z, fine_z=fine_z, image_timestamps=dict(zip(self.image_names, timestamps)))
        if self.should_skip(position_dir, position_metadata, images):
            self.skip_positions.append(position_name)
        return images, self.image_names, metadata

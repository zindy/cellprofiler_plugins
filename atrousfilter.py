
#CellProfiler is distributed under the GNU General Public License.
#See the accompanying file LICENSE for details.
#
#Copyright (c) 2003-2009 Massachusetts Institute of Technology
#Copyright (c) 2009-2014 Broad Institute
#All rights reserved.
#
#Please see the AUTHORS file for credits.
#
#Website: http://www.cellprofiler.org

from cellprofiler_core.image import Image
from cellprofiler_core.module import ImageProcessing
from cellprofiler_core.setting import Binary
from cellprofiler_core.setting.choice import Choice
from cellprofiler_core.setting.subscriber import ImageSubscriber
from cellprofiler_core.setting.text import ImageName,Float,Integer
from cellprofiler_core.setting.range import IntegerRange,FloatRange

import libatrous
import numpy as np

KERNEL_CHOICES = libatrous.get_names()

HELP_ATROUS_FILTER = """\
Single-channel images can be two-or-three-dimensional and multichannel images can be two-dimensional.
"""

__doc__ = """\
AtrousFilter
============

The **AtrousFilter** is an image processing module which applies the *A Trous* wavelet transform to an image.

{HELP_ATROUS_FILTER}

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          YES          NO
============ ============ ===============

""".format(
    **{"HELP_ATROUS_FILTER": HELP_ATROUS_FILTER}
)


class AtrousFilter(ImageProcessing):
    category = "Image Processing"
    module_name = "AtrousFilter"
    variable_revision_number = 1
    
    def create_settings(self):
        self.x_name = ImageSubscriber(
            text = "Input image name",
            doc = """This is the image that the module operates on. You can
            choose any image that is made available by a prior module.

            **AtrousFilter** will produce a filtered version of the input image.
            """)

        self.y_name = ImageName(
            text = "Output image name",
            value = "FilteredImage",
            doc = """This is the image resulting from the operation.""")

        self.atrous_overide_dimensions = Binary(
           "Do you want to overide voxel dimensions?",
           value=False,
           doc = """Pixel dimensions are normally read from metadata and are taken into account for correcting for
           rectangular pixels / voxels. For temporal (X,Y,T) stacks and temporal filtering, the "T" dimension may require
           additional tweaking.
           """
        )

        self.atrous_xdim = Float(
            "x", 1,
            doc="""The voxel size in the X dimension
            """
        )

        self.atrous_ydim = Float(
            "y", 1,
            doc="""The voxel size in the Y dimension
            """
        )

        self.atrous_zdim = Float(
            "z", 1,
            doc="""The voxel size in the Z dimension
            """
        )

        n_kernel = len(KERNEL_CHOICES)
        doc = "Choose which kernel to filter with: <ul>"
        for i in range(n_kernel):
            kernel = libatrous.get_kernel(i)
            doc += "* %s: %s" % (KERNEL_CHOICES[i],str(kernel))

        self.atrous_choice = Choice(
            "Kernel type",
            # The choice takes a list of possibilities. The first one
            # is the default - the one the user will typically choose.
            KERNEL_CHOICES,
            #
            # Here, in the documentation, we do a little trick so that
            # we use the actual text that's displayed in the documentation.
            #
            # %(KERNEL_CHOICES[0])s will get changed into "Linear 3x3"
            # etc. Python will look in globals() for the "ATROUS_" names
            # and paste them in where it sees %(ATROUS_...)s
            #
            # The <ul> and <li> tags make a neat bullet-point list in the docs
            #
            #doc = doc % globals()
        )

        self.atrous_scalerange = IntegerRange(
           "Band-pass filter width (smallest / largest scale)", (1, 8),
           minval=1, maxval=10,

           doc="""The smallest and largest scale to include in the filter determine the width
           of the band-pass filter. Single scale filters are entered by using the same scale
           index for the smallest and largest scale.<br><br>

           A High-pass filter would start at scale 1 and not include the residual low-pass
           filter, whereas a low-pass filter would start at a small scale greater than 1
           and would include the residual low-pass filter.<br><br>

           Any filter whose smallest scale is 1 and includes the residual low-pass filter
           would output the input image.
           """)
        self.atrous_lowpass = Binary(
           "Do you want to include the residual Low Pass image?",
           False,
           doc = """Add the residual Low Pass image to the filtered image.
           """)
        self.atrous_threshold = Binary(
           "Do you want to threshold the output?",
           True,
           doc = """The output image will be thresholded
           """)
        self.atrous_threshrange = FloatRange(
           "Threshold range percentile", (0, 100), 
           doc="""The lower and upper percentiles for the threshold range selection.
           """)
        self.atrous_normalise = Binary(
           "Do you want to normalise the output?",
           False,
           doc = """The output image will be normalised.
           """)

    #
    # This method ensures that the scales are within range
    def validate_scales(self):
        low_scale,high_scale = self.atrous_scalerange.value

        if low_scale > high_scale:
            low_scale = high_scale

        if high_scale < low_scale:
            high_scale = low_scale

        if high_scale > self.atrous_scalerange.get_max():
            self.atrous_scalerange.set_max(high_scale)

        self.atrous_scalerange.value = (low_scale,high_scale)

    #
    # The "settings" method tells CellProfiler about the settings you
    # have in your module. CellProfiler uses the list for saving
    # and restoring values for your module when it saves or loads a
    # pipeline file.
    #
    def settings(self):
        self.validate_scales()

        return [ self.x_name, self.y_name,
                 self.atrous_overide_dimensions,
                 self.atrous_xdim, self.atrous_ydim, self.atrous_zdim,
                 self.atrous_choice, self.atrous_scalerange,
                 self.atrous_lowpass,
                 self.atrous_threshold,self.atrous_threshrange,
                 self.atrous_normalise ]

    def visible_settings(self):
        self.validate_scales()

        __settings__ = [ self.x_name, self.y_name,
                   self.atrous_overide_dimensions ]

        if self.atrous_overide_dimensions:
            __settings__ += [self.atrous_xdim, self.atrous_ydim, self.atrous_zdim]

        __settings__ += [ self.atrous_choice, self.atrous_scalerange,
                    self.atrous_lowpass,
                    self.atrous_threshold]
        
        #only show the min/max threshold values if threshold is ticked
        if self.atrous_threshold:
            __settings__ += [self.atrous_threshrange]

        __settings__ += [self.atrous_normalise]
    
        return __settings__ 

    #
    # CellProfiler calls "run" on each image set in your pipeline.
    # This is where you do the real work.
    #
    def run(self, workspace):
        #
        # Get the input and output image names. You need to get the .value
        # because otherwise you'll get the setting object instead of
        # the string name.
        #

        x_name = self.x_name.value
        y_name = self.y_name.value
        #
        # Get the image set. The image set has all of the images in it.
        #
        image_set = workspace.image_set
        #
        # Get the input image object. We want a grayscale image here.
        # The image set will convert a color image to a grayscale one
        # and warn the user.
        #
        x = workspace.image_set.get_image(x_name,
                                          must_be_grayscale = True)
        #
        # Get the pixels - these are a 2-d Numpy array.
        #
        dimensions = x.dimensions
        value_max = x.scale
        pixels = x.pixel_data
        #
        # Get the wavelet parameters
        #
        kernel_index = KERNEL_CHOICES.index(self.atrous_choice)
        kernel = libatrous.get_kernel(kernel_index)

        low_scale,high_scale = self.atrous_scalerange.value

        #Here we need to calculate the thresholds from percentiles
        low_perc,high_perc = self.atrous_threshrange.value
        low_thresh,high_thresh = self.atrous_threshrange.value

        if 0:
            low_thresh = float(low_thresh) / value_max
            high_thresh = float(high_thresh) / value_max
        elif 0:
            low_thresh = float(low_thresh) * value_max / 100.
            high_thresh = float(high_thresh) * value_max / 100.

        #
        # build the output_pixels array iteratively
        #
        #atrous_pixels = libatrous.get_bandpass(pixels.astype(np.float32),low_scale-1,high_scale-1,kernel,self.atrous_lowpass)
        lowpass = pixels.astype(np.float32)
        output_pixels = np.zeros(pixels.shape,np.float32)
        for i in range(high_scale):
            bandpass,lowpass = libatrous.iterscale(lowpass,kernel,i)
            if i >= (low_scale-1):
                output_pixels += bandpass

        if self.atrous_lowpass:
            output_pixels += lowpass

        #
        # Do the thresholding (if needed -- always)
        #
        if self.atrous_threshold:
            #mi = np.min(output_pixels)
            #ma = np.max(output_pixels)

            #NEW Here we calculate the low and high thresholds:
            #Maybe only the positive pixels to begin with
            output_pixels[output_pixels < 0] = 0
            low_thresh = np.percentile(output_pixels, low_perc)
            high_thresh = np.percentile(output_pixels, high_perc)
            print("---")
            print("Percentiles:",low_perc,high_perc)
            print("Thresholds:",low_thresh,high_thresh)
            
            #Here we apply the thresholds
            output_pixels[output_pixels < low_thresh] = low_thresh
            output_pixels[output_pixels > high_thresh] = high_thresh

        #
        # Do we normalise?
        #
        if self.atrous_normalise:
            mi = float(np.min(output_pixels))
            ma = float(np.max(output_pixels))
            output_pixels = (output_pixels-mi)/(ma-mi)

        y = Image(output_pixels, parent_image = x)
        image_set.add(y_name, y)

        #
        # Save intermediate results for display if the window frame is on
        #
        if self.show_window:
            workspace.display_data.x_data = pixels
            workspace.display_data.y_data = output_pixels
            workspace.display_data.dimensions = dimensions

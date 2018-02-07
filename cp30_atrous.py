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

"""
AtrousFilter
============

The **Atrous filter** is an image processing module which applies the *A Trous* wavelet transform to an image.

Single-channel images can be two-or-three-dimensional and multichannel images can be two-dimensional.

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          YES          NO
============ ============ ===============

"""

import cellprofiler.image  as cpi
import cellprofiler.module as cpm
import cellprofiler.measurement as cpmeas
import cellprofiler.object as cpo
import cellprofiler.pipeline as cpp
import cellprofiler.setting as cps
import cellprofiler.workspace as cpw
from cellprofiler.setting import YES, NO
import libatrous
import numpy as np

KERNEL_CHOICES = libatrous.get_names()

###################################
#
# The module class
#
# Your module should "inherit" from cellprofiler.cpmodule.CPModule.
# This means that your module will use the methods from CPModule unless
# you re-implement them. You can let CPModule do most of the work and
# implement only what you need.
#
###################################

class AtrousFilter(cpm.ImageProcessing, object):
    ###############################################
    #
    # The module starts by declaring the name that's used for display,
    # the category under which it is stored and the variable revision
    # number which can be used to provide backwards compatibility if
    # you add user-interface functionality later.
    #
    ###############################################
    module_name = "AtrousFilter"
    category = "Image Processing"
    variable_revision_number = 1
    
    ###############################################
    #
    # create_settings is where you declare the user interface elements
    # (the "settings") which the user will use to customize your module.
    #
    # You can look at other modules and in cellprofiler.settings for
    # settings you can use.
    #
    ################################################
    
    def create_settings(self):
        #
        # The ImageNameSubscriber "subscribes" to all ImageNameProviders in 
        # prior modules. Modules before yours will put images into CellProfiler.
        # The ImageSubscriber gives your user a list of these images
        # which can then be used as inputs in your module.
        #
        self.x_name = cps.ImageNameSubscriber(
            # The text to the left of the edit box
            "Input image name:",
            # HTML help that gets displayed when the user presses the
            # help button to the right of the edit box
            doc = """This is the image that the module operates on. You can
            choose any image that is made available by a prior module.
            <br>
            <b>AtrousFilter</b> will produce a filtered version of the input image.
            """)
        #
        # The ImageNameProvider makes the image available to subsequent
        # modules.
        #
        self.y_name = cps.ImageNameProvider(
            "Output image name:",
            # The second parameter holds a suggested name for the image.
            "FilteredImage",
            doc = """This is the image resulting from the operation.""")
        
        self.atrous_overide_dimensions = cps.Binary(
           "Do you want to overide voxel dimensions?",
           False,
           doc = """Pixel dimensions are normally read from metadata and are taken into account for correcting for
           rectangular pixels / voxels. For temporal (X,Y,T) stacks and temporal filtering, the "T" dimension may require
           additional tweaking.
           """
        )

        self.atrous_xdim = cps.Float(
            "x", 1, minval=.01, maxval=100.0,
            doc="""The voxel size in the X dimension
            """
        )

        self.atrous_ydim = cps.Float(
            "y", 1, minval=.01, maxval=100.0,
            doc="""The voxel size in the Y dimension
            """
        )

        self.atrous_zdim = cps.Float(
            "z", 1, minval=.01, maxval=100.0,
            doc="""The voxel size in the Z dimension
            """
        )

        #
        # Here's a choice box - the user gets a drop-down list of what
        # can be done.
        #

        n_kernel = len(KERNEL_CHOICES)
        doc = "Choose which kernel to filter with: <ul>"
        for i in range(n_kernel):
            kernel = libatrous.get_kernel(i)
            doc += "<li><i>%s:</i> %s</li>" % (KERNEL_CHOICES[i],str(kernel))
        doc += "</ul>"

        self.atrous_choice = cps.Choice(
            "Kernel type:",
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
            doc = doc % globals()
        )

        self.atrous_scalerange = cps.IntegerRange(
           "Band-pass filter width (smallest / largest scale):", (1, 8),
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
        self.atrous_lowpass = cps.Binary(
           "Do you want to include the residual Low Pass image?",
           False,
           doc = """Add the residual Low Pass image to the filtered image.
           """)
        self.atrous_threshold = cps.Binary(
           "Do you want to threshold the output?",
           True,
           doc = """The output image will be thresholded
           """)
        self.atrous_threshrange = cps.FloatRange(
                "Threshold range:", (0, 100), 
           doc="""The lower and upper limits for the threshold range.
           """)
        self.atrous_normalise = cps.Binary(
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
    #
    # visible_settings tells CellProfiler which settings should be
    # displayed and in what order.
    #
    # You don't have to implement "visible_settings" - if you delete
    # visible_settings, CellProfiler will use "settings" to pick settings
    # for display.
    #
    def visible_settings(self):
        self.validate_scales()

        result = [ self.x_name, self.y_name,
                   self.atrous_overide_dimensions ]

        if self.atrous_overide_dimensions:
            result += [self.atrous_xdim, self.atrous_ydim, self.atrous_zdim]

        result += [ self.atrous_choice, self.atrous_scalerange,
                    self.atrous_lowpass,
                    self.atrous_threshold]
        
        #only show the min/max threshold values if threshold is ticked
        if self.atrous_threshold:
            result += [self.atrous_threshrange]

        result += [self.atrous_normalise]
    
        return result

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
        low_thresh,high_thresh = self.atrous_threshrange.value

        low_thresh /= value_max
        high_thresh /= value_max

        #
        # build the output_pixels array iteratively
        #
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
            mi = np.min(output_pixels)
            ma = np.max(output_pixels)
            output_pixels[output_pixels < low_thresh] = low_thresh
            output_pixels[output_pixels > high_thresh] = high_thresh

        #
        # Do we normalise?
        #
        if self.atrous_normalise:
            mi = np.min(output_pixels)
            ma = np.max(output_pixels)
            output_pixels = (output_pixels-mi)/(ma-mi)

        y = cpi.Image(output_pixels, parent_image = x)
        image_set.add(y_name, y)

        #
        # Save intermediate results for display if the window frame is on
        #
        if self.show_window:
            workspace.display_data.x_data = pixels
            workspace.display_data.y_data = output_pixels
            workspace.display_data.dimensions = dimensions

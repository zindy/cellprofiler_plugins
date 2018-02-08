# -*- coding: utf-8 -*-

"""
SaveCroppedObjects
==================

**SaveCroppedObjects** exports each object as a binary image. Pixels corresponding to an exported object are assigned
the value 255. All other pixels (i.e., background pixels and pixels corresponding to other objects) are assigned the
value 0. The dimensions of each image are the same as the original image.

The filename for an exported image is formatted as "{object name}_{label index}_{timestamp}.tiff", where *object name*
is the name of the exported objects, *label index* is the integer label of the object exported in the image (starting
from 1), and *timestamp* is the time at which the image was saved (this prevents accidentally overwriting a previously
exported image).

|

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          NO           NO
============ ============ ===============

"""

import numpy as np
import os.path
import skimage.io
import time

import cellprofiler.image  as cpi
import cellprofiler.module as cpm
import cellprofiler.object as cpo
import cellprofiler.pipeline as cpp
import cellprofiler.setting as cps
import cellprofiler.workspace as cpw
from cellprofiler.setting import YES, NO
import cellprofiler.modules.loadimages
from cellprofiler.modules import _help

IF_SAVEOBJECTS       = "Save Binary Objects"
IF_SAVEIMAGE    = "Save Image Crops"
IF_ALL = [IF_SAVEOBJECTS, IF_SAVEIMAGE]

OF_ALLOBJECTS       = "Save all Objects"
OF_SPARSEOBJECTS       = "Only save Sparse Objects"
OF_ALL = [OF_ALLOBJECTS, OF_SPARSEOBJECTS]

FF_JPEG = "jpeg"
FF_PNG = "png"
FF_TIFF = "tiff"

BIT_DEPTH_8 = "8-bit integer"
BIT_DEPTH_16 = "16-bit integer"
BIT_DEPTH_FLOAT = "32-bit floating point"

PC_WITH_IMAGE = "Same folder as image"


class SaveCroppedObjects(cpm.Module):
    category = "File Processing"

    module_name = "AdvancedSaveCroppedObjects"

    variable_revision_number = 1

    def create_settings(self):
        self.objects_name = cps.ObjectNameSubscriber(
            "Objects",
            doc="Select the objects you want to save."
        )

        self.save_type = cps.Choice(
            "Type of output",
            IF_ALL,
            IF_SAVEOBJECTS,
            doc="""\
Select the type of image to save.\n
The following types of images can be saved as a file on the hard drive:
            """
        )

        self.image_name = cps.ImageNameSubscriber(
            # The text to the left of the edit box
            "Image to crop",
            # HTML help that gets displayed when the user presses the
            # help button to the right of the edit box
            doc = """This is the image the module will cookiecut from. You can
            choose any image that is made available by a prior module.
            """)
        
        self.file_format = cps.Choice(
            "Saved file format",
            [
                FF_TIFF
                FF_PNG,
                FF_JPEG,
            ],
            value=FF_TIFF,
            doc="""\
Select the format to save the image(s).

Only *{FF_TIFF}* supports saving as 16-bit or 32-bit. *{FF_TIFF}* is a
"lossless" file format.

*{FF_PNG}* is also a "lossless" file format and it tends to produce
smaller files without losing any image data.

*{FF_JPEG}* is also small but is a "lossy" file format and should not be
used for any images that will undergo further quantitative analysis.

""".format(**{
                "FF_TIFF": FF_TIFF,
                "FF_PNG": FF_PNG,
                "FF_JPEG": FF_JPEG
            })
        )

        self.objects_type = cps.Choice(
            "Objects filter",
            OF_ALL,
            OF_ALLOBJECTS,
            doc="""\
Select the type of objects to save.\n
The following types of objects can be saved:
            """
        )

        self.border_size = cps.Integer(
"Border size", 1, minval=0, doc="""\
Add a border around each objects
""" % globals())

        self.bit_depth = cps.Choice(
            "Image bit depth",
            [
                BIT_DEPTH_8,
                BIT_DEPTH_16,
                BIT_DEPTH_FLOAT
            ],
            value = BIT_DEPTH_8,
            doc="""\
Select the bit-depth at which you want to save the images.

*{BIT_DEPTH_FLOAT}* saves the image as floating-point decimals with
32-bit precision. When the input data is integer or binary type, pixel
values are scaled within the range (0, 1). Floating point data is not
rescaled.

{BIT_DEPTH_16} and {BIT_DEPTH_FLOAT} images are supported only for
TIFF formats.""".format(**{
                "BIT_DEPTH_FLOAT": BIT_DEPTH_FLOAT,
                "BIT_DEPTH_16": BIT_DEPTH_16
            })
        )

        self.pathname = cps.DirectoryPath(
            "Directory",
            doc="Enter the directory where object crops are saved.",
            value=cps.DEFAULT_OUTPUT_FOLDER_NAME
        )

        self.pathname_with_image = DirectoryPath(
            "Output file location",
            self.image_name,
            doc="""\
This setting lets you choose the folder for the output files.
{IO_FOLDER_CHOICE_HELP_TEXT}

An additional option is the following:

-  *Same folder as image*: Place the output file in the same folder that
   the source image is located.

{IO_WITH_METADATA_HELP_TEXT}

If the subfolder does not exist when the pipeline is run, CellProfiler
will create it.

If you are creating nested subfolders using the sub-folder options, you
can specify the additional folders separated with slashes. For example,
“Outlines/Plate1” will create a “Plate1” folder in the “Outlines”
folder, which in turn is under the Default Input/Output Folder. The use
of a forward slash (“/”) as a folder separator will avoid ambiguity
between the various operating systems.
""".format(**{
                "IO_FOLDER_CHOICE_HELP_TEXT": _help.IO_FOLDER_CHOICE_HELP_TEXT,
                "IO_WITH_METADATA_HELP_TEXT": _help.IO_WITH_METADATA_HELP_TEXT
            })
        )


    def display(self, workspace, figure):
        figure.set_subplots((1, 1))

        figure.subplot_table(0, 0, [["\n".join(workspace.display_data.filenames)]])

    def visible_settings(self):
        settings = [
            self.objects_name, self.save_type
        ]

        if self.save_type.value == IF_SAVEIMAGE:
            settings += [ self.image_name , self.objects_type, self.border_size, self.pathname_with_image ]
        else:
            settings += [ self.pathname ]

        settings += [
            self.file_format,
            self.bit_depth
        ]

        return settings

    def run(self, workspace):
        save_objects = self.save_type.value == IF_SAVEOBJECTS
        save_sparse = self.objects_type.value == OF_SPARSEOBJECTS


        objects = workspace.object_set.get_objects(self.objects_name.value)

        if save_objects:
            directory = self.pathname.get_absolute_path(workspace.measurements)
        else:
            directory = self.pathname_with_image.get_absolute_path(workspace.measurements)

        if not os.path.exists(directory):
            os.makedirs(directory)

        labels = objects.segmented

        unique_labels = np.unique(labels)

        if unique_labels[0] == 0:
            unique_labels = unique_labels[1:]

        filenames = []

        bit_depth = self.get_bit_depth()
        print ">>>",bit_depth
        if not save_objects:
            orig_image = workspace.image_set.get_image(self.image_name.value)

        if save_objects:
            image_id = int(time.time())
        else:
            image_id = workspace.measurements.get_current_measurement('Image', self.file_name_feature)
            image_id, _ = os.path.splitext(image_id)

        print image_id


        border_size = self.border_size.value
        for label in unique_labels:
            mask = labels == label

            #TODO add the filename of the image being cropped
            if save_objects:
                filename = "{}_{:04d}_{}.{}".format(self.objects_name.value, label, image_id, self.get_file_format())
            else:
                filename = "{}_{}_{:04d}.{}".format(image_id, self.objects_name.value, label, self.get_file_format())

            filename = os.path.join(
                directory,
                filename
            )

            if save_objects:
                skimage.io.imsave(filename, skimage.img_as_ubyte(mask))
            else:

                ny, nx = mask.shape
                nzy,nzx = np.nonzero(mask)
                ymin,ymax = np.min(nzy)-border_size,np.max(nzy)+border_size
                xmin,xmax = np.min(nzx)-border_size,np.max(nzx)+border_size

                if ymin < 0: ymin=0
                if ymax > ny-1: ymax = ny-1

                if xmin < 0: xmin=0
                if xmax > nx-1: ymax = nx-1

                pixels = orig_image.pixel_data[ymin:ymax+1,xmin:xmax+1,...]

                if save_sparse:
                    crop_mask = labels[ymin:ymax+1,xmin:xmax+1,...].astype(np.int)

                    v = np.sum(crop_mask,axis=0)
                    if v[0] > 0 or v[-1] > 0:
                        continue

                    v = np.sum(crop_mask,axis=1)
                    if v[0] > 0 or v[-1] > 0:
                        continue

                if bit_depth == BIT_DEPTH_8:
                    pixels  = pixels*255.
                    pixels[pixels<0.] = 0
                    pixels[pixels>255.] =0
                    pixels = skimage.util.img_as_ubyte(pixels.astype(np.uint8))

                elif bit_depth == BIT_DEPTH_16:
                    pixels  = pixels*65535.
                    pixels[pixels<0.] = 0
                    pixels[pixels>65535.] =0
                    pixels = skimage.util.img_as_uint(pixels.astype(np.uint16))
                else:
                    pixels = skimage.util.img_as_float(pixels).astype(numpy.float32)

                skimage.io.imsave(filename, pixels)


            filenames.append(filename)

        if self.show_window:
            workspace.display_data.filenames = filenames

    @property
    def file_name_feature(self):
        return '_'.join((cellprofiler.modules.loadimages.C_FILE_NAME, self.image_name.value))

    def get_file_format(self):
        """Return the file format associated with the extension in self.file_format
        """
        #if self.save_image_or_figure == IF_MOVIE:
        #    return FF_TIFF

        return self.file_format.value

    def get_bit_depth(self):
        if self.get_file_format() == FF_JPEG:
            return BIT_DEPTH_8
        else:
            return self.bit_depth.value

    def settings(self):
        settings = [
            self.objects_name,
            self.save_type,
            self.objects_type,
            self.border_size,
            self.image_name,
            self.file_format,
            self.bit_depth,
            self.pathname,
            self.pathname_with_image
        ]

        return settings

    def volumetric(self):
        return True

class DirectoryPath(cps.DirectoryPath):
    '''A specialized version of DirectoryPath to handle saving in the image dir'''

    def __init__(self, text, file_image_name, doc):
        '''Constructor
        text - explanatory text to display
        file_image_name - the file_image_name setting so we can save in same dir
        doc - documentation for user
        '''
        super(DirectoryPath, self).__init__(
                text, dir_choices=[
                    cps.DEFAULT_OUTPUT_FOLDER_NAME, cps.DEFAULT_INPUT_FOLDER_NAME,
                    PC_WITH_IMAGE, cps.ABSOLUTE_FOLDER_NAME,
                    cps.DEFAULT_OUTPUT_SUBFOLDER_NAME,
                    cps.DEFAULT_INPUT_SUBFOLDER_NAME], doc=doc)
        self.file_image_name = file_image_name

    def get_absolute_path(self, measurements=None, image_set_index=None):
        if self.dir_choice == PC_WITH_IMAGE:
            path_name_feature = "PathName_%s" % self.file_image_name.value
            return measurements.get_current_image_measurement(path_name_feature)
        return super(DirectoryPath, self).get_absolute_path(
                measurements, image_set_index)

    def test_valid(self, pipeline):
        if self.dir_choice not in self.dir_choices:
            raise cps.ValidationError("%s is not a valid directory option" %
                                                       self.dir_choice, self)

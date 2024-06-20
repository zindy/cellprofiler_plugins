import numpy as np
from cellprofiler_core.module.image_segmentation import ImageSegmentation
from cellprofiler_core.setting import Binary
from cellprofiler_core.setting.choice import Choice
from cellprofiler_core.setting.text import Integer
from cellprofiler_core.setting.subscriber import ImageSubscriber, FileImageSubscriber
from cellprofiler_core.object import Objects
import os
from roifile import ImagejRoi, ROI_TYPE



HELP_BINARY_IMAGE = """\
This module loads masks saved in imagej as objects
"""

__doc__ = """\
LoadMaskObjects
=====================

Given an image, **LoadMaskObjects** loads a FIJI/ImageJ ROI file of
the same name but with either as a .zip or a .roi extension and creates
objects. This module is useful for importing regions of interest that
can easily be drawn and saved in FIJI.

{HELP_BINARY_IMAGE}

|

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          YES          NO
============ ============ ===============

""".format(
    **{"HELP_BINARY_IMAGE": HELP_BINARY_IMAGE}
)

OPTION_PRIO_ZIP = "Multi-ROI (.zip) files"
OPTION_PRIO_ROI = "Single ROI (.roi) files"

OPTION_MISSING_FULL = "Output is whole image"
OPTION_MISSING_BLANK = "No object is output"

class LoadMaskObjects(ImageSegmentation):
    category = "Object Processing"

    module_name = "LoadMaskObjects"

    variable_revision_number = 1
   
    def __init__(self):
        print(f"Adding {self.module_name} in \"{self.category}\"")
        super().__init__()

    def create_settings(self):
        super(LoadMaskObjects, self).create_settings()
        
        self.priority_option = Choice(
            "Priority given to",
            [OPTION_PRIO_ZIP, OPTION_PRIO_ROI],
            doc="""\
This helps solving conflicts when both a .zip and a .roi files is found.
You can choose one of the following options:

-  *%(OPTION_PRIO_ZIP)s:* Prioritize .zip files ahead of .roi
-  *%(OPTION_PRIO_ROI)s:* Prioritize .roi files ahead of .zip"""
            % globals(),
        )

        self.missing_option = Choice(
            "If no file is found",
            [OPTION_MISSING_FULL, OPTION_MISSING_BLANK],
            doc="""\
This defines the behavior when no file is found.
You can choose one of the following options:

-  *%(OPTION_MISSING_FULL)s:* An object will be generated to cover the whole image.
-  *%(OPTION_MISSING_BLANK)s:* No objects will be output."""
            % globals(),
        )

        self.wants_single_label = Binary(
            "Single label output?",
            False,
            doc="""\
Select *Yes* to give multiple objects the same label.

By default, if multiple ROIs are read from a zip file, each is given
its own label."""
            % globals(),
        )

    def settings(self):
        __settings__ = super(LoadMaskObjects, self).settings()
        return __settings__ + [self.priority_option, self.missing_option, self.wants_single_label]

    def visible_settings(self):
        __settings__ = super(LoadMaskObjects, self).visible_settings()
        return __settings__ + [self.priority_option, self.missing_option, self.wants_single_label]

    def run(self, workspace):
        x_name = self.x_name.value
        y_name = self.y_name.value

        priority_zip = self.priority_option == OPTION_PRIO_ZIP
        missing_is_blank = self.missing_option == OPTION_MISSING_BLANK
        single_label = self.wants_single_label.value

        #Here we get the input image dimensions
        images = workspace.image_set
        x = images.get_image(x_name)
        x_data = x.pixel_data
        dimensions = x.dimensions
        shape = x_data.shape

        #Here we get the absolute path of the image
        measurements = workspace.measurements

        name_feature = "PathName_%s" % x_name
        x_path = measurements.get_current_image_measurement(name_feature)

        name_feature = "FileName_%s" % x_name
        x_filename = measurements.get_current_image_measurement(name_feature)

        y_data = load_masks(
                os.path.join(x_path, x_filename) , shape,
                priority_zip=priority_zip, missing_is_blank=missing_is_blank,
                single_label=single_label)

        y = Objects()
        y.segmented = y_data
        y.parent_image = x.parent_image

        objects = workspace.object_set
        objects.add_objects(y, y_name)

        self.add_measurements(workspace)

        if self.show_window:
            workspace.display_data.x_data = x_data

            workspace.display_data.y_data = y_data

            workspace.display_data.dimensions = dimensions


    def display(self, workspace, figure):
        layout = (2, 1)

        figure.set_subplots(
            dimensions=workspace.display_data.dimensions, subplots=layout
        )

        figure.subplot_imshow(
            colormap="gray",
            image=workspace.display_data.x_data,
            title=self.x_name.value,
            x=0,
            y=0,
        )

        figure.subplot_imshow_labels(
            image=workspace.display_data.y_data,
            sharexy=figure.subplot(0, 0),
            title=self.y_name.value,
            x=1,
            y=0,
        )


# https://stackoverflow.com/questions/3654289/scipy-create-2d-polygon-mask
def create_polygon(shape,poly_verts):
    from matplotlib.path import Path

    #FIXME Assumes 2-D array...
    ny,nx = shape

    # Create vertex coordinates for each grid cell...
    # (<0,0> is at the top left of the grid in this system)
    x, y = np.meshgrid(np.arange(nx), np.arange(ny))
    x, y = x.flatten(), y.flatten()

    points = np.vstack((x,y)).T

    path = Path(poly_verts)
    grid = path.contains_points(points)

    grid = grid.reshape((ny,nx))

    return grid


def load_masks(filename, dimensions, priority_zip=True, missing_is_blank=False, single_label=False):

    data = np.zeros(dimensions, dtype=int)

    #Strip the extension, we'll check if there is a zip or a roi...
    filename = os.path.splitext(filename)[0]

    search_list = [filename+'.zip', filename+'.roi']
    if priority_zip == False:
        search_list = search_list[::-1]

    roi_list = None
    for fn in search_list:
        print(f"Opening {fn}")
        if os.path.exists(fn):
            roi_list = ImagejRoi.fromfile(fn)
            if type(roi_list) is not list:
                roi_list = [roi_list]

            #Data was loaded from the prioritized file, can break now.
            break

    if roi_list is None:
        # Here we check the value of missing_is_blank
        if missing_is_blank == False:
            data = np.ones(dimensions, dtype=int)
        return data

    # Now we can look through the rois:
    for i, roi in enumerate(roi_list):
        if roi.roitype in [ROI_TYPE.POLYGON, ROI_TYPE.FREEHAND, ROI_TYPE.OVAL, ROI_TYPE.RECT]:
            print(f"ROI {i+1}: {roi.name} - {roi.roitype}")
            vertices = roi.coordinates()
            label = 1 if single_label == True else i+1
            data = np.where( create_polygon(dimensions,vertices), label, data)
        else:
            print(f"ROI {i+1}: {roi.name} - Type not implemented {roi.roitype}")
            print(roi)

    return data

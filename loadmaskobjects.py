import numpy as np
from cellprofiler_core.module.image_segmentation import ImageSegmentation
from cellprofiler_core.setting import Binary
from cellprofiler_core.setting.text import Integer
from cellprofiler_core.setting.subscriber import ImageSubscriber, FileImageSubscriber
from cellprofiler_core.object import Objects
import os
import read_roi


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


class LoadMaskObjects(ImageSegmentation):
    category = "Object Processing"

    module_name = "LoadMaskObjects"

    variable_revision_number = 1

    def create_settings(self):
        super(LoadMaskObjects, self).create_settings()

    def settings(self):
        __settings__ = super(LoadMaskObjects, self).settings()
        return __settings__

    def visible_settings(self):
        __settings__ = super(LoadMaskObjects, self).visible_settings()
        return __settings__

    def run(self, workspace):
        x_name = self.x_name.value
        y_name = self.y_name.value

        #Here we get the input image dimensions
        images = workspace.image_set
        x = images.get_image(x_name)
        x_data = x.pixel_data
        dimensions = x.dimensions
        shape = x_data.shape
        print(dimensions, shape)

        #Here we get the absolute path of the image
        measurements = workspace.measurements

        name_feature = "PathName_%s" % x_name
        x_path = measurements.get_current_image_measurement(name_feature)

        name_feature = "FileName_%s" % x_name
        x_filename = measurements.get_current_image_measurement(name_feature)

        y_data = load_masks(
                os.path.join(x_path, x_filename) , shape)

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


def load_masks(filename, dimensions):
    data = np.zeros(dimensions, dtype=int)

    #Strip the extension, we'll check if there is a zip or a roi...
    filename = os.path.splitext(filename)[0]

    if os.path.exists(filename+'.zip'):
        dic_roi = read_roi.read_roi_zip(filename+'.zip')
    elif os.path.exists(filename+'.roi'):
        dic_roi = read_roi.read_roi_file(filename+'.roi')
    else:
        # TODO what to do if can't find a ROI file?
        # have a flag to whether to return an empty or a full image mask
        # for now, return a full image mask
        data = np.ones(dimensions, dtype=int)
        return data

    for i, (k,r) in enumerate(dic_roi.items()):
        if r['type'] == 'polygon':
            x = r['x']
            y = r['y']
        elif r['type'] == 'oval':
            #'oval', 'left': 53, 'top': 237, 'width': 762, 'height': 739,
            yc = r['top']+r['height']/2.
            xc = r['left']+r['width']/2.
            ir = np.arange(0,2*np.pi,2*np.pi/100.)
            x = r['width']/2.*np.cos(ir)+xc
            y = r['height']/2.*np.sin(ir)+yc
        else:
            print(f"  Could not process {r}: {r['type']}")
            continue

        vertices = np.vstack([x,y]).T
        data = np.where( create_polygon(dimensions,vertices), i+1, data)

    return data



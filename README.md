# cellprofiler_plugins
My CellProfiler plugins.

* "AtrousFilter" is described here (for now): http://forum.cellprofiler.org/t/a-trous-filter-module-for-cellprofiler/5111 .
The filter uses [libatrous](https://github.com/zindy/libatrous). The CP3.0 version works with both 2-D and 3-D objects.

* "Reload" is described in https://groups.google.com/a/broadinstitute.org/forum/#!msg/cellprofiler-dev/Jt2EQOxAcJc/LMGFsbb3h6kJ -- I think there's an issue with modules using super(), in which case reloading the pipeline leads to some errors. If I ever get to the bottom of this, I'll report back.

* "AdvancedSaveCroppedObjects" cuts objects from an image and saves the cropped images separately.



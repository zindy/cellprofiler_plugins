import cellprofiler_core.module as cpm
import cellprofiler_core.pipeline as cpp
from cellprofiler_core.setting.do_something import DoSomething


__doc__ = """\
CellProfilerReload
============
**CellProfilerReload** can be used for reloading all the CellProfiler modules.

All credit and copyright Lee Kamentsky

Code (poorly) maintained by Egor Zindy at https://github.com/zindy/cellprofiler_plugins


References
^^^^^^^^^^

Lee Kamentsky says: I tried Ray's suggestion out with the release version of CellProfiler.
I put in a couple tweaks, including getting wx to run the reloading outside of the module code. It works -
you have to reload your pipeline afterwards or delete and reinsert the module to see the changes.

The attached module is what I came up with...
https://groups.google.com/a/broadinstitute.org/forum/#!msg/cellprofiler-dev/Jt2EQOxAcJc/LMGFsbb3h6kJ

|

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          YES           YES
============ ============ ===============

"""

class CellProfilerReload(cpm.Module):

    module_name = "CellProfilerReload"
    category = "Other"
    variable_revision_number = 1

    def __init__(self):
        print(f"Adding {self.module_name} in \"{self.category}\"")
        super().__init__()

    def create_settings(self):
        self.reload_button = DoSomething(
            "Reload modules", "Reload", self.do_reload)
        self.pipeline = None

    def do_reload(self):
        import wx
        if isinstance(self.pipeline, cpp.Pipeline):
            print("Reloading modules...")
            wx.CallAfter(self.pipeline.reload_modules)
            
    def settings(self):
        return [self.reload_button]

    def visible_settings(self):
        return [self.reload_button]

    def validate_module(self, pipeline):
        self.pipeline = pipeline

    def run(self, workspace):
        pass
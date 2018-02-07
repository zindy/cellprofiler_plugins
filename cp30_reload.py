# All credit and copyright Lee Kamentsky:
#
# I tried Ray's suggestion out with the release version of CellProfiler.
# I put in a couple tweaks, including getting wx to run the reloading outside of the module code. It works -
# you have to reload your pipeline afterwards or delete and reinsert the module to see the changes.
#
# The attached module is what I came up with...
# https://groups.google.com/a/broadinstitute.org/forum/#!msg/cellprofiler-dev/Jt2EQOxAcJc/LMGFsbb3h6kJ
#
# Adapted for CP30 (Egor Zindy)

import cellprofiler.module as cpm
import cellprofiler.pipeline as cpp
import cellprofiler.setting as cps

class Reload(cpm.Module):
    variable_revision_number = 1
    module_name = "Reload"
    category = "Other"
    
    def create_settings(self):
        self.reload_button = cps.DoSomething(
            "Reload modules", "Reload", self.do_reload)
        self.pipeline = None
        
    def do_reload(self):
        import wx
        import cellprofiler.pipeline as cpp
        
        if isinstance(self.pipeline, cpp.Pipeline):
            print("Reloading modules...")
            wx.CallAfter(self.pipeline.reload_modules)
            
    def settings(self):
        return []
    
    def visible_settings(self):
        return [self.reload_button]
    
    def run(self, workspace):
        pass
    
    def validate_module(self, pipeline):
        self.pipeline = pipeline

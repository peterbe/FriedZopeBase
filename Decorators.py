import os
from Products.PageTemplates.PageTemplateFile import PageTemplateFile as ZPageTemplateFile
class PageTemplateFile(ZPageTemplateFile):
    
    def _exec(self, bound_names, args, kw):
        extra_kw = self.view_wrapper_function(self, self.REQUEST)
        if isinstance(extra_kw, dict):
            extra_kw.pop('self')
            extra_kw.pop('REQUEST')
            kw.update(extra_kw)
        return super(PageTemplateFile, self)._exec(bound_names, args, kw)
    
    

class zpt_function:
    """
    Use like this:
        @zpt_function(MyClass, 'foo.zpt', globals())
        def my_dashboard(self, REQUEST):
            variable = 123
            return locals()
    """
    def __init__(self, host_object, template, globals, name=None, **kwargs):
        self.host_object = host_object
        self.template = template
        self.name = name
        self.globals = globals
        
    def __call__(self, func, *a, **kw):
        if self.name:
            name = self.name
        else:
            name = func.func_name
        pt = PageTemplateFile(self.template, self.globals,
                                   __name__=name)
        pt.view_wrapper_function = func
        setattr(self.host_object, name, pt)

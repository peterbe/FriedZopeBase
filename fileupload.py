# -*- coding: iso-8859-1 -*
##
## FriedZopeBase
## (c) Fry-IT, www.fry-it.com
## <peter@fry-it.com>
##
import os


class NewFileUpload:
    """
    This class makes it easy and possible to 'fake' uploading
    files from code that doesn't use the ZPublisher.
    """
    
    def __init__(self, file_path, selfdestruct=True):
        self.file = open(file_path, 'rb')
        self.filename = os.path.basename(file_path)
        self.file_path = file_path
        self.selfdestruct = selfdestruct
        
    def read(self, bytes=None):
        import stat
        print os.stat(self.file_path)[stat.ST_SIZE]
        if bytes:
            return self.file.read(bytes)
        else:
            return self.file.read()

    def seek(self, offset, whence=0):
        self.file.seek(offset, whence)
    
    def __del__(self):
        if self.selfdestruct:
            if os.path.isfile(self.file_path):
                os.remove(self.file_path)
            
    def tell(self):
        return self.file.tell()

            
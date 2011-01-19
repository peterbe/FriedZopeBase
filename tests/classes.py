# -*- coding: iso-8859-1 -*
##
## unittest Bases
## (c) Fry-IT, www.fry-it.com
## <peter@fry-it.com>
##

from Globals import SOFTWARE_HOME    
from Testing import ZopeTestCase



ZopeTestCase.installProduct('FriedZopeBase')


#------------------------------------------------------------------------------
#
# Some constants
#

#------------------------------------------------------------------------------


# Open ZODB connection
app = ZopeTestCase.app()
        
# Set up sessioning objects
ZopeTestCase.utils.setupCoreSessions(app)
        
# Set up example applications
#if not hasattr(app, 'Examples'):
#    ZopeTestCase.utils.importObjectFromFile(app, examples_path)
        
# Close ZODB connection
ZopeTestCase.close(app)
        
    
#------------------------------------------------------------------------------


class TestBase(ZopeTestCase.ZopeTestCase):

    def dummy_redirect(self, *a, **kw):
        self.has_redirected = a[0]
        if kw:
            print "*** Redirecting to %r + (%s)" % (a[0], kw)
        else:
            print "*** Redirecting to %r" % a[0]
    
    def afterSetUp(self):
        #dispatcher = self.folder.manage_addProduct['MExpenses']
        #dispatcher.manage_addHomepage('mexpenses')
        #self.mexpenses = self.folder['mexpenses']
        #self.mexpenses.http_redirect = self.dummy_redirect
        self.has_redirected = False
        
    def _prepareSessionManager():
        request = self.app.REQUEST
        sdm = self.app.session_data_manager
        request.set('SESSION', sdm.getSessionData())
        
        


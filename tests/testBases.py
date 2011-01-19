# -*- coding: iso-8859-1 -*
##
## unittest Bases
## (c) Fry-IT, www.fry-it.com
## <peter@fry-it.com>
##

import cgi
from sets import Set
import cStringIO
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))
    

from classes import TestBase

from Products.FriedZopeBase.Bases import HomepageBase

class TestBases(TestBase):
    
    def test_getDomainCookie(self):
        x = HomepageBase()
        x.REQUEST = self.app.REQUEST
        
        x.REQUEST.URL = 'http://www.mobilexpenses.com'
        self.assertEqual(x._getCookieDomain(), '.mobilexpenses.com')
        
        x.REQUEST.URL = 'http://www.mobilexpenses.com'
        self.assertEqual(x._getCookieDomain(), '.mobilexpenses.com')
        
        x.REQUEST.URL = 'http://127.0.0.1:8080/foo/bar.html'
        self.assertEqual(x._getCookieDomain(), None)
        
        x.REQUEST.URL = 'http://www.mobilexpenses.com/foo/bar.html'
        self.assertEqual(x._getCookieDomain(), '.mobilexpenses.com')
        
        x.REQUEST.URL = 'http://www.mobilexpenses.co.uk/foo/bar.html'
        self.assertEqual(x._getCookieDomain(), '.mobilexpenses.co.uk')
        
        x.REQUEST.URL = 'http://www.mobile.expenses.com/foo/bar.html'
        self.assertEqual(x._getCookieDomain(), '.mobile.expenses.com')
        
        x.REQUEST.URL = 'http://www.mobile.expenses.co.uk/foo/bar.html'
        self.assertEqual(x._getCookieDomain(), '.mobile.expenses.co.uk')
        
        x.REQUEST.URL = 'http://mobilexpenses.co.uk/foo/bar.html'
        self.assertEqual(x._getCookieDomain(), None)
        
        x.REQUEST.URL = 'http://mobilexpenses.com/foo/bar.html'
        self.assertEqual(x._getCookieDomain(), None)

        
    def dummy_redirect(self, *a, **kw):
        self.last_redirect = a[0]
        #if kw:
        #    print "*** Redirecting to %r + (%s)" % (a[0], kw)
        #else:
        #    print "*** Redirecting to %r" % a[0]
            
    def test_http_redirect(self):
        """ test http_redirect() """
        hb = HomepageBase()
        hb.REQUEST = self.app.REQUEST
        hb.REQUEST.RESPONSE.redirect = self.dummy_redirect
        func = hb.http_redirect
        
        
        
        func('bajs', **{'balle':'fjong'})
        self.assertEqual(self.last_redirect.split('/')[-1], 
                         'bajs?balle=fjong')
                         
     
        func('bajs#anchor', **{'balle':'fjong'})
        self.assertEqual(self.last_redirect.split('/')[-1], 
                         'bajs?balle=fjong#anchor')
                         
        func('%s/#anchor' % self.app.absolute_url(), **{'balle':'fjong'})
        self.assertEqual(self.last_redirect,
                         '%s/?balle=fjong#anchor' % self.app.absolute_url())
        
                         
        func('/GKM/Tavlor-se/MAGIK#fm-12', **{'success':'balle fjong'})
        expect = 'http://nohost/GKM/Tavlor-se/MAGIK?success=balle+fjong#fm-12'
        self.assertEqual(self.last_redirect, expect)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestBases))
    return suite

if __name__ == '__main__':
    framework()

    
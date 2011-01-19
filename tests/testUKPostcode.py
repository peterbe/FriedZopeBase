# -*- coding: iso-8859-1 -*

"""FriedZopeBase Utils ZopeTestCase
"""
import os, re, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))
    
from classes import TestBase

from Products.FriedZopeBase import ukpostcode

class TestUKPostcode(TestBase):
    """
    the file ukpostcode.py has its own unit tests but including them 
    here is a good idea so that it's tested with the rest of FriedZopeBase
    which will make sure it imports properly and continues to work.
    """
    
    def test_valid_uk_postcode(self):
        yes = ('se19pg','e1 6jx', )
        no = ('se1', '', '123123123123','se1 kkk')
        for each in yes:
            self.assertTrue(ukpostcode.valid_uk_postcode(each))
        for each in no:
            self.assertTrue(not ukpostcode.valid_uk_postcode(each))
            
    def test_format_uk_postcode(self):
        func = ukpostcode.format_uk_postcode
        self.assertEqual(func('e16jx'), 'E1 6JX')
        self.assertEqual(func('s e 1 9 p g'), 'SE1 9PG')
        
    

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestUKPostcode))
    return suite

if __name__ == '__main__':
    framework()

    
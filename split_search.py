#-*- coding: iso-8859-1 -*
## 
## Split search string - Useful when building advanced search application
## By: Peter Bengtsson, mail@peterbe.com
## May 2008
## ZPL
##

__version__='1.0'

"""

split_search(searchstring [str or unicode], 
                      keywords [list or tuple])
                      
  Splits the search string into a free text part and a dictionary of keyword 
  pairs. For example, if you search for 'Something from: Peter to: Lukasz' 
  this function will return 
  'Something', {'from':'Peter', 'to':'Lukasz'}
  
  It works equally well with unicode strings.
  
  Any keywords in the search string that isn't recognized is considered text.
  
"""

import re


def split_search(q, keywords):
    params = {}
    s = []
    
    regex = re.compile(r'\b(%s):' % '|'.join(keywords), re.I)
    bits = regex.split(q)
    
    skip_next = False
    for i, bit in enumerate(bits):
        if skip_next:
            skip_next = False
        else:
            if bit in keywords:
                params[bit.lower()] = bits[i+1].strip()
                skip_next = True
            elif bit.strip():
                s.append(bit.strip())
                
    return ' '.join(s), params

if __name__=='__main__':
    import unittest
    class Test(unittest.TestCase):
        
        def test_basic(self):
            """ one free text part, two keywords """
            keywords = ('to','from')
            q = "Peter something to:AAa aa from:Foo bar"
            s, params = split_search(q, keywords)
            self.assertEqual(s, 'Peter something')
            self.assertEqual(params, {'to': 'AAa aa', 'from': 'Foo bar'})
            
        def test_unrecognized_keywords(self):
            """ free text and keywords we don't support """
            keywords = ('something','else')
            q = "Free text junk: Aaa aaa foo:bar"
            s, params = split_search(q, keywords)
            self.assertEqual(s, q)
            self.assertEqual(params, {})
            
        def test_unrecognized_and_recognized_keywords(self):
            """ free text and keywords we don't support """
            keywords = ('something','else','name')
            q = "Free text junk: something else name: peter"
            s, params = split_search(q, keywords)
            self.assertEqual(s, 'Free text junk: something else')
            self.assertEqual(params, {'name': 'peter'})
            
        def test_empty_keyword_value(self):
            """ free text and an empty keyword """
            keywords = ('to',)
            q = "Naughty parameter to:"
            s, params = split_search(q, keywords)
            self.assertEqual(s, "Naughty parameter")
            self.assertEqual(params, {'to':''})
            
        def test_unicode_string(self):
            """ test with unicode string input """
            keywords = ('from','to')
            q = u"\xa1 to:\xa2 from:\xa3"
            s, params = split_search(q, keywords)
            self.assertEqual(s, u'\xa1')
            self.assertEqual(params, {u'to': u'\xa2', u'from': u'\xa3'})
            
    def suite():
        return unittest.makeSuite(Test)

    unittest.main()

        

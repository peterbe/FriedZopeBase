# -*- coding: iso-8859-1 -*

"""FriedZopeBase Utils ZopeTestCase
"""
import os, re, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))
    
from classes import TestBase

from Products.FriedZopeBase.Input import InputWidgets
from Products.FriedZopeBase.Input import InputwidgetTypeError, InputwidgetValueError, InputwidgetNameError



class TestInput(TestBase):
          
    def assertEqualLongString(self, a, b):
        NOT, POINT = '-', '*'
        if a != b:
            print a
            o = ''
            for i, e in enumerate(a):
                try:
                    if e != b[i]:
                        o += POINT
                    else:
                        o += NOT
                except IndexError:
                    o += '*'

            o += NOT * (len(a)-len(o))
            if len(b) > len(a):
                o += POINT* (len(b)-len(a))

            print o
            print b

            raise AssertionError, '(see string comparison above)'
            
    
    def test_inputwidget(self):
        """ test the basic inputwidget() method that returns a piece of HTML
        of the input thing. """
        
        iw = InputWidgets()
        iw.REQUEST = self.app.REQUEST
        func = iw.inputwidget
        
        html = func('name')
        expect = '<input type="text" id="id_name" name="name" value="" />'
        self.assertEqual(html, expect)
        
        html = func('name', 'value')
        expect = '<input type="text" id="id_name" name="name" value="value" />'
        self.assertEqual(html, expect)

        # try setting the value in the REQUEST
        self.app.REQUEST.set('name','value')
        html = func('name')
        expect = '<input type="text" id="id_name" name="name" value="value" />'
        self.assertEqual(html, expect)
        
        html = func('name:latin1:ustring', u'Sm\xa3')
        expect = u'<input type="text" id="id_name" name="name:latin1:ustring" value="Sm\xa3" />'
        self.assertEqual(html, expect)        
        
        # let's complicate things with different type_
        html = func('name', 'value', type_='hidden')
        expect = '<input type="hidden" id="id_name" name="name" value="value" />'
        self.assertEqual(html, expect)

        html = func('name', 'value', type_='password')
        expect = '<input type="password" id="id_name" name="name" value="value" />'
        self.assertEqual(html, expect)
        
        html = func('name', 'value', type_='file')
        expect = '<input type="file" id="id_name" name="name" value="value" />'
        self.assertEqual(html, expect)
        
        html = func('name', 'value', type_='textarea')
        expect = '<textarea name="name" id="id_name" rows="10" cols="70">value</textarea>'
        self.assertEqual(html, expect)
        
        # try setting an unrecognized type_
        self.assertRaises(InputwidgetTypeError, func, 'name', type_='junk')
        
        # the name can't be padded with whitespace
        self.assertRaises(InputwidgetNameError, func, 'name ',)
        # and it can't obviously be blank
        self.assertRaises(InputwidgetNameError, func, '',)

        # use the type_ to guess the value from the REQUEST
        self.app.REQUEST.set('name','value')
        html = func('name', self.app.REQUEST )
        expect = '<input type="text" id="id_name" name="name" value="value" />'
        self.assertEqual(html, expect)
        self.app.REQUEST.set('name', None)
        
        # if you want to use the radio type, make sure the value isn't a list
        self.assertRaises(InputwidgetValueError, func, 'name', [1,2], type_='radio')

        # and you can't have multiple for radio inputs
        self.assertRaises(InputwidgetTypeError, func, 'name', 'value', type_='radio', multiple='multiple')
        
        # a luxury, if the value is an integer and as a string little,
        # then it automatically sets the size=5
        html = func('name', 123,)
        expect = '<input type="text" id="id_name" name="name" value="123" size="5" />'
        self.assertEqual(html, expect)
        
        # if the type is checkbox, convert it to value 1 and use checked or not 
        html = func('name', True, type_='checkbox')
        expect = '<input type="checkbox" id="id_name" name="name" value="1" checked="checked" />'
        self.assertEqual(html, expect)
        
        # suppose there is a 'submiterrors' in REQUEST with this name
        submiterrors={'name':u"Bad input!", 'other':'junk'}
        self.app.REQUEST.set('submiterrors', submiterrors)
        html = func('name', 'value')
        expect = u'<input type="text" id="id_name" name="name" value="value" class="inputerror" />'\
                 '<span class="submiterror">Bad input!</span><br/>'
        self.assertEqual(html, expect)
        self.app.REQUEST.set('submiterrors', {})

        # set the class_ 
        html = func('name', class_='koko')
        expect = '<input type="text" id="id_name" name="name" value="" class="koko" />'
        self.assertEqual(html, expect)

        html = func('name', class_=['ko','ku'])
        expect = '<input type="text" id="id_name" name="name" value="" class="ko ku" />'
        self.assertEqual(html, expect)
        
        # if you provide a list of options and don't explicitly set 
        # the type to be radio, then make it a select input.
        html = func('name', options=['a','b'])
        expect = u'<select name="name" id="id_name">\n'\
                  '<option value="a">a</option>\n'\
                  '<option value="b">b</option>\n'\
                  '</select>'
        self.assertEqual(html, expect)
        
        html = func('name', 'b', options=['a','b'])
        expect = u'<select name="name" id="id_name">\n'\
                  '<option value="a">a</option>\n'\
                  '<option value="b" selected="selected">b</option>\n'\
                  '</select>'
        #self.assertEqual(html, expect)
        self.assertEqualLongString(html, expect)
        
        html = func('name', ['b','a'], options=['a','b','c'], multiple=1)
        expect = u'<select name="name" id="id_name" multiple="multiple">\n'\
                  '<option value="a" selected="selected">a</option>\n'\
                  '<option value="b" selected="selected">b</option>\n'\
                  '<option value="c">c</option>\n'\
                  '</select>'
        self.assertEqual(html, expect)
        
        # test the posttext thing
        html = func('name', 'value', posttext=u'\xa3')
        expect = u'<input type="text" id="id_name" name="name" value="value" />'\
                 u'<span class="input-posttext">\xa3</span>'
        self.assertEqual(html, expect)
        
        # a radio input
        html = func('name', 'b', options=['a','b'], type_='radio')
        expect = u'<input type="radio" name="name" id="id_name_0" value="a" />'\
                 u'<label style="display:inline" for="id_name_0">a</label><br/><input type="radio" name="name" '\
                 u'id="id_name_1" value="b" checked="checked" /><label style="display:inline" for="id_name_1">b</label><br/>'
        self.assertEqualLongString(html, expect)
        
        # a radio input with extra keywords
        html = func('name', 'b', options=['a','b'], type_='radio', class_='fmradio')
        expect = u'<input type="radio" name="name" id="id_name_0" value="a" class="fmradio" />'\
                 u'<label style="display:inline" for="id_name_0">a</label><br/><input type="radio" name="name" '\
                 u'id="id_name_1" value="b" checked="checked" class="fmradio" /><label style="display:inline" for="id_name_1">b</label><br/>'
        self.assertEqual(html, expect)
        
        
        html = func('name', 2, options=[1,2,3])
        expect = u'<select name="name" id="id_name">\n'\
                  '<option value="1">1</option>\n'\
                  '<option value="2" selected="selected">2</option>\n'\
                  '<option value="3">3</option>\n'\
                  '</select>'
        self.assertEqual(html, expect)
        
        # now the value is actually different from the options
        html = func('name', '2', options=[1,2,3])
        expect = u'<select name="name" id="id_name">\n'\
                  '<option value="1">1</option>\n'\
                  '<option value="2">2</option>\n'\
                  '<option value="3">3</option>\n'\
                  '</select>'
        self.assertEqual(html, expect)
        
        # with the special keyword 'careful_int_match__' it can work
        html = func('name', '2', options=[1,2,3], careful_int_match__=True)
        expect = u'<select name="name" id="id_name">\n'\
                  '<option value="1">1</option>\n'\
                  '<option value="2" selected="selected">2</option>\n'\
                  '<option value="3">3</option>\n'\
                  '</select>'
        self.assertEqual(html, expect)
        
        
        # this time, the value can't even be converted to an int
        html = func('name', 'x', options=[1,2,3], careful_int_match__=True)
        expect = u'<select name="name" id="id_name">\n'\
                  '<option value="1">1</option>\n'\
                  '<option value="2">2</option>\n'\
                  '<option value="3">3</option>\n'\
                  '</select>'
        self.assertEqual(html, expect)        
        
        # the same but for radio
        html = func('name', '2', options=[1,2], type_='radio',
                    careful_int_match__=True)
        expect = u'<input type="radio" name="name" id="id_name_0" value="1" />'\
                 u'<label style="display:inline" for="id_name_0">1</label><br/>'\
                 u'<input type="radio" name="name" id="id_name_1" value="2" '\
                 u'checked="checked" /><label '\
                 u'style="display:inline" for="id_name_1">2</label><br/>'
        self.assertEqualLongString(html, expect)
        
        
        

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestInput))
    return suite

if __name__ == '__main__':
    framework()


    

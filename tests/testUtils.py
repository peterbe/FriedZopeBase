# -*- coding: iso-8859-1 -*

"""FriedZopeBase Utils ZopeTestCase
"""
import os, re, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))
    
from classes import TestBase

from Products.FriedZopeBase import Utils

class TestUtils(TestBase):

    def test_http_redirect(self):
        """ test http_redirect """
        pass
    
    def test_highlightQ(self):
        """ test highlightQ """
        func = Utils.highlightQ
        expect = 'The <span class="highlight">Peter</span> is here'
        self.assertEqual(func('peter','The Peter is here'), expect)

        expect = 'The **Peter** is here'
        self.assertEqual(func('peter','The Peter is here',
                              template='**%s**'), 
                         expect)
                         
        expect = u'så <span class="highlight">Peter</span> is here'
        self.assertEqual(func('peter', u'så Peter is here'), expect)
        
    def test_html_entity_fixer(self):
        """ test html_entity_fixer """
        func = Utils.html_entity_fixer
        
        x = "ö £"
        self.assertEqual(func(x), '&ouml; &pound;')
        
        x = u"ö £"
        self.assertEqual(func(x), '&#246; &#163;')
        
    def test_LineIndent(self):
        func = Utils.LineIndent
        
        x = 'This is a message ' * 10
        y = func(x, '\t')
        self.assertEqual(y, '\t' + x)
        
        x = 'This is a message ' * 10
        y = func(x, '\t', maxwidth=50)
        self.assertEqual(y, '\tThis is a message This is a message This is a\n'\
                            '\tmessage This is a message This is a message This\n'\
                            '\tis a message This is a message This is a message\n'\
                            '\tThis is a message This is a message')
        
        x = u'This is å message ' * 10
        y = func(x, '\t', maxwidth=50)
        self.assertEqual(y, u'\tThis is å message This is å message This is å\n'\
                            u'\tmessage This is å message This is å message This\n'\
                            u'\tis å message This is å message This is å message\n'\
                            u'\tThis is å message This is å message')
                         
                            
    def test_tex_quote(self):
        func = Utils.tex_quote
        x = func('Simple')
        y = 'Simple'
        self.assertEqual(x, y)
        
        x = func('Simple & Poor')
        y = 'Simple \& Poor'
        self.assertEqual(x, y)
        
        x = func('Simple & Poor $10 dot_com 10% less | grep number #10 2^10 in /~guido')
        y = r'Simple \& Poor \$10 dot\_com 10\% less \textbackslash grep number \#10 2\^{}10 in /\~{}guido'
        self.assertEqual(x, y)        

    
    def test_hasExternalProgram(self):
        """ test hasExternalProgram """
        func = Utils.hasExternalProgram
        x = func('less')
        y = True
        self.assertEqual(x, y)
        
        x = func('apdijaeifj')
        y = False
        self.assertEqual(x, y)
        
        x = func('unzip')
        y = os.path.isfile('/usr/bin/unzip')
        self.assertEqual(x, y)
        
        x = func('pdflatex')
        y = os.path.isfile('/usr/bin/pdflatex')
        self.assertEqual(x, y)
        
        x = func('witch')
        y = os.path.isfile('/usr/bin/witch')
        self.assertEqual(x, y)
        
        x = func('dot')
        y = os.path.isfile('/usr/bin/dot')
        self.assertEqual(x, y)
        
        
    def test_parametrize_url(self):
        """ test parametrize_url() """
        func = Utils.parametrize_url
        
        url = 'http://www.peterbe.com'
        params = {'a':'A', 'b':'B'}
        y = 'http://www.peterbe.com/?a=A&b=B'
        self.assertEqual(func(url, **params), y)
        
        url = 'http://www.peterbe.com/'
        params = {'a':'A', 'b':'B'}
        y = 'http://www.peterbe.com/?a=A&b=B'
        self.assertEqual(func(url, **params), y)
        
        url = 'http://www.peterbe.com?x=X'
        params = {'a':'A', 'b':'B'}
        y = 'http://www.peterbe.com/?x=X&a=A&b=B'
        self.assertEqual(func(url, **params), y)        
        
        url = 'http://www.peterbe.com/page.html'
        params = {'a':'A', 'b':'B'}
        y = 'http://www.peterbe.com/page.html?a=A&b=B'
        self.assertEqual(func(url, **params), y)
        
        url = 'http://www.peterbe.com/page.html?c=C'
        params = {'a':'A', 'b':'B'}
        y = 'http://www.peterbe.com/page.html?c=C&a=A&b=B'
        self.assertEqual(func(url, **params), y)
        
        url = 'http://www.peterbe.com/page.html?c=C&d=D'
        params = {'a':'A', 'b':'B'}
        y = 'http://www.peterbe.com/page.html?c=C&d=D&a=A&b=B'
        self.assertEqual(func(url, **params), y)
        
        url = 'http://www.peterbe.com'
        params = {'letters':('A','B')}
        y = 'http://www.peterbe.com/?letters=A&letters=B'
        self.assertEqual(func(url, doseq=True, **params), y)
        
        params = {'a':u'A', 'b':u'B'}
        y = 'http://www.peterbe.com/?a=A&b=B'
        self.assertEqual(func(url, **params), y)
        
        params = {'a':u'\xc3\xa5', 'o':u'\xc3\xb6'}
        y = 'http://www.peterbe.com/?a=%C3%83%C2%A5&o=%C3%83%C2%B6'
        self.assertEqual(func(url, unicode_encoding='utf-8', **params), y)
        
    def test_environment_variable_functions(self):
        os.environ['NAME'] = 'Peter'
        self.assertEqual(Utils.getEnvStr('NAME', 'Default'), 'Peter')
        
        self.assertEqual(Utils.getEnvStr('ZAHXSF','Default'), 'Default')
        
        os.environ['AGE'] = '27'
        self.assertEqual(Utils.getEnvInt('AGE', 28), 27)
        self.assertEqual(Utils.getEnvInt('KILOS', 100), 100)
        
        self.assertEqual(Utils.getEnvBool('GAY', False), False)
        os.environ['HAPPY'] = 'Yes'
        self.assertEqual(Utils.getEnvBool('HAPPY', False), True)
        
        
    def test_lazyDateThisYear(self):
        func = Utils.lazyDateThisYear
        
        from time import strftime
        
        x = func('20 June')
        self.assertEqual(x, '20 June '+ strftime('%Y'))
        x = func('20 Jun')
        self.assertEqual(x, '20 Jun '+ strftime('%Y'))
        
        x = func('June 20')
        self.assertEqual(x, '20 June '+ strftime('%Y'))
        x = func('Jun 20')
        self.assertEqual(x, '20 Jun '+ strftime('%Y'))
        
    def test_lazyDateDayless(self):
        func = Utils.lazyDateDayless
        
        from time import strftime
        
        x = func('June 2006')
        self.assertEqual(x, '2006/06/01')
        
        x = func('july')
        self.assertEqual(x, strftime('%Y')+'/07/01')
        #print x
        
        x = func('JUL')
        self.assertEqual(x, strftime('%Y')+'/07/01')
        
        

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestUtils))
    return suite

if __name__ == '__main__':
    framework()


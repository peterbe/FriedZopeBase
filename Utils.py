# -*- coding: iso-8859-1 -*-

##
## Fry-IT Zope Base utility scripts
## Peter Bengtsson, peter@fry-it.com, (c) 2005
##


# python
import os
import string
import sys
import re
import inspect
import random
from time import strftime
from random import shuffle
from math import floor
import httplib, urllib
from urlparse import urlparse, urlunparse
from types import FloatType, IntType
from urllib import urlencode
import itertools
import unicodedata
from datetime import date

from htmlentitydefs import entitydefs

entitydefs_inverted = {}
for k,v in entitydefs.items():
    entitydefs_inverted[v] = k

from addhrefs import addhrefs
from unaccent import unaccented_map

# zope
try:
    from DocumentTemplate import sequence
    from Products.PythonScripts.standard import html_quote, newline_to_br, \
         structured_text, url_quote, url_quote_plus, thousands_commas
    from DateTime import DateTime
    from Acquisition import aq_base

except ImportError:
    pass
    #from DocumentTemplate import sequence
    #from Products.PythonScripts.standard import html_quote, newline_to_br, \
    #     structured_text, url_quote, url_quote_plus, thousands_commas



#-----------------------------------------------------------------------------
#
# ZODB
#

## https://bugs.launchpad.net/zope2/+bug/142399
def safe_hasattr(obj, name, _marker=object()):
    """Make sure we don't mask exceptions like hasattr().

    We don't want exceptions other than AttributeError to be masked,
    since that too often masks other programming errors.
    Three-argument getattr() doesn't mask those, so we use that to
    implement our own hasattr() replacement.
    """
    return getattr(obj, name, _marker) is not _marker

def base_hasattr(obj, name):
    """Like safe_hasattr, but also disables acquisition."""
    return safe_hasattr(aq_base(obj), name)


#-----------------------------------------------------------------------------
#
# Debuggning
#

def debug(s, tabs=0, steps=(1,), include_module_name=False):
    inspect_dbg = []
    if isinstance(steps, int):
        steps = range(1, steps+1)
    for i in steps:
        try:
            caller_module = inspect.stack()[i][1]
            caller_method = inspect.stack()[i][3]
            caller_method_line = inspect.stack()[i][2]
        except IndexError:
            break
        if include_module_name:
            if caller_module.endswith('/__init__.py'):
                caller_module = '/'.join(caller_module.split('/')[-2:])
            else:
                caller_module = caller_module.split('/')[-1]
            inspect_dbg.append("(%s)%s:%s"%(caller_module, caller_method, caller_method_line))
        else:
            inspect_dbg.append("%s:%s"%(caller_method, caller_method_line))
    inspect_appendix = ", ".join(inspect_dbg)
    if inspect_appendix:
        out = "\t"*tabs + "%s (%s)"%(s, inspect_appendix)
    else:
        out = "\t"*tabs + "%s"%s

    print out


#-----------------------------------------------------------------------------
#
# Unicode
#

def unaccent_string(ustring, encoding="ascii"):
    if not isinstance(ustring, unicode):
        ustring = ustring.decode(encoding)
    return ustring.translate(unaccented_map()).encode(encoding, "ignore")


def unicodify(i, encoding='latin-1'):
    if type(i) == unicode:
        return i
    else:
        return unicode(str(i), encoding)

def safe_unicodify(s, encodings=('utf8','latin1')):
    if isinstance(s, str):
        if not isinstance(encodings, (tuple, list)):
            encodings = [encodings]
        for encoding in encodings:
            try:
                return unicode(s, encoding)
            except UnicodeDecodeError:
                pass
        raise UnicodeDecodeError, \
        "Unable to unicodify %r with these encodings %s" % (s, encodings)
    return s



def internationalizeID(y, encoding='latin-1'):
    """ this is an improvement to the previous internationalizeID() function
    which is left above.
    Taken from the comment by Aaron Bentley on
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/251871
    """
    if isinstance(y, str):
        y = unicode(y, encoding)
    return unicodedata.normalize('NFKD', y).encode('ascii','ignore')


from types import StringType, UnicodeType, InstanceType

nasty_exception_str = Exception.__str__.im_func

def ustr(v):
    """Convert any object to a plain string or unicode string,
    minimising the chance of raising a UnicodeError. This
    even works with uncooperative objects like Exceptions
    """
    string_types = (StringType,UnicodeType)
    if type(v) in string_types:
        return v
    else:
        fn = getattr(v,'__str__',None)
        if fn is not None:
            # An object that wants to present its own string representation,
            # but we dont know what type of string. We cant use any built-in
            # function like str() or unicode() to retrieve it because
            # they all constrain the type which potentially raises an exception.
            # To avoid exceptions we have to call __str__ direct.
            if getattr(fn,'im_func',None)==nasty_exception_str:
                # Exception objects have been optimised into C, and their
                # __str__ function fails when given a unicode object.
                # Unfortunately this scenario is all too common when
                # migrating to unicode, because of code which does:
                # raise ValueError(something_I_wasnt_expecting_to_be_unicode)
                return _exception_str(v)
            else:
                # Trust the object to do this right
                v = fn()
                if type(v) in string_types:
                    return v
                else:
                    raise ValueError('__str__ returned wrong type')
        # Drop through for non-instance types, and instances that
        # do not define a special __str__
        return str(v)


def _exception_str(exc):
    if hasattr(exc, 'args'):
        if not exc.args:
            return ''
        elif len(exc.args) == 1:
            return ustr(exc.args[0])
        else:
            return str(exc.args)
    return str(exc)


#-----------------------------------------------------------------------------
#
# Internet, sockets, networking
#

def anyPost(url, cgi_params={}):
    params = urllib.urlencode(cgi_params)
    headers = {"Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain"}

    url_parsed = urlparse(url)
    conn = httplib.HTTPConnection(url_parsed[1])
    conn.request("POST", url_parsed[2], params, headers)
    response = conn.getresponse()
    res = response.status, response.reason, response.read()
    conn.close()
    return res

#-----------------------------------------------------------------------------
#
# URL handling
#

def parametrize_url(url, unicode_encoding='utf8', doseq=False, **params):
    """ don't just add the **params because the url
    itself might contain CGI variables embedded inside
    the string. """
    url_parsed = list(urlparse(url))

    for k, v in params.items():
        if isinstance(v, unicode):
            params[k] = v.encode(unicode_encoding)
    encoded = urlencode(params, doseq=doseq)

    qs = url_parsed[4]
    if encoded:
        if qs:
            qs += '&'+encoded
        else:
            qs = encoded
    netloc = url_parsed[1]
    if netloc.find('?')>-1:
        url_parsed[1] = url_parsed[1][:netloc.find('?')]
        if qs:
            qs = netloc[netloc.find('?')+1:]+'&'+qs
        else:
            qs = netloc[netloc.find('?')+1:]

    url_parsed[4] = qs

    if url_parsed[2] == '':
        url_parsed[2] = '/'

    url = urlunparse(url_parsed)
    return url


def AddParam2URL(url, params={}):
    """ return url and append params but be aware of existing params """
    return parametrize_url(url, **params)
    p='?'
    if p in url:
        p = '&'
    url = url + p
    for key, value in params.items():
        url = url + '%s=%s&'%(key, url_quote(value))
    return url[:-1]



#-----------------------------------------------------------------------------
#
# Zope inspired
#


def cookIdAndTitle(s):
    """ if s='image1~Image One.gif' then return ['image1.gif','Image One']

        Testwork:
        s='image1~Image One.gif'    => ['image1.gif','Image One']
        s='image1.gif'              => ['image1.gif','']
        s='image1~.gif'             => ['image1.gif','']
        s='image1~Image One.gif.gif'=> ['image1.gif','Image One.gif']
    """
    if s.find('~') == -1:
        return [s, '']
    splitted = s.split('~',1)
    id = splitted[0]
    rest = s.replace(id+'~','')
    if rest.rfind('.') == -1:
        return [id, rest]
    else:
        pos_last_dot = rest.rfind('.')
        ext = rest[pos_last_dot:]
        id = id.strip() + ext.strip()
        title = rest[0:pos_last_dot].strip()
        return [id, title]


hide_key={'HTTP_AUTHORIZATION':1,
          'HTTP_CGI_AUTHORIZATION': 1,
          }.has_key

def REQUEST2String(REQUEST):
    result="form\n"
    row = "\t%s: %s\n"
    for k,v in _filterPasswordFields(REQUEST.form.items()):
        result=result + row % (escape(k), escape(repr(v)))


    result += "cookies\n"
    for k,v in _filterPasswordFields(REQUEST.cookies.items()):
        result=result + row % (escape(k), escape(repr(v)))

    result += "lazy items\n"
    for k,v in _filterPasswordFields(REQUEST._lazies.items()):
        result=result + row % (escape(k), escape(repr(v)))

    result += "other\n"
    for k,v in _filterPasswordFields(REQUEST.other.items()):
        if k in ('PARENTS','RESPONSE'): continue
        result=result + row % (escape(k), escape(repr(v)))

    for n in "0123456789":
        key = "URL%s"%n
        try: result=result + row % (key, escape(REQUEST[key]))
        except KeyError: pass
    for n in "0123456789":
        key = "BASE%s"%n
        try: result=result + row % (key, escape(REQUEST[key]))
        except KeyError: pass

    result=result+"environ\n"
    for k,v in REQUEST.environ.items():
        if not hide_key(k):
            result=result + row % (escape(k), escape(repr(v)))

    return result



#-----------------------------------------------------------------------------
#
# Quoting
#

def tex_quote(s):
    for k, v in {'&':r'\&', '$':r'\$', '_':r'\_', r'%':r'\%',
               '|':r'\textbackslash', '#':r'\#', '^':r'\^{}',
               '~':r'\~{}',
               '<':'\textless ', # notice the extra space
               '>':'\textgreater ', # notice the extra space
              }.items():
        s = s.replace(k, v)
    return s

def tag_quote(text):
    """ similiar to html_quote but only fix < and > """
    return text.replace('<','&lt;').replace('>','&gt;')


destroyed_hex_entities = re.compile('&amp;#(\d+);')
def safe_html_quote(text):
    """ like html_quote but allow things like &#1234; """
    text = html_quote(text)
    text = destroyed_hex_entities.sub(r'&#\1;', text)
    return text


_badchars_regex = re.compile('|'.join(entitydefs.values()))
_been_fixed_regex = re.compile('&\w+;|&#[0-9]+;')
def html_entity_fixer(text, skipchars=[], extra_careful=1):

    if not text:
        # then don't even begin to try to do anything
        return text

    if isinstance(text, unicode):
        return text.encode('ascii', 'xmlcharrefreplace')

    # if extra_careful we don't attempt to do anything to
    # the string if it might have been converted already.
    if extra_careful and _been_fixed_regex.findall(text):
        return text

    if isinstance(skipchars, basestring):
        skipchars = [skipchars]


    keyholder= {}
    for x in _badchars_regex.findall(text):
        if x not in skipchars:
            keyholder[x] = 1
    text = text.replace('&','&amp;')
    text = text.replace('\x80', '&#8364;')
    for each in keyholder.keys():
        if each == '&':
            continue

        better = entitydefs_inverted[each]
        if not better.startswith('&#'):
            better = '&%s;'%entitydefs_inverted[each]

        text = text.replace(each, better)
    return text


#-----------------------------------------------------------------------------
#
# Randomness
#

def nicepass(alpha=6,numeric=2):
    """
    returns a human-readble password (say rol86din instead of
    a difficult to remember K8Yn9muL )
    """

    vowels = ['a','e','i','o','u']
    consonants = [a for a in string.ascii_lowercase if a not in vowels]
    digits = string.digits

    ####utility functions
    def a_part(slen):
        ret = ''
        for i in range(slen):
            if i%2 ==0:
                randid = random.randint(0,20) #number of consonants
                ret += consonants[randid]
            else:
                randid = random.randint(0,4) #number of vowels
                ret += vowels[randid]
        return ret

    def n_part(slen):
        ret = ''
        for i in range(slen):
            randid = random.randint(0,9) #number of digits
            ret += digits[randid]
        return ret

    ####
    fpl = alpha/2
    if alpha % 2 :
        fpl = int(alpha/2) + 1
    lpl = alpha - fpl

    start = a_part(fpl)
    mid = n_part(numeric)
    end = a_part(lpl)

    return "%s%s%s" % (start,mid,end)


def getRandomString(length=10, loweronly=1, numbersonly=0,
                    more_numbers=0, avoidchars=[], lettersonly=0):
    """ return a very random string """
    if numbersonly:
        l = list('0123456789')
    else:
        if lettersonly:
            lowercase = 'abcdefghijklmnopqrstuvwxyz'
        else:
            lowercase = 'abcdefghijklmnopqrstuvwxyz'+'0123456789'
        if more_numbers and abs(more_numbers)==more_numbers:
            for i in range(more_numbers):
                lowercase += '0123456789'
        if loweronly:
            l = list(lowercase)
        else:
            l = list(lowercase + lowercase.upper())
    if avoidchars:
        if type(avoidchars)==type('s'):
            avoidchars = list(avoidchars)

        for e in avoidchars:
            while e in l:
                l.remove(e)
    shuffle(l)
    s = string.join(l,'')
    if len(s) < length:
        s = s + getRandomString(loweronly=1)
    s = s[:length]
    if loweronly:
        return s.lower()
    else:
        return s


#-----------------------------------------------------------------------------
#
# Sequences, lists
#

def anyTrue(pred, seq):
    """ http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/212959 """
    return True in itertools.imap(pred,seq)

def anyFalse(pred, seq):
    """ http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/212959 """
    return False in itertools.imap(pred,seq)

def insensitiveRemove(item, list):
    rm_these = []
    for each in list:
        if ss(each) == ss(item):
            rm_these.append(each)
    for each in rm_these:
        list.remove(each)

def insensitiveIN(item, list):
    if same_type(item, 's'):
        item = ss(item)
    for each in list:
        if same_type(each, 's'):
            if item == ss(each):
                return 1
    return 0

def listintersection(list1, list2):
    checked = []
    for e in list1:
        if e in list2:
            checked.append(e)
    return checked

def mergeEnglishList(seq, lastword='or'):
    """ make ['abc','def','efg'] into 'abc, def or efg' """
    if len(seq) == 0:
        return ''
    elif len(seq) == 1:
        return seq[0]
    else:
        s = ''
        for i in range(len(seq)):
            if i == len(seq)-2:
                t = ' %s '%lastword
            elif i == len(seq)-1:
                t = ''
            else:
                t = ', '
            s += "%s%s"%(seq[i], t)
        return s


def uniqify(seq, idfun=None): # Alex Martelli ******* order preserving
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        # in old Python versions:
        # if seen.has_key(marker)
        # but in new ones:
        ##if marker in seen: continue
        if seen.has_key(marker): continue
        seen[marker] = 1
        result.append(item)
    return result

def uniqify(seq, idfun=None): # Alex Martelli ******* order preserving
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        # in old Python versions:
        # if seen.has_key(marker)
        # but in new ones:
        ##if marker in seen: continue
        if seen.has_key(marker): continue
        seen[marker] = 1
        result.append(item)
    return result

def iuniqify(seq):
    """ return a list of strings unique case insensitively.
    If the input is ['foo','bar','Foo']
    return ['foo','bar']
    """
    def idfunction(x):
        if isinstance(x, basestring):
            return x.lower()
        else:
            return x
    return uniqify(seq, idfunction)


def moveUpListelement(element, xlist):
    """ move an element in a _mutable_ list up one position
    if possible. If the element is a list, then the function
    is self recursivly called for each subelement.
    """

    assert type(xlist)==type([]), "List to change not of list type "\
                                  "(%r)"%type(xlist)

    if type(element)==type([]):
        for subelement in element:
            moveUpListelement(subelement, xlist)

    if element==xlist[0]:
        pass
    elif element in xlist:
        i=xlist.index(element)
        xlist[i], xlist[i-1] = xlist[i-1], xlist[i]


#-----------------------------------------------------------------------------
#
# HTML handling
#

starttag_regex = re.compile('<.*?>', re.MULTILINE|re.DOTALL)
singletontag_regex = re.compile('<.*?/>', re.MULTILINE|re.DOTALL)
endtag_regex = re.compile('</.*?>', re.MULTILINE|re.DOTALL)
multiple_linebreaks = re.compile('\n\s+\n|\n\n')
def dehtmlify(html):
    """ Try to convert an HTML chunk to text """
    li_tags = re.compile('<li>\s*',re.I)
    html = li_tags.sub(' * ', html)
    html = multiple_linebreaks.sub('\n', html)
    html = starttag_regex.sub('',html)
    html = singletontag_regex.sub('', html)
    html = endtag_regex.sub('\n', html)

    return html.strip()


#-----------------------------------------------------------------------------
#
# String enhancing
#


def ordinalth(n, html=0):
    t = 'th st nd rd th th th th th th'.split()
    if n % 100 in (11, 12, 13): #special case
        if html:
            return '%d'%n+'<sup>th</sup>'
        else:
            return '%dth' % n
    if html:
        return str(n) + '<sup>%s</sup>'% t[n % 10]
    else:
        return str(n) + t[n % 10]


def LineIndent(text, indent, maxwidth=None):
    """ indent each new line with 'indent' """
    if maxwidth:
        parts = []
        for part in text.split('\n'):
            words = part.split(' ')
            lines = []
            tmpline = ''
            for word in words:
                if len(tmpline+' '+word) > maxwidth:
                    lines.append(tmpline.strip())
                    tmpline = word
                else:
                    tmpline += ' ' + word

            lines.append(tmpline.strip())
            start = "\n%s"%indent
            parts.append(indent + start.join(lines))
        return "\n".join(parts)
    else:
        text = indent+text
        text = text.replace('\n','\n%s'%indent)
    return text



def safeId(id, nospaces=0, extra_allows=[]):
    """ Just make sure it contains no dodgy characters """
    lowercase = 'abcdefghijklmnopqrstuvwxyz'
    digits = '0123456789'
    specials = '_-.' + ''.join(extra_allows)
    allowed = lowercase + lowercase.upper() + digits + specials
    if not nospaces:
        allowed = ' ' + allowed
    n_id=[]
    allowed_list = list(allowed)
    for letter in list(id):
        if letter in allowed_list:
            n_id.append(letter)
    return ''.join(n_id)


def banner(text, ch='=', length=78):
    """Return a banner line centering the given text.

        "text" is the text to show in the banner. None can be given to have
            no text.
        "ch" (optional, default '=') is the banner line character (can
            also be a short string to repeat).
        "length" (optional, default 78) is the length of banner to make.

    Examples:
        >>> banner("Peggy Sue")
        '================================= Peggy Sue =================================='
        >>> banner("Peggy Sue", ch='-', length=50)
        '------------------- Peggy Sue --------------------'
        >>> banner("Pretty pretty pretty pretty Peggy Sue", length=40)
        'Pretty pretty pretty pretty Peggy Sue'
    """
    if text is None:
        return ch * length
    elif len(text) + 2 + len(ch)*2 > length:
        # Not enough space for even one line char (plus space) around text.
        return text
    else:
        remain = length - (len(text) + 2)
        prefix_len = remain / 2
        suffix_len = remain - prefix_len
        if len(ch) == 1:
            prefix = ch * prefix_len
            suffix = ch * suffix_len
        else:
            prefix = ch * (prefix_len/len(ch)) + ch[:prefix_len%len(ch)]
            suffix = ch * (suffix_len/len(ch)) + ch[:suffix_len%len(ch)]
        return prefix + ' ' + text + ' ' + suffix


def normalizeMobileNumber(number, default_cc='44'):
    """ prepare a mobile number """
    number = number.strip()
    if number.startswith('00%s'%default_cc):
        number = "+"+number[2:]
    elif number.startswith('0'):
        number = '+%s'%default_cc+number[1:]

    number = number.replace(' ','').replace('-','')

    return number


def ss(s):
    """ simple string """
    return s.strip().lower()


def encodeEmailString(email, title=None, nolink=0):
    """ just write the email like
    <span class="aeh">peter_AT_peterbe_._com</span>
    and a 'onLoad' Javascript will convert it to look nice.
    The way we show the email address must match the Javascript
    that converts it on the fly. """

    methods = ['_dot_',' dot ', '_._']
    shuffle(methods)

    # replace . after @
    if '@' in list(email):
        afterbit = email.split('@')[1]
        newbit = afterbit.replace('.', methods[0])
        email = email.replace(afterbit, newbit)

    methods = ['_', '~']
    shuffle(methods)

    atsigns = ['at','AT']
    shuffle(atsigns)

    # replace @ with *AT*
    email = email.replace('@','%s%s%s'%(methods[0], atsigns[0], methods[0]))

    if title is None or title == email:
        title = email

    spantag = '<span class="aeh">%s</span>'
    spantag_link = '<span class="aeh"><a href="mailto:%s">%s</a></span>'
    if nolink:
        return spantag%email
    else:
        return spantag_link%(email, title)


def encodeEmailString2(email, title=None, nolink=0):
    """ A second version of the old encodeEmailString() function.
    This one returns a XHTML valid tag not wrapped in a <span> tag"""

    methods = [urllib.quote(x) for x in ['_dot_',' dot ', '_._']]
    shuffle(methods)

    # replace . after @
    if '@' in list(email):
        afterbit = email.split('@')[1]
        newbit = afterbit.replace('.', methods[0])
        email = email.replace(afterbit, newbit)

    methods = ['_', '~']
    shuffle(methods)

    atsigns = ['at','AT','ATT']
    shuffle(atsigns)

    r = random.randint(1,3)
    if r==1:
        email = email.replace('@','@(removethis)')
    elif r==2:
        email = email.replace('@','(removethis)@')

    # replace @ with *AT*
    email = email.replace('@','%s%s%s'%(methods[0], atsigns[0], methods[0]))

    if title is None or title == email:
        title = email

    spantag = '<span class="aeh">%s</span>'
    spantag_link = '<a class="aeh" href="mailto:%s">%s</a>'
    if nolink:
        return spantag % email
    else:
        return spantag_link % (email, title)


#-----------------------------------------------------------------------------
#
# Booleanism
#

def niceboolean(value):
    if type(value) is bool:
        return value
    falseness = ('','no','off','false','none','0', 'f')
    return str(value).lower().strip() not in falseness


def isOrdinalth(s):
    """ return true if like 1st, 4th, 11th, 23rd """

    ordn = re.compile(r"""\dst$
                          |\dnd$
                          |\drd$
                          |\dth$
                          |\d\dst$
                          |\d\dnd$
                          |\d\drd$
                          |\d\dth$""",
                      re.I|re.VERBOSE)

    return not not ordn.findall(s)


def typelessEqual(a, b):
    """ Checks equality of two values regardless of type  """
    if a is None or b is None:
        # like Postgres deals with NULL
        return False
    try: # floatable?
        a = float(a)
        b = float(b)
        return a == b
    except ValueError:
        try:
            a = int(a)
            b = int(b)
            return a == b
        except ValueError:
            a = str(a)
            b = str(b)
            return a == b

def same_type(one, two):
    """ use this because 'type' as variable can be used elsewhere """
    return type(one)==type(two)

def safebool(value):
    try:
        return not not int(value)
    except ValueError:
        return 0



#-----------------------------------------------------------------------------
#
# Showers, converters, nicifiers
#


# taken from IssueTrackerProduct and modified
def ShowText(text, display_format='',
             emaillinkfunction=None,
             urllinkfunction=None,
             allowhtml=False, # only applies to plaintext and structured_text
             paragraphtag=True, # only applies with plaintext
             ):
    """
    Display text, using harmless HTML
    """
    if not text: # blank or None
        return ""

    if display_format == 'structuredtext':
        #st=_replace_special_chars(text)
        st=text

        if not allowhtml:
            for k,v in {'<':'&lt;', '>':'&gt;'}.items():
                st = st.replace(k, v)

        st = st.replace('[','|[|')

        st = html_entity_fixer(st, skipchars=('"',))

        st = structured_text(st)

        if allowhtml:
            for k,v in {'<':'&lt;', '>':'&gt;'}.items():
                st = st.replace(v, k)


        for k,v in {'&amp;lt;':'&lt;', '&amp;gt;':'&gt;',
                    '|[|':'['}.items():
            st = st.replace(k,v)


        st = addhrefs(st, emaillinkfunction=emaillinkfunction, urllinkfunction=urllinkfunction)

        st = st.rstrip()

        return st

    elif display_format == 'html':
        return text

    else:
        if paragraphtag:
            t = '<p>%s</p>'%safe_html_quote(text)
        else:
            t = safe_html_quote(text)
        t = t.replace('&amp;lt;','&lt;').replace('&amp;gt;','&gt;')
        t = addhrefs(t)
        t = newline_to_br(t)
        return t


def ShowFilesize(bytes, whole_numbers=False):
    """ Return nice representation of size """
    if bytes < 1024:
        return "1 Kb"
    elif bytes > 1024**3:
        if whole_numbers:
            mb_bytes = '%0.02f'%(bytes / 1024.0**3)
        else:
            mb_bytes = '%.f'%(bytes / 1024.0**3)
        return "%s Gb"%mb_bytes
    elif bytes > 1024**2:
        if whole_numbers:
            mb_bytes = '%0.02f'%(bytes / 1024.0**2)
        else:
            mb_bytes = '%.f'%(bytes / 1024.0**2)
        return "%s Mb"%mb_bytes
    else:
        return "%s Kb"%int(bytes / 1024)


def formatFloat(f, decimal_places=2):
    """ return a float with thousand commas
    and two decimal places if any. """
    try:
        assert type(f) is FloatType or type(f) is IntType, \
               "parameter f is not float or int"
    except AssertionError:
        f = float(f)

    if str(int(f))!=str(f): # try if f==1.1 but not if f==1
        f= round(f, decimal_places)
        _fmt = "%."+str(decimal_places)+"f"
        f = _fmt%f

    f = thousands_commas(f)

    return f


def _QasList(q):
    """ q is a string that might contain 'and' and/or 'or'.
    Remove that and make it a list. """
    L = []
    for e in re.compile("'.*'|\".*\"").findall(q):
        L.append(e[1:-1])
        q = q.replace(e,'')
    r=re.compile(r"\band\b|\bor\b", re.I)
    return r.sub("", q).split() + L

def _warpLine(found, line, template):
#    print found
    return line

def highlightQ(q, text, template='<span class="highlight">%s</span>',
               splitlines=False):
    """ return a result text where certain words are highligheted.
    This code is taken from the IssueTrackerProduct and modified """


    if isinstance(q, str):
        q = unicode(q, 'latin1')
    if isinstance(text, str):
        text = unicode(text, 'latin1')
    if isinstance(template, str):
        template = unicode(template, 'latin1')

    transtab = string.maketrans('/ ','_ ')
    #q=string.translate(q, transtab, '?&!;()<=>*#[]{}')
    q = q.translate('?&!;()<=>*#[]{}')

    highlighted_lines = []

    template = " " + template.strip() + " "
    text = " %s "%text
    for e in _QasList(q):
        regex = "(\s(%s)\s)" % e
        merged_regex = re.compile(regex, re.I)
        text = merged_regex.sub(template%r"\2", text)

    if splitlines:
        lines = []
        for line in text.splitlines():
            line_regex = re.compile('%s'%(template%'.*?'), re.MULTILINE|re.DOTALL)
            if line_regex.findall(line):
                lines.append(line)
        return lines

    return text.strip()


#-----------------------------------------------------------------------------
#
# Validators, checkers
#

def _ShouldBeNone(result): return result is not None
def _ShouldNotBeNone(result): return result is None

tests = (
    # Thank you Bruce Eckels for these (some modifications by Peterbe)
  (re.compile("^[0-9a-zA-Z\.\'\+\-\_]+\@[0-9a-zA-Z\.\-\_]+$"),
   _ShouldNotBeNone, "Failed a"),
  (re.compile("^[^0-9a-zA-Z]|[^0-9a-zA-Z]$"),
   _ShouldBeNone, "Failed b"),
  (re.compile("([0-9a-zA-Z\_]{1})\@."),
   _ShouldNotBeNone, "Failed c"),
  (re.compile(".\@([0-9a-zA-Z]{1})"),
   _ShouldNotBeNone, "Failed d"),
  (re.compile(".\.\-.|.\-\..|.\.\..|.\-\-."),
   _ShouldBeNone, "Failed e"),
  (re.compile(".\.\_.|.\-\_.|.\_\..|.\_\-.|.\_\_."),
   _ShouldBeNone, "Failed f"),
  (re.compile(".\.([a-zA-Z]{2,3})$|.\.([a-zA-Z]{2,4})$"),
   _ShouldNotBeNone, "Failed g"),
  # no underscore just left of @ sign or _ after the @
  (re.compile("\_@|@[a-zA-Z0-9\-\.]*\_"),
   _ShouldBeNone, "Failed h"),
)
def ValidEmailAddress(address, debug=None):
    for test in tests:
        if test[1](test[0].search(address)):
            if debug: return test[2]
            return 0
    return 1

def ValidMobileNumber(mn):
    """ Check if a mobile number is valid """
    if mn is None:
        return 0

    mn = mn.replace(' ','').strip()
    if len(mn) < 10:
        return false

    # | pipe means to "or" cases
    #  1st: must start with '+' and be numbers the rest
    #  2nd: must start with '0' and be numbers the rest
    test = re.compile(r'^\+[0-9]+$|^0[0-9]+$')

    return not not test.findall(mn) # use 'not not' to reduce to boolean


def ValidDate(day, month, year):
    """ Checks if a date address is valid and within oferred range """
    month = string.zfill(month, 2)
    day = string.zfill(day, 2)
    isodatestring = "%s-%s-%s"%(year, month, day)

    try:
        dateobj = DateTime(isodatestring)
        return 1
    except:
        return 0



#-----------------------------------------------------------------------------
#
# Date testing, comparing, modifying
#

def somedate2DateTime(datestr, raiseerrors=1):
    """ accept
    today,
    18/02/02,
    18/02/02 15:00,
    18/02/2003,
    18/02/2003 15:00,
    18,
    18[st|nd|rd|th],
    15:00,
    18 15:00,
    18 FeB[ruary],
    18[st|nd|rd|th] FeB[ruary],
    18 FeB[ruary] 2003,
    18[st|nd|rd|th] FeB[ruary] 2003,
    18 FeB[ruary] 15:00,
    18[st|nd|rd|th] FeB[ruary] 15:00,
    Fri[day],
    Fri[day] 15:00
    noW """
    datestr = datestr.lower().strip()
    datestr = _simpleSpace(datestr)
    now = DateTime()


    _months = ['January','February','March','April','May','June','July',
               'August','September','October','November','December']
    _months = [x.lower() for x in _months]
    _d_months={}
    for i in range(len(_months)):
        _d_months[_months[i]] = i+1
        _d_months[_months[i][:3]] = i+1
    _months=_d_months

    _days = ['Monday','Tuesday','Wednesday','Thursday',
             'Friday','Saturday','Sunday']
    _days = [x.lower() for x in _days]
    _d_days={}
    for e in _days:
        _d_days[e]=e
        _d_days[e[:3]]=e
    _days=_d_days


    def _onlyInt(*s, **kw):
        for _s in s:
            try:
                _s=int(_s)
            except ValueError:
                if kw.get('pos_ord') and isOrdinalth(_s):
                    pass
                else:
                    return 0
        return 1

    def _ord2Int(s):
        """ convert 1st to 1 """
        s = s.lower()
        for each in ['st','nd','rd','th']:
            s = s.replace(each,'')
        return int(s)

    def _possibleTime(s):
        try:
            h,m = s.split(':')
            h=int(h)
            h=int(m)
            return 1
        except:
            return 0

    def _possibleMonth(s, ms=_months):
        return s.lower().strip() in ms.keys()
    def _possibleDay(s, ds=_days):
        return s.lower().strip() in ds.keys()
    def _getmonthnr(s, ms=_months):
        return ms[s.lower()]
    def _getdayrepr(s, ds=_days):
        return ds[s.lower().strip()]

    # 'now'
    if type(datestr) != type('s'):
        # already a DateTime instance
        return datestr

    elif datestr == 'today':
        return DateTime()

    elif datestr == 'now':
        return DateTime()

    # '18/02/2003 13:30'
    elif datestr.count('/') == 2 and datestr.find(' ') > -1 and \
         datestr.split(' ')[1].find(':') > -1:
        yy, mm, dd = twistDateformat(datestr.split(' ')[0]).split('/')

        time = datestr.split(' ')[1]
        if time.count(':') == 1:
            hour, minute = time.split(':')
            hour = int(hour)
            minute = int(minute)

            datestring = '%s/%s/%s %s:%s'%(yy, mm, dd, hour, minute)
            return DateTime(datestring)

    # '18/02/2003'
    elif datestr.count('/') == 2:
        yy, mm, dd = twistDateformat(datestr).split('/')
        dd=int(dd)
        mm=int(mm)
        yy=int(yy)

        datestring = '%s/%s/%s 00:00'%(yy,mm,dd)
        return DateTime(datestring)

    # '18' or '18[st|nd|rd|th]'
    elif _onlyInt(datestr, pos_ord=1):
        dd = int(_ord2Int(datestr))
        mm = int(now.strftime('%m'))
        yy = int(now.strftime('%Y'))

        datestring = '%s/%s/%s 00:00'%(yy, mm, dd)
        return DateTime(datestring)

    # '15:00'
    elif len(datestr.split(' '))==1 and _possibleTime(datestr):
        dd = int(now.strftime('%d'))
        mm = int(now.strftime('%m'))
        yy = int(now.strftime('%Y'))
        h, m = datestr.split(':')

        datestring = '%s/%s/%s %s:%s'%(yy,mm,dd, h, m)
        return DateTime(datestring)

    # '18 15:00' or '18[st|nd|rd|th] 15:00'
    elif len(datestr.split(' '))==2 and\
         _onlyInt(datestr.split(' ')[0], pos_ord=1) and \
         _possibleTime(datestr.split(' ')[1]):
        dd = int(_ord2Int(datestr.split(' ')[0]))
        mm = int(now.strftime('%m'))
        yy = int(now.strftime('%Y'))

        h, m = datestr.split(' ')[1].split(':')

        datestring = '%s/%s/%s %s:%s'%(yy,mm,dd,h,m)
        return DateTime(datestring)

    # '15 FeB[ruary] 2003' or '15[st|nd|rd|th] FeB[ruary] 2003'
    elif len(datestr.split(' '))==3 and\
         _onlyInt(datestr.split(' ')[0], pos_ord=1) and\
         _possibleMonth(datestr.split(' ')[1]) and \
         _onlyInt(datestr.split(' ')[2]):
        splitted = datestr.split(' ')
        dd = int(_ord2Int(splitted[0]))
        mm = _getmonthnr(splitted[1])
        yy = int(splitted[2])

        datestring = '%s/%s/%s 00:00'%(yy,mm,dd)
        return DateTime(datestring)

    # '15 Feb' or '15[st|nd|rd|th] Feb'
    elif len(datestr.split(' '))==2 and \
         _onlyInt(datestr.split(' ')[0], pos_ord=1) and\
         _possibleMonth(datestr.split(' ')[1]):
        dd = int(_ord2Int(datestr.split(' ')[0]))
        mm = _getmonthnr(datestr.split(' ')[1])
        yy = int(now.strftime('%Y'))

        datestring = '%s/%s/%s 00:00'%(yy,mm,dd)
        return DateTime(datestring)

    # '18[st|nd|rd|th] FeB[ruary] 15:00'
    elif len(datestr.split(' '))==3 and \
         _onlyInt(datestr.split(' ')[0], pos_ord=1) and \
         _possibleMonth(datestr.split(' ')[1]) and \
         _possibleTime(datestr.split(' ')[2]):
        dd = int(_ord2Int(datestr.split(' ')[0]))
        mm = _getmonthnr(datestr.split(' ')[1])
        yy = int(now.strftime('%Y'))

        h, m = datestr.split(' ')[2].split(':')

        datestring = '%s/%s/%s %s:%s'%(yy,mm,dd,h,m)
        return DateTime(datestring)


    # 'Fri[day]'
    elif _possibleDay(datestr):
        day = _getdayrepr(datestr)
        fromdate = DateTime(now.strftime('%Y/%m/%d 00:00'))+1
        return _getNextDayByDay(day, fromdate)

    # 'Fri[day] 15:00'
    elif len(datestr.split(' '))==2 and _possibleDay(datestr.split(' ')[0])\
         and _possibleTime(datestr.split(' ')[1]):
        day = _getdayrepr(datestr.split(' ')[0])
        h, m = datestr.split(' ')[1].split(':')
        _fmt = '%Y/%m/%d '+'%s:%s'%(h,m)
        fromdate = DateTime(now.strftime(_fmt))+1
        return _getNextDayByDay(day, fromdate)
    else:
        if raiseerrors:
            raise "SomeDateFailed", datestr
        else:
            return None

def _getNextDayByDay(day, fromdate):
    """ loop through all dates to find next match """
    for i in range(8):
        then = fromdate+i
        if then.strftime('%A').lower() == day:
            return then
    return None

# Language constants
MINUTE = 'minute'
MINUTES = 'minutes'
HOUR = 'hour'
HOURS = 'hours'
YEAR = 'year'
YEARS = 'years'
MONTH = 'month'
MONTHS = 'months'
WEEK = 'week'
WEEKS = 'weeks'
DAY = 'day'
DAYS = 'days'
AND = 'and'


def timeSince(firstdate, seconddate, afterword=None,
              minute_granularity=False,
              max_no_sections=3):
    """
    Use two date objects to return in plain english the difference between them.
    E.g. "3 years and 2 days"
     or  "1 year and 3 months and 1 day"

    Try to use weeks when the no. of days > 7

    If less than 1 day, return number of hours.

    If there is "no difference" between them, return false.
    """

    def wrap_afterword(result, afterword=afterword):
        if afterword is not None:
            return "%s %s" % (result, afterword)
        else:
            return result

    fdo = firstdate
    sdo = seconddate

    day_difference = int(abs(sdo-fdo))

    years = day_difference/365
    months = (day_difference % 365)/30
    days = (day_difference % 365) % 30
    minutes = ((day_difference % 365) % 30) % 24


    if days == 0 and months == 0 and years == 0:
        # use hours
        hours=int(round(abs(sdo-fdo)*24, 2))
        if hours == 1:
            return wrap_afterword("1 %s" % (HOUR))
        elif hours > 0:
            return wrap_afterword("%s %s" % (hours, HOURS))
        elif minute_granularity:
            minutes = int(round(abs(sdo-fdo) * 24 * 60, 3))
            if minutes == 1:
                return wrap_afterword("1 %s" % MINUTE)
            elif minutes > 0:
                return wrap_afterword("%s %s" % (minutes, MINUTES))
            else:
                # if the differnce is smaller than 1 minute,
                # return 0.
                return 0
        else:
            # if the difference is smaller than 1 hour,
            # return it false
            return 0
    else:
        s = []
        if years == 1:
            s.append('1 %s'%(YEAR))
        elif years > 1:
            s.append('%s %s'%(years,YEARS))

        if months == 1:
            s.append('1 %s'%MONTH)
        elif months > 1:
            s.append('%s %s'%(months,MONTHS))

        if days == 1:
            s.append('1 %s'%DAY)
        elif days == 7:
            s.append('1 %s'%WEEK)
        elif days == 14:
            s.append('2 %s'%WEEKS)
        elif days == 21:
            s.append('3 %s'%WEEKS)
        elif days > 14:
            weeks = days / 7
            days = days % 7
            if weeks == 1:
                s.append('1 %s'%WEEK)
            else:
                s.append('%s %s'%(weeks, WEEKS))
            if days % 7 == 1:
                s.append('1 %s'%DAY)
            elif days > 0:

                s.append('%s %s'%(days % 7,DAYS))
        elif days > 1:
            s.append('%s %s'%(days,DAYS))

        s = s[:max_no_sections]

        if len(s)>1:
            return wrap_afterword("%s" % (string.join(s,' %s '%AND)))
        else:
            return wrap_afterword("%s" % s[0])



MONTHS_ABBREVIATED = [date(2007, e, 1).strftime('%b').lower() for e in range(1,13)]
MONTHS_FULL = [date(2007, e, 1).strftime('%B').lower() for e in range(1,13)]

LAZY_MONTH_YEAR_REGEX = re.compile(
                        '^(%s)\s+(%s)$' % ('|'.join(MONTHS_ABBREVIATED+MONTHS_FULL),
                                       '|'.join([str(x) for x in range(2004, 2015)])),
                                       re.I)

LAZY_YEAR_MONTH_REGEX = re.compile(
                        '^(%s)\s+(%s)$' % ('|'.join([str(x) for x in range(2004, 2015)]),
                                         '|'.join(MONTHS_ABBREVIATED+MONTHS_FULL)),
                                       re.I)

LAZY_DAY_MONTH_YEARLESS_REGEX = re.compile(
                        '^(\d{1,2})\s+(%s)$' % ('|'.join(MONTHS_FULL+MONTHS_ABBREVIATED)),
                                       re.I)

LAZY_MONTH_DAY_YEARLESS_REGEX = re.compile(
                        '^(%s)\s+(\d{1,2})$' % ('|'.join(MONTHS_FULL+MONTHS_ABBREVIATED)),
                                       re.I)

def lazyDateThisYear(datestr):
    """ return and change the datestr we recognize it to be one of these
    kinds of formats:
        '20 June'
        '20 Jun'
        'June 20'
        'Jun 20'
    If we do recognize it, return it with todays year appended at the
    end.
    """
    if LAZY_DAY_MONTH_YEARLESS_REGEX.findall(datestr):
        day, month = LAZY_DAY_MONTH_YEARLESS_REGEX.findall(datestr)[0]
        today = DateTime()
        return '%s %s %s' %(day, month, today.strftime('%Y'))
    elif LAZY_MONTH_DAY_YEARLESS_REGEX.findall(datestr):
        month, day = LAZY_MONTH_DAY_YEARLESS_REGEX.findall(datestr)[0]
        today = DateTime()
        return '%s %s %s' %(day, month, today.strftime('%Y'))

    return datestr

def lazyDateDayless(datestr, last_day_of_month=False):
    """ if datestr is 'june 2005' return '2005/06/01'
    (or '2005/06/30' if last_day_of_month is True)
    """

    def fixDateStr(datestr, month, year, last_day_of_month):
        try:
            month = [x.lower() for x in MONTHS_FULL].index(month.lower()) + 1
        except ValueError:
            month = [x.lower() for x in MONTHS_ABBREVIATED].index(month.lower()) + 1
        if last_day_of_month:
            year = int(year)
            if int(month) + 1 > 12:
                year += (int(month) + 1) % 12
                month = (int(month) + 1) / 12
            else:
                month = int(month) + 1
            datestr = '%s/%s/01' % (year, string.zfill(month, 2))
            datestr = (DateTime(datestr)-1).strftime('%Y/%m/%d')
        else:
            datestr = '%s/%s/01' % (year, string.zfill(month, 2))

        return datestr

    if LAZY_MONTH_YEAR_REGEX.findall(datestr):
        month, year = LAZY_MONTH_YEAR_REGEX.findall(datestr)[0]
        datestr = fixDateStr(datestr, month, year, last_day_of_month)
    elif LAZY_YEAR_MONTH_REGEX.findall(datestr):
        year, month = LAZY_YEAR_MONTH_REGEX.findall(datestr)[0]
        datestr = fixDateStr(datestr, month, year, last_day_of_month)
    elif datestr.lower() in [x.lower() for x in MONTHS_FULL]:
        datestr += ' ' + strftime('%Y')
        return lazyDateDayless(datestr)
    elif datestr.lower() in [x.lower() for x in MONTHS_ABBREVIATED]:
        full_index = [x.lower() for x in MONTHS_ABBREVIATED].index(datestr.lower())
        full = MONTHS_FULL[full_index]
        datestr = '%s ' % full + strftime('%Y')
        return lazyDateDayless(datestr)
    return datestr



#-----------------------------------------------------------------------------
#
# External programs
#

try:
    import subprocess
    common_version_arguments = {
      'less':'-V',
      'convert':'-version',
      'svn':'--version',
      'dot':'-V',
      'ocrad':'-h',
      'pngtopnm':'-h',
      'djpeg':'-h',
    }
    def hasExternalProgram(name, cmd_argument_version=None):
        if cmd_argument_version is None:
            cmd_argument_version = common_version_arguments.get(name, '-v')
        proc = subprocess.Popen('%s %s' % (name, cmd_argument_version),
                                shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        v = proc.communicate()
        # some programs sends the version info on stderr
        if name in ('dot','pdftotext','pngtopnm','djpeg'):
            return bool(v[1])
        else:
            return not bool(v[1])

except ImportError:
    def hasExternalProgram(name, version=None):
        print >>sys.stderr, "hasExternalProgram() needs subprocess which is "\
                            "only available in python 2.4 and newer"
        return False


#-----------------------------------------------------------------------------
#
# System related
#

def getEnvBool(key, default):
    """ return an boolean from the environment variables """
    value = os.environ.get(key, default)
    try:
        value = not not int(value)
    except ValueError:
        if str(value).lower().strip() in ['yes','on','t','y']:
            value = 1
        elif str(value).lower().strip() in ['no','off','f','n']:
            value = 0
        else:
            value = default
    return value

def getEnvInt(key, default):
    """ return an integer from the environment variables """
    value = os.environ.get(key, default)
    try:
        return int(value)
    except ValueError:
        return default

def getEnvStr(key, default=''):
    """ return an integer from the environment variables """
    value = os.environ.get(key, default)
    try:
        return str(value)
    except ValueError:
        return default



def test_highlightQ():
    text = '''this is Peter Bengtsson
is here
this line has nothing that we care about
bu here peter is mentioned
again'''
    print highlightQ("peter is", text, splitlines=1)
    print
    text = "Expertise"
    print highlightQ("expertise or nothing", text, template="<s>%s</s>")



def test_ShowText():
    text = "Peter **bengtsson** was _here_"
#    print ShowText(text, 'structuredtext')

    text += " <keep>"
    #print ShowText(text, 'structuredtext')
    #print ShowText(text, 'structuredtext', allowhtml=1)

    text = "Word\n\nWord2"
    print ShowText(text)


if __name__=='__main__':
    #test_highlightQ()
    test_ShowText()
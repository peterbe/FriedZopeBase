# -*- coding: iso-8859-1 -*-
##
## Fry-IT Zope Bases
## Peter Bengtsson, peter@fry-it.com, (c) 2005
##

# python
import os, inspect, sys, re
import cStringIO
import cgi
from urlparse import urlparse
import logging
from time import time, strftime
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Header import Header
from email.Utils import parseaddr, formataddr
import email.Header as email_Header


# Zope
import OFS
from App.Common import rfc1123_date
from ExtensionClass import Base
from Globals import Persistent
from OFS import SimpleItem, Folder, OrderedFolder
from Products.ZCatalog.CatalogAwareness import CatalogAware
#from zLOG import LOG, ERROR, INFO, PROBLEM, WARNING
from DateTime import DateTime

try:
    from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2
except ImportError:
    class BTreeFolder2(Folder.Folder):
        pass

import Utils

__all__ = ('HomepageBaseCatalogAware','HomepageBTreeBaseCatalogAware',
           'HomepageOrderedBaseCatalogAware',
           'HomepageBase', 'HomepageOrderedBase', 'HomepageBTreeBase',
           'SimpleItemBaseCatalogAware', 'SimpleItemBase'
           )

logger = logging.getLogger("FriedZopeBase.Bases")

#-----------------------------------------------------------------------------
#
# Scroll to the bottom of this file for the interesting classes
#

DateTimeType = type(DateTime())
ANCHOR_REGEX = re.compile('#[\w\-_]+$')

class _FriedBase(Base):

    #-------------------------------------------------------------------------
    #
    # Support the bridge between the products misc_ and templates
    #

    def getStaticAlias(self, object_id):
        """ wrapper on getMiscAlias() that always passed the current context
        """
        return self.getMiscAlias(object_id, context=self)


    def getMiscAlias(self, misc_object_id, context=None):
        """ If this self has a misc_infinite_aliases then return the
        alias of this one.
        If @misc_object_id looks like '/misc_/Mest/screen.css' then ignore the
        first given bit.
        """
        if context:
            # We might have been given a base context but the misc_object_id
            # might be something like /css/plugin/file.css then we need to
            # get context = context.css.plugin
            path, filename = misc_object_id.rsplit('/', 1)
            for bit in [x for x in path.split('/') if x.strip()]:
                context = getattr(context, bit, context)

            if Utils.getEnvStr('ABSOLUTE_MISC_URLS', '').count('//'):
                misc_object_id = Utils.getEnvStr('ABSOLUTE_MISC_URLS') + misc_object_id

            elif Utils.getEnvBool('ABSOLUTE_MISC_URLS', False):
                # see comment below about ABSOLUTE_MISC_URLS
                if misc_object_id.startswith('/'):
                    misc_object_id = self.absolute_url() + misc_object_id
                else:
                    misc_object_id = '%s/%s' % (self.absolute_url(), misc_object_id)

        else:
            if misc_object_id.startswith('/misc_/'):

                productid, filename = misc_object_id[len('/misc_/'):].split('/', 1)

                if Utils.getEnvStr('ABSOLUTE_MISC_URLS', '').count('//'):
                    misc_object_id = Utils.getEnvStr('ABSOLUTE_MISC_URLS') + misc_object_id

                elif Utils.getEnvBool('ABSOLUTE_MISC_URLS', False):
                    # Why would you want to do this? Well, if you have a ProxyPass
                    # rule that looks like this:
                    # ProxyPass /bar http://127.0.0.1:8080/VirtualHostBase/http/foo.com:80/zobjectid/VirtualHostRoot/_vh_bar
                    # then the <base> tag href will become http://foo.com/bar but
                    # the misc_ URLs will be http://foo.com/misc_/ProductName/screen.css
                    # which is not always ideal because if you host multiple sub-paths
                    # (not sub-domains) on one apache you won't be able to distinguish
                    # between them.
                    # This was the important problem Jan discovered (July, 2008)
                    # which caused him problems with root.fry-it.com/ovz-...
                    misc_object_id = self.absolute_url() + misc_object_id
            else:
                productid, filename = misc_object_id.split('/')

            context = getattr(OFS.misc_.misc_, productid)

        if not hasattr(context, 'misc_infinite_aliases'):
            return misc_object_id

        aliases = context.misc_infinite_aliases
        return misc_object_id.replace(filename,
                                      aliases.get(filename, filename))



    #-------------------------------------------------------------------------
    #
    # Where ZODB meets the file system
    #

    def _deployImages(self, destination, dir, clean=0):
        """ do the actual deployment of images in a dir """
        s=''
        osj = os.path.join
        image_extensions = ['jpg','png','gif','jpeg','ico']
        for filestr in os.listdir(dir):
            if self._file_has_extensions(filestr, image_extensions):
                # take the image
                id, title = Utils.cookIdAndTitle(filestr)
                base= getattr(destination,'aq_base',destination)
                if hasattr(base, id) and clean:
                    destination.manage_delObjects([id])

                if not hasattr(base, id):
                    content_type = ''
                    if id.endswith('.ico'):
                        content_type = 'image/x-icon'
                    destination.manage_addImage(id, title=title, \
                          file=open(osj(dir, filestr),'rb').read(),
                          content_type=content_type)
                    s +="Image (%s)\n"%id
            elif os.path.isdir(osj(dir, filestr)):
                if filestr in ('CVS','.svn'):
                    continue

                if not hasattr(destination, filestr):
                    destination.manage_addFolder(filestr)
                new_destination = getattr(destination, filestr)
                s += self._deployImages(new_destination, osj(dir, filestr),
                                        clean=clean)

        return s

    def _file_has_extensions(self, filestr, extensions):
        """ check if a filestr has any of the give extensions """
        for extension in extensions:
            if filestr.lower().endswith('.'+extension):
                return True
        return False


    #-------------------------------------------------------------------------
    #
    # Some useful methods for simplifying URLs
    #


    def relative_url(self):
        """ shorter than absolute_url """
        return self.global_relative_url(self)

    def global_relative_url(self, object_or_url):
        """ return a simpler url of any object """
        if Utils.same_type(object_or_url, 's'):
            url = object_or_url
        else:
            url = object_or_url.absolute_url()
        return url.replace(self.REQUEST.BASE0, '')


    def getRedirectURL(self, url, params=None, noaurl=0, **kw):
        """ prepares a URL with params
        if url='http://page' and params{'a':123,'b':'foo bar'}
        you get 'http://page?a:int=123&b=foo%bar'
        """
        if params is None:
            params = {}

        for k, v in kw.items():
            if not params.has_key(k):
                params[k] = v

        datetimeinstance = DateTime()

        post_url = ''
        for post_url in ANCHOR_REGEX.findall(url):
            url = ANCHOR_REGEX.sub('', url)
            break

        p='?'
        if url.find(p) > -1:
            p='&'
        for k, v in params.items():
            if isinstance(v, str):
                v = Utils.url_quote_plus(v)
            elif isinstance(v, unicode):
                v = Utils.url_quote_plus(v.encode('latin1', 'xmlcharrefreplace'))
            elif Utils.same_type(v, datetimeinstance):
                k = "%s:date"%k
                v = Utils.url_quote_plus(v.strftime('%Y/%m/%d %H:%M'))
            elif Utils.same_type(v, 33):
                k = "%s:int"%k
            elif Utils.same_type(v, 3.3):
                k = "%s:float"%k
            elif Utils.same_type(v, []):
                for item in v:
                    url = '%s%s%s:list=%s'%(url, p, k, item)
                    if p in url:
                        p='&'
                continue

            url = '%s%s%s=%s'%(url, p, k, v)
            if p in url:
                p='&'

        return url + post_url


    def slimTag(self, imageobject, **kw):
        """ return the image object but with a shorter URL """
        ourl = imageobject.absolute_url()
        tag = apply(imageobject.tag, (), kw)
        return tag.replace(ourl, self.slimURL(ourl))
    slimtag = slimTag

    def slimURL(self, url, emptyslash=False):
        """ suppose 'url' is http://www.peterbe.com/foo/bar.html
        then return /foo/bar.html """
        # if url by misstake an object?
        if not Utils.same_type(url, ''):
            if url is None:
                return None # fuck off then!

            if hasattr(url, 'meta_type'):
                # url is a Zope object
                url = url.absolute_url() # wild try
            else:
                url = str(url)

        base0 = self.REQUEST.BASE0
        if url == base0 and emptyslash:
            return "/"
        else:
            return url.replace(base0, '')

    slimurl = slimURL


    def ActionURL(self, url=None):
        """
        If URL is http://host/index_html
        I prefer to display it http://host
        Just a little Look&Feel thing
        """
        if url is None:
            url = self.REQUEST.URL

        URLsplitted = url.split('/')
        if URLsplitted[-1] == 'index_html':
            return '/'.join(URLsplitted[:-1])

        return url


    def thisInURL(self, url, homepage=0, exactly=0):
        """ To find if a certain objectid is in the URL """
        URL = self.ActionURL(self.REQUEST.URL)
        rootURL = self.getRootURL()
        if homepage and URL == rootURL:
            return True
        else:
            URL = URL.lower()
            if Utils.same_type(url, 's'):
                pageurls = [url]
            else:
                pageurls = url

            state = False
            for pageurl in pageurls:
                if not (pageurl.startswith('http') or pageurl.startswith('/')):
                    pageurl = rootURL + '/' + pageurl

                if exactly:
                    if URL == pageurl.lower():
                        state = True # at least one good one
                else:
                    if URL.find(pageurl.lower()) > -1:
                        state = True

            return state

    def thisInURLEnding(self, endings, homepage=0, exactly=0):
        """ To find if a certain objectid is in the URL """
        if isinstance(endings, basestring):
            endings = [endings]
        for ending in endings:
            if ending.find('/')==-1:
                ending = '/'+ending
            if self.thisInURL(self.REQUEST.URL1+ending):
                return True
        return False



    #-------------------------------------------------------------------------
    #
    # For changing the querystring
    #

    def changeQueryString(self, querystring, **keywordvariables):
        """ return the querystring changed by the 'keywordvariables' dict.

        For example, if querystring= 'foo=bar&bar=1' and
        keywordvariables= {'foo':'bar2', 'bar':2, 'new':1}
        then the result will be 'foo=bar2&bar=2&new=1'
        """
        qs = cgi.parse_qs(querystring, 1)
        for k, v in keywordvariables.items():
            qs[k] = [v]
        return self._stringifyQueryString(qs)

    def reduceQueryString(self, querystring, *keys):
        """ return the querystring where an element has been removed """
        qs = cgi.parse_qs(querystring, 1)
        changes = 0
        for key in keys:
            if qs.has_key(key):
                del qs[key]
                changes += 1

        if changes:
            return self._stringifyQueryString(qs)
        else:
            return querystring

    def _stringifyQueryString(self, qs):
        lines = []
        for k, v in qs.items():
            if len(v) > 1:
                for v_ in v:
                    lines.append('%s=%s' % (k, Utils.url_quote(v_)))
            else:
                lines.append('%s=%s' % (k, Utils.url_quote(str(v[0]))))
        return '&'.join(lines)


    #-------------------------------------------------------------------------
    #
    # Cookies
    #

    def set_cookie(self, key, value, expires=None, path='/',
                   across_domain_cookie_=False, RESPONSE=None,
                   **kw):
        """ set a cookie in REQUEST

        'across_domain_cookie_' sets the cookie across all subdomains
        eg. www.mobilexpenses.com and mobile.mobilexpenses.com etc.
        This rule will only apply if the current domain name plus sub domain
        contains at least two dots.
        """
        if expires is None:
            then = DateTime()+365
            then = then.rfc822()
        elif isinstance(expires, int):
            then = DateTime()+expires
            then = then.rfc822()
        elif type(expires)==DateTimeType:
            # convert it to RFC822()
            then = expires.rfc822()
        else:
            then = expires

        if across_domain_cookie_ and not kw.get('domain'):

            # set kw['domain'] = '.domainname.com' if possible
            cookie_domain = self._getCookieDomain()
            if cookie_domain:
                kw['domain'] = cookie_domain

        if RESPONSE is None:
            RESPONSE = self.REQUEST.RESPONSE

        RESPONSE.setCookie(key, value,
                           expires=then, path=path, **kw)

    def get_cookie(self, key, default=None, REQUEST=None):
        """ return a cookie from REQUEST """
        if REQUEST is None:
            REQUEST = self.REQUEST
        return REQUEST.cookies.get(key, default)

    def has_cookie(self, key, REQUEST=None):
        """ return if a cookie is set """
        if REQUEST is None:
            REQUEST = self.REQUEST
        return REQUEST.cookies.has_key(key)

    def expire_cookie(self, key, path='/', across_domain_cookie_=False,
                      RESPONSE=None):
        """ expire a cookie

        'across_domain_cookie_' sets the cookie across all subdomains
        eg. www.mobilexpenses.com and mobile.mobilexpenses.com etc.
        This rule will only apply if the current domain name plus sub domain
        contains at least two dots.
        """
        if RESPONSE is None:
            RESPONSE = self.REQUEST.RESPONSE

        if across_domain_cookie_:
            cookie_domain = self._getCookieDomain()
            if cookie_domain:
                RESPONSE.expireCookie(key, path=path, domain=cookie_domain)
                return

        RESPONSE.expireCookie(key, path=path)

    def _getCookieDomain(self):
        """ from the REQUEST.URL work out what is the cookie domain.
        E.g. if REQUEST.URL is http://www.foo.com/path/page.html
        the correct result is '.foo.com'
        """
        netloc = urlparse(self.REQUEST.URL)[1]

        threes = 'com', 'net', 'org', 'biz', 'gov'
        fours = 'name', 'info', 'firm', 'gov'
        if not re.findall('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', netloc):
            top = netloc.split('.')[-1]
            if top in threes or top in fours:
                if len(netloc.split('.')) > 2:
                    return '.%s' % '.'.join(netloc.split('.')[1:])
            else:
                if len(netloc.split('.')) > 3:
                    return '.%s' % '.'.join(netloc.split('.')[1:])

        return None


    #-------------------------------------------------------------------------
    #
    # Sessions
    #

    def set_session(self, key, value):
        """ set session data """
        self.REQUEST.SESSION.set(key, value)

    def get_session(self, key, default=None):
        """ return a session data """
        return self.REQUEST.SESSION.get(key, default)

    def has_session(self, key):
        """ return if a session is set """
        return self.REQUEST.SESSION.has_key(key)

    def delete_session(self, key):
        """ remove an item from the session object """
        return self.REQUEST.SESSION.delete(key)


    #------------------------------------------------------------------------
    #
    # Caching
    #

    def stopCache(self):
        """ set appropriate headers to make sure it's not being cached """
        response = self.REQUEST.RESPONSE
        now = DateTime().toZone('GMT').rfc822()
        response.setHeader('Expires', now)
        response.setHeader('Cache-Control','public,max-age=0')
        response.setHeader('Pragma', 'no-cache') # HTTP 1.0 and MS IE



    def doCache(self, hours=10):
        """ set cache headers on this request """
        if hours > 0:
            response = self.REQUEST.RESPONSE
            #now = DateTime()
            #then = now+float(hours/24.0)
            #response.setHeader('Expires', then.rfc822())
            response.setHeader('Expires', rfc1123_date(time() + 3600*hours))
            response.setHeader('Cache-Control', 'public,max-age=%d' % int(3600*hours))


    ##########################################################################
    ##                                                                      ##
    ## Below are wrappings to functions (not methods) located in the        ##
    ## Utils.py file.                                                       ##
    ##                                                                      ##
    ##########################################################################


    #------------------------------------------------------------------------
    #
    # Internet, sockets, networking
    #

    def anyPost(self, *a, **k):
        return apply(Utils.anyPost, a, k)

    def AddParam2URL(self, *a, **k):
        return Utils.AddParam2URL(*a, **k)
    AddParams2URL=AddParam2URL

    def cookIdAndTitle(self, *a, **k):
        return apply(Utils.cookIdAndTitle, a, k)

    def REQUEST2String(self, REQUEST):
        return Utils.REQUEST2String(REQUEST)

    def http_redirect(self, url, lock=0, **kw):
        """ a clever redirect wrapper """

        if hasattr(url, 'absolute_url'):
            # an object was passed instead of a string url
            url = url.absolute_url()

        if isinstance(lock, dict):
            # accidently called http_redirect('page', {'key':'value'})
            kw.update(lock)
            lock = 0

        if kw:
            url = self.getRedirectURL(url, kw)

        if url.startswith('/') and hasattr(self, 'getRootURL'):
            url = self.getRootURL() + url
        elif url.startswith('/'):
            url = self.REQUEST.BASE0 + url
        elif not url.startswith('http'):
            if url.startswith('/'):
                url = self.REQUEST.URL1 + url
            else:
                url = self.REQUEST.URL1 + '/' + url

        self.REQUEST.RESPONSE.redirect(url, lock=lock)

    def sendEmail(self, msg, to=None, fr=None, subject=None,
                  mcc=None, mbcc=None, subtype='plain', charset='us-ascii',
                  swallowerrors=False, debug=None,
                  construct_body=False # for legacy reasons
                  ):
        """ Attempt to send emails un protectedly. Return true if
        managed to send it, false otherwise. (except when 'swallowerrors'
        is true where errors can be raised).

        If debug is set print the message there instead of actually sending it

        mcc, mbcc, subtype and charset can only be passed if the mailhost found
        is a SecureMailhost.
        mcc:
            Cc: (carbon copy) field (string or list)
        mbcc:
            Bcc: (blind carbon copy) field (string or list)
        subtype:
            Content subtype of the email e.g. 'plain' for text/plain
        charset:
            Charset used for the email
        """
        mailhost = self._findMailHost()


        if debug:
            if os.environ.get('DEBUG_SENDEMAIL_DEVNULL', None):
                debug = cStringIO.StringIO()
            elif not hasattr(debug, 'write'):
                debug = sys.stdout

            print >>debug, "-------- DEBUG sendEmail() --------"
            print >>debug, "To: %s" % to
            if mcc:
                print >>debug, "CC: %s" % mcc
            if mbcc:
                print >>debug, "BCC: %s" % mbcc
            print >>debug, "From: %s" % fr
            print >>debug, "Subject: %s" % subject


            print >>debug, msg

            return True


        if 1:#try:
            if hasattr(mailhost, 'secureSend'):
                mailhost.secureSend(msg, to, fr, subject,
                       mcc=mcc, mbcc=mbcc, subtype=subtype, charset=charset)
            elif mcc or mbcc:
                raise TypeError, "Only with SecureMailHost can you use mcc and mbcc"
            else:

                header_charset = 'ISO-8859-1'
                # We must choose the body charset manually

                for body_charset in 'US-ASCII', 'ISO-8859-1', 'UTF-8', 'LATIN-1':
                    try:
                        msg.encode(body_charset)
                    except UnicodeError:
                        pass
                    else:
                        break


                # The creation of a body
                # is done here in the sendEmail() function. If the msg
                # is already made into a body, then don't proceed.
                if msg.find('To: %s' % to) + msg.find('From: %s' % fr) > -2:
                    body = msg

                else:
                    body = '\r\n'.join(["From: %s" % fr,
                                        "To: %s" % to,
                                        "Subject: %s" % subject,
                                        "",
                                        msg])

                if isinstance(subject, unicode):
                    # from u'försäljningen' ...
                    subject = email_Header.Header(subject, 'iso-8859-1')
                    subject = str(subject)
                    # ...to '=?iso-8859-1?q?f=F6rs=E4ljningen?='

                    # http://maxischenko.in.ua/blog/entries/103/python-emails-i18n/

                mailhost.send(body, to, fr, subject)
                #mailhost.send(body)
            return True
        else: #except:
            typ, val, tb = sys.exc_info()
            if swallowerrors:
                try:
                    err_log = self.error_log
                    err_log.raising(sys.exc_info())
                except:
                    pass
                _classname = self.__class__.__name__
                _methodname = inspect.stack()[1][3]

                #LOG("%s.%s"%(_classname, _methodname), ERROR,
                #    'Could not send email to %s'%to,
                #    error=sys.exc_info())
                logger.error("Could not send email to %s" % to, exc_info=True)
                return False
            else:
                raise typ, val


    def sendEmailNG(self, msg, to, fr, subject, html_msg=None,
                  mcc=None, mbcc=None,
                  swallowerrors=False, debug=None,
                  charset='iso-8859-1',
                  ):
        """ send email directly via SMTPLib without using mailhost. However,
        take the SMTP server address from the mailhost.

        This method comes from inspiration from
        http://mg.pov.lt/blog/unicode-emails-in-python.html
        where msg, to, fr, subject are expected to be unicode but works as
        ASCII too.
        """

        if 1:#try:

            header_charset = charset

            # We must choose the body charset manually
            try:
                msg.encode(charset)
                body_charset = charset
            except UnicodeError:
                # need to guess it
                for body_charset in charset, 'us-ascii', 'iso-8859-1', 'utf-8':
                    try:
                        msg.encode(body_charset)
                    except UnicodeError:
                        pass
                    else:
                        break

            # Split real name (which is optional) and email address parts
            fr_name, fr_addr = parseaddr(fr)
            to_name, to_addr = parseaddr(to)


            # We must always pass Unicode strings to Header, otherwise it will
            # use RFC 2047 encoding even on plain ASCII strings.
            fr_name = str(Header(unicode(fr_name), header_charset))
            to_name = str(Header(unicode(to_name), header_charset))


            # Make sure email addresses do not contain non-ASCII characters
            fr_addr = fr_addr.encode('ascii')
            to_addr = to_addr.encode('ascii')

            # Create the message ('plain' stands for Content-Type: text/plain)
            try:
                msg_encoded = msg.encode(body_charset)
            except UnicodeDecodeError:
                if isinstance(msg, str):
                    try:
                        msg_encoded = unicode(msg, body_charset).encode(body_charset)
                    except UnicodeDecodeError:
                        logger.warn("Unable to encode msg (type=%r, body_charset=%s)" %\
                            (type(msg), body_charset),
                            exc_info=True)
                        msg_encoded = Utils.internationalizeID(msg)

                else:
                    logger.warn("Unable to encode msg (type=%r, body_charset=%s)" %\
                            (type(msg), body_charset),
                            exc_info=True)
                    msg_encoded = Utils.internationalizeID(msg)

            if html_msg is not None:
                try:
                    html_msg_encoded = html_msg.encode(body_charset)
                except UnicodeDecodeError:
                    if isinstance(html_msg, str):
                        try:
                            html_msg_encoded = unicode(html_msg, body_charset).encode(body_charset)
                        except UnicodeDecodeError:
                            logger.warn("Unable to encode html_msg (type=%r, body_charset=%s)" %\
                                (type(html_msg), body_charset),
                                exc_info=True)
                            html_msg_encoded = Utils.internationalizeID(html_msg)

                    else:
                        logger.warn("Unable to encode html_msg (type=%r, body_charset=%s)" %\
                                (type(html_msg), body_charset),
                                exc_info=True)
                        html_msg_encoded = Utils.internationalizeID(html_msg)

            if html_msg is not None:
                message = MIMEMultipart('related')
                message['From'] = formataddr((fr_name, fr_addr))
                message['To'] = formataddr((to_name, to_addr))
                message['Subject'] = Header(unicode(subject), header_charset)
                message.preamble = 'This is a multi-part message in MIME format.'

                # Encapsulate the plain and HTML versions of the message body in an
                # 'alternative' part, so message agents can decide which they want to display.
                msgAlternative = MIMEMultipart('alternative')
                message.attach(msgAlternative)

                if msg:
                    msgText = MIMEText(msg_encoded, 'plain', body_charset)
                    msgAlternative.attach(msgText)

                # We reference the image in the IMG SRC attribute by the ID we give it below
                msgText = MIMEText(html_msg_encoded, 'html', body_charset)
                msgAlternative.attach(msgText)

            else:
                message = MIMEText(msg_encoded, 'plain', body_charset)
                message['From'] = formataddr((fr_name, fr_addr))
                message['To'] = formataddr((to_name, to_addr))
                message['Subject'] = Header(unicode(subject), header_charset)


            if debug:
                close_debug_after = False

                if isinstance(debug, basestring) and os.path.isdir(debug):
                    filename = '%s.eml' % strftime('%Y%m%d%H%M%S')
                    c = 0
                    while os.path.isfile(os.path.join(debug, filename)):
                        c += 1
                        filename = '%s-%d.eml' % (strftime('%Y%m%d%H%M%S'), c)
                    debug = open(os.path.join(debug, filename), 'w')

                    close_debug_after = True

                elif isinstance(debug, basestring) and os.path.isfile(debug):
                    debug = open(debug, 'a')
                    close_debug_after = True

                elif os.environ.get('DEBUG_SENDEMAIL_DEVNULL', None):
                    debug = cStringIO.StringIO()
                elif not hasattr(debug, 'write'):
                    debug = sys.stdout

                def w(x):
                    try:
                        debug.write(x)
                    except UnicodeEncodeError:
                        debug.write(x.encode('ascii','replace'))
                    debug.write('\n')

                w(message.as_string())

                if close_debug_after:
                    debug.close()

            else:
                mailhost = self._findMailHost()
                # We like to do our own (more unicode sensitive) munging of headers and
                # stuff but like to use the mailhost to do the actual network sending.
                mailhost._send(fr_addr, to_addr, message.as_string())

            return True
        else: #except:
            typ, val, tb = sys.exc_info()
            if swallowerrors:
                try:
                    err_log = self.error_log
                    err_log.raising(sys.exc_info())
                except:
                    pass
                _classname = self.__class__.__name__
                _methodname = inspect.stack()[1][3]

                #LOG("%s.%s"%(_classname, _methodname), ERROR,
                #    'Could not send email to %s'%to,
                #    error=sys.exc_info())
                logger.error("Could not send email to %s" % to, exc_info=True)
                return False
            else:
                raise typ, val



    def _findMailHost(self):
        """ find a suitable MailHost object and return it. """
        # root instance object of issuetracker
        if hasattr(self, 'getRoot'):
            root = self.getRoot()
        else:
            root = self

        # root instance object but without deeper acquisition
        rootbase = getattr(root, 'aq_base', root)

        ## Notice the order of this if-statement.

        # 1. 'MailHost' explicitly in the issuetrackerroot
        # (would fail if the MailHost is defined "deeper")
        if hasattr(rootbase, 'MailHost'):
            mailhost = self.MailHost

        # 2. 'SecureMailHost' explicitly in the issuetrackerroot
        # (would fail if the SecureMailHost is defined "deeper")
        elif hasattr(rootbase, 'SecureMailHost'):
            mailhost = self.SecureMailHost

        # 3. Any 'MailHost' in acquisition
        elif hasattr(self, 'MailHost'):
            mailhost = self.MailHost

        # 4. Any 'SecureMailHost' in acquisition
        elif hasattr(self, 'SecureMailHost'):
            mailhost = self.SecureMailHost

        else: # desperate search
            all_mailhosts = self.superValues(['Secure Mail Host', 'Mail Host'])
            if all_mailhosts:
                mailhost = all_mailhosts[0] # first one
            else:
                raise "AttributeError", "MailHost object not found"

        return mailhost



    #------------------------------------------------------------------------
    #
    # Quoting
    #

    def tex_quote(self, *a, **k):
        return apply(Utils.tex_quote, a, k)

    def tag_quote(self, *a, **k):
        return apply(Utils.tag_quote, a, k)

    def safe_html_quote(self, *a, **k):
        return apply(Utils.safe_html_quote, a, k)

    def html_entity_fixer(self, *a, **k):
        return apply(Utils.html_entity_fixer, a, k)


    #------------------------------------------------------------------------
    #
    # Randomness
    #

    def getRandomString(self, *a, **k):
        return apply(Utils.getRandomString, a, k)


    #------------------------------------------------------------------------
    #
    # Sequences, lists
    #

    def insensitiveRemove(self, *a, **k):
        return apply(Utils.insensitiveRemove, a, k)

    def insensitiveIN(self, *a, **k):
        return apply(Utils.insensitiveIN, a, k)

    def listintersection(self, *a, **k):
        return apply(Utils.listintersection, a, k)

    def mergeEnglishList(self, *a, **k):
        return apply(Utils.mergeEnglishList, a, k)

    def uniqify(self, *a, **k):
        return apply(Utils.uniqify, a, k)

    def moveUpListelement(self, *a, **k):
        return apply(Utils.moveUpListelement, a, k)

    def anyTrue(self, *a, **k):
        return apply(Utils.anyTrue, a, k)

    def anyFalse(self, *a, **k):
        return apply(Utils.anyFalse, a, k)


    #------------------------------------------------------------------------
    #
    # HTML handling
    #

    def dehtmlify(self, *a, **k):
        return apply(Utils.dehtmlify, a, k)


    #------------------------------------------------------------------------
    #
    # String enhancing
    #

    def LineIndent(self, *a, **k):
        return apply(Utils.LineIndent, a, k)

    def safeId(self, *a, **k):
        return apply(Utils.safeId, a, k)

    def banner(self, *a, **k):
        return apply(Utils.banner, a, k)

    def normalizeMobileNumber(self, *a, **k):
        return apply(Utils.normalizeMobileNumber, a, k)

    def ss(self, *a, **k):
        return apply(Utils.ss, a, k)

    def encodeEmailString(self, *a, **k):
        return apply(Utils.encodeEmailString, a, k)

    def encodeEmailString2(self, *a, **k):
        return apply(Utils.encodeEmailString2, a, k)

    def unicodify(self, *a, **k):
        return apply(Utils.unicodify, a, k)


    #------------------------------------------------------------------------
    #
    # Booleanism
    #

    def niceboolean(self, *a, **k):
        return apply(Utils.niceboolean, a, k)

    def isOrdinalth(self, *a, **k):
        return apply(Utils.isOrdinalth, a, k)

    def typelessEqual(self, *a, **k):
        return apply(Utils.typelessEqual, a, k)

    def same_type(self, *a, **k):
        return apply(Utils.same_type, a, k)

    def safebool(self, *a, **k):
        return apply(Utils.safebool, a, k)

    def isValidUploadFile(self, fileupload):
        """ return true if the uploaded file has a name and has content """
        # taken from MExpenses/Expense.py
        if hasattr(fileupload, 'filename'):
            if getattr(fileupload, 'filename').strip():
                # read 1 byte
                if fileupload.read(1) == "":
                    fileupload.seek(0) #rewind file
                else:
                    fileupload.seek(0) #rewind file
                    return True
        return False


    #------------------------------------------------------------------------
    #
    # Showers, converters, nicifiers
    #

    def ShowText(self, *a, **k):
        return apply(Utils.ShowText, a, k)

    def ShowFilesize(self, *a, **k):
        return apply(Utils.ShowFilesize, a, k)

    def formatFloat(self, *a, **k):
        return apply(Utils.formatFloat, a, k)

    def highlightQ(self, *a, **k):
        return apply(Utils.highlightQ, a, k)

    def addhrefs2Text(self, *a, **k):
        return apply(addhrefs.addhrefs, a, k)




    #------------------------------------------------------------------------
    #
    # Misc headers
    #

    def getContentType(self, charset, value='text/html',
                       set_header=True):
        """ set the content type """
        ct = '%s; charset=%s' % (value, charset)
        if set_header:
            self.REQUEST.RESPONSE.setHeader('Content-Type',ct)
        return ct

# To read more about staticmethod() see:
# https://planet.fry-it.com/peter/606

#------------------------------------------------------------------------
#
# Date testing, comparing, modifying
#

_FriedBase.somedate2DateTime = staticmethod(Utils.somedate2DateTime)
_FriedBase.timeSince = staticmethod(Utils.timeSince)

#------------------------------------------------------------------------
#
# Validators, checkers
#

_FriedBase.ValidEmailAddress = staticmethod(Utils.ValidEmailAddress)
_FriedBase.ValidMobileNumber = staticmethod(Utils.ValidMobileNumber)
_FriedBase.ValidDate = staticmethod(Utils.ValidDate)



class _FolderBase(Folder.Folder, Persistent, _FriedBase):
    def __init__(self):
        pass

class _OrderedFolderBase(OrderedFolder.OrderedFolder, Persistent, _FriedBase):
    pass

class _BTreeFolder2Base(BTreeFolder2, _FriedBase):
    pass

class _ItemBase(SimpleItem.SimpleItem, Persistent, _FriedBase):
    def __init__(self):
        pass

#-----------------------------------------------------------------------------
#
# Now the interesting things begin.
# Below are the classes that you can import and subclass
#


class HomepageBaseCatalogAware(_FolderBase, CatalogAware):
    """ Useful Homepage base class with CatalogAware support """
    pass

class HomepageOrderedBaseCatalogAware(_OrderedFolderBase, CatalogAware):
    """ Useful Homepage Ordered base class with CatalogAware support """
    pass

class HomepageBTreeBaseCatalogAware(_BTreeFolder2Base, CatalogAware):
    """ Useful Homepage base class with CatalogAware support with support
    for thousands of sub objects """
    pass

class HomepageBase(_FolderBase):
    """ Useful Homepage base class without CatalogAware support """
    pass

class HomepageOrderedBase(_OrderedFolderBase):
    """ Useful Homepage base class without CatalogAware support and Ordered support """
    pass

class HomepageBTreeBase(_BTreeFolder2Base):
    """ Useful Homepage base class without CatalogAware support with support
    for thousands of sub objects """
    pass

class SimpleItemBaseCatalogAware(_ItemBase, CatalogAware):
    """ Useful for simple non-folderish items with CatalogAware support """

    def manage_afterAdd(self, item, container):
        _ItemBase.manage_afterAdd(self, item, container)
        CatalogAware.manage_afterAdd(self, item, container)

    def manage_beforeDelete(self, item, container):
        _ItemBase.manage_beforeDelete(self, item, container)
        CatalogAware.manage_beforeDelete(self, item, container)

    def manage_afterClone(self, item):
        _ItemBase.manage_afterClone(self, item)
        CatalogAware.manage_afterClone(self, item)

    def DestinationURL(self):
        """
        Used to correctly get path for catalogging.
        Method ZCatalog.CatalogAwarness.url can call this method
        if defined to extract url instead of absolute_url which
        doesn't include folders that are hidden by domain name.
        """
        return '/'.join( self.getPhysicalPath()[:-1] )

class SimpleItemBase(_ItemBase):
    """ Useful for simple non-folderish items without CatalogAware support """
    pass

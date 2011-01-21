# -*- coding: iso-8859-1 -*
##
## (c) Fry-IT, www.fry-it.com
## <peter@fry-it.com>
##

# python
import os, sys, re


# Other Zope products
from Utils import html_quote, niceboolean, unicodify

__version__='1.4'

#------------------------------------------------------------------------------

class InputwidgetTypeError(Exception):
    """ happens when the type_ passed to the inputwidgry functions doesn't
    add up. """
    pass

class InputwidgetValueError(Exception):
    """ happens when the value passed to the inputwidgry functions doesn't
    add up. """
    pass

class InputwidgetNameError(Exception):
    """ happens when the value passed to the inputwidgry functions doesn't
    add up. """
    pass

#------------------------------------------------------------------------------
class InputWidgets:


    def inputwidgetTR(self, name, value=None, label=None,
                      mandatory=False, optional=False,
                      sup=None, sub=None,
                      type_=None, class_=None, **kw):
        """
        Return a chunk of HTML like this:
        <tr>
          <td><label for="$id">$label:</label></td>
          <td><input ... /></td>
        </tr>
        """
        template = u'<tr>\n\t<td><label for="%(nameid)s">%(label)s:%(mandot)s%(subsup)s</label></td>\n'\
                   u'\t<td>%(input_part)s</td>\n</tr>'
        return self._inputwidget_by_template(template, name, value=value,
                                             label=label, mandatory=mandatory,
                                             optional=optional,
                                             sub=sub, sup=sup,
                                             type_=type_, class_=class_, **kw)


    def inputwidgetDT(self, name, value=None, label=None,
                      mandatory=False, optional=False,
                      sub=None, sup=None,
                      type_=None, class_=None, **kw):
        """
        Return a chunk of HTML like this:
        <dt><label for="$id">$label:</label></dt>
        <dd><input ... /></dd>
        """
        template = u'<dt><label for="%(nameid)s">%(label)s:%(mandot)s%(optional)s%(subsup)s</label></dt>\n'\
                   u'<dd>%(input_part)s</dd>'
        return self._inputwidget_by_template(template, name, value=value,
                                            label=label, mandatory=mandatory,
                                            optional=optional,
                                            type_=type_, class_=class_, **kw)


    def _inputwidget_by_template(self, template, name,
                                 value=None, label=None,
                                 mandatory=False, optional=False,
                                 sub=None, sup=None,
                                 type_=None, class_=None, **kw):

        unicode_encoding = kw.get('unicode_encoding',
                               getattr(self, 'UNICODE_ENCODING', 'UTF-8'))

        # If the name passed to this function is 'title:latin1:ustring'
        # or 'price:float', create a new variable called name_full and change
        # the original variable name.
        name_full = name
        if name.find(':') > -1:
            name_full = name
            name = name_full.split(':')[0]

        if len(name_full.split(':')) == 2 and name_full.split(':')[1] in ('ustring','utext'):
            # lazy! You didn't include the encoding
            name_full = name_full.split(':')[0] + ':%s:' % unicode_encoding + name_full.split(':')[1]

        input_part = self.inputwidget(name_full, value, type_=type_, class_=class_,
                                      **kw)

        if label is None:
            label = self._name2label(name)

        def isBiggerThan1Int(x):
            try:
                return int(x) > 1
            except ValueError:
                return False
        if isBiggerThan1Int(mandatory):
            tmpl = u' <span class="mandatory mandatory-%s">%s</span>'
            note = u'*' * int(mandatory)
            #if int(mandatory) == 4:
            #    note = u'&dagger;'
            #elif int(mandatory) == 5:
            #    note = u'&Dagger;'
            mandot = tmpl % (mandatory, note)
        elif mandatory:
            mandot = u' <span class="mandatory">*</span>'
        else:
            mandot = u''

        if sub:
            subsup = '<sub>%s</sub>' % sub
        elif sup:
            subsup = '<sup>%s</sup>' % sup
        else:
            subsup = ''

        if isinstance(optional, basestring):
            # keep 'optional' the way it is
            optional = unicodify(optional)
            if optional.startswith('(') and optional.startswith(')'):
                optional = optional[1:-1]
            optional = u' <span class="optional">(%s)</span>' % unicodify(optional)
        elif bool(optional):
            optional = u' <span class="optional">(optional)</span>'
        else:
            optional = u''

        nameid = self._name2nameID(name)
        data = dict(nameid=nameid, input_part=input_part, label=label,
                    mandot=mandot, optional=optional, subsup=subsup)
        return template % data


    def inputwidget(self, name, value=None, type_=None, class_=None,
                    options=None, **kw):
        """ Return the input part as a chunk of HTML. Most cases it's just an
        <input /> tag but this can be different depending on the value of
        type_. For example, if type_=='textarea' return a <textarea> tags
        etc.
        """

        unicode_encoding = kw.get('unicode_encoding',
                               getattr(self, 'UNICODE_ENCODING', 'UTF-8'))

        # If the name passed to this function is 'title:latin1:ustring'
        # or 'price:float', create a new variable called name_full and change
        # the original variable name.
        name_full = name
        if name.find(':') > -1:
            name_full = name
            name = name_full.split(':')[0]

        if len(name_full.split(':')) == 2 and name_full.split(':')[1] in ('ustring','utext'):
            # lazy! You didn't include the encoding
            name_full = name_full.split(':')[0] + ':%s:' % unicode_encoding + name_full.split(':')[1]

        # special case magic which saves a lot of typing the template code
        if value is None:
            # assume that they mean the REQUEST object
            value = self.REQUEST

        if hasattr(value, 'has_key') and hasattr(value, 'get'):
            # this means that the actual value wasn't given to us.
            # We were given a dictionary which we can dig through
            # ourselfs. If we end up here, it's quite likely that the
            # user called inputwidget() like this:
            #   here.inputwidget('first_name', request)
            if value.get(name) is not None:
                # I know this looks odd but it makes perfect sense :)
                value = value[name]
            else:
                # the variable wasn't available in this dictionary. The
                # default value will now depend on the type_
                if type_ in (None, u'text', u'textarea', u'password', u'file',
                             u'hidden'):
                    # assume string
                    value = ''
                elif type_ == 'checkbox':
                    value = False
                elif type_ == 'radio':
                    value = ''
                else:
                    raise InputwidgetTypeError, \
                    "Invalid type_. Can't guess default value"

        # Now that we've fixed the value for the lazy people who just
        # send a dict we can do some ...
        # ...some basic validation
        if name.strip() != name:
            raise InputwidgetNameError, "Name not stripped"

        if not name.strip():
            raise InputwidgetNameError, "Name blank"

        if type_ in (u'radio',):
            # the value can't be a list
            if isinstance(value, (list, tuple)):
                raise InputwidgetValueError, \
                "For radio input you can't make the value a list"

            # you can't have a multiple parameter to these
            if kw.get('multiple'):
                raise InputwidgetTypeError, "Can't have multiple on type_ radio"

        # check that the type_ is a recognized one
        if type_ not in (None, u'text', u'password', u'file', u'hidden', u'radio',
                         u'checkbox', u'textarea', u'select'):
            raise InputwidgetTypeError, "Unrecognized type_ option %r" % type_

        ##
        ## Before we start rendering it, we might want to make things
        ## smoother by being clever. Hopefully the code speaks for itself.
        ##


        if not kw.has_key(u'size') and not options:
            if type_ in (None, 'text') and len(unicode(value)) < 5:
                if isinstance(value, (int, float)):
                    kw[u'size'] = 5

        if type_ == u'textarea':
            if not kw.has_key(u'rows'):
                kw[u'rows'] = 10
            if not kw.has_key(u'cols'):
                kw[u'cols'] = 70

        if type_ == u'checkbox':
            if niceboolean(value):
                value = "1"
                kw[u'checked'] = u'checked'
            else:
                value = "1"


        # Check for submiterrors
        error_message = ''
        if self.REQUEST.get('submiterrors', {}).get(name):
            class_ = u"inputerror"
            message = self.REQUEST.get('submiterrors').get(name)
            error_message = u'<span class="submiterror">%s</span><br/>'%\
                             html_quote(message)

        if class_ is not None:
            kw[u'class'] = class_

        if kw.get(u'class') and isinstance(kw.get(u'class'), (list, tuple)):
            kw[u'class'] = ' '.join(kw[u'class'])


        # Decide and populate the right template
        if options and isinstance(options, (list, tuple)) and type_ not in ('radio','checkbox'):
            template = u'<select name="%(name)s" id="%(nameid)s" '
            html = template % dict(name=name_full, nameid=self._name2nameID(name))

        elif type_ == 'checkbox' and options and isinstance(options, (list, tuple)):
            html = ''

        elif type_ in (None, u'text', u'password', u'file', u'hidden', u'checkbox'):
            template = u'<input type="%(type)s" id="%(nameid)s" name="%(name)s" value="%(value)s" '
            if type_ is None:
                type_ = u'text'
            html = template % dict(type=type_, name=name_full, value=value,
                                   nameid=self._name2nameID(name))

        elif type_ == u'textarea':
            template = u'<textarea name="%(name)s" id="%(nameid)s" '
            html = template % dict(name=name_full, nameid=self._name2nameID(name))

        elif type_ == 'radio':
            html = ''

        if kw.get(u'pretext'):
            html = kw.get(u'pretext') + html
            kw.pop(u'pretext')

        if 'readonly' in kw:
            # to allow this to be None which can happen if you do this:
            # <td tal:content="structure python:here.inputwidget(...,
            #                             readonly=test(here.check_readonly()))
            if kw.get('readonly'):
                kw['readonly'] = 'readonly'
            else:
                del kw['readonly']

        if type_ != 'radio':
            for key, value_ in kw.items():
                if key.endswith('__'):
                    # special
                    continue
                if key == u'posttext':
                    continue
                if key == 'multiple':
                    value_ = 'multiple'
                html += u'%s="%s" ' % (key, value_)



        def isEqual(x, y):
            """ compare x and y and be aware of the careful_int_match__ """
            if x == y:
                return True

            if kw.get('careful_int_match__'):
                try:
                    return int(x) == int(y)
                except ValueError, TypeError:
                    pass

            if kw.get('careful_float_match__'):
                try:
                    return float(x) == float(y)
                except ValueError, TypeError:
                    pass

            return False

        def isIn(x, yyy):
            if x in yyy:
                return True

            if kw.get('careful_int_match__'):
                try:
                    return int(x) in [int(e) for e in yyy]
                except ValueError, TypeError:
                    pass

            if kw.get('careful_float_match__'):
                try:
                    return float(x) in [float(e) for e in yyy]
                except ValueError, TypeError:
                    pass

            return False


        # wrap up

        if type_ == u'textarea':
            html = html.strip()+ u'>'
            html += html_quote(value)
            html += u'</textarea>'
        elif type_ in ('radio','checkbox') and options and isinstance(options, (list, tuple)):
            c = 0
            for option in options:
                valueid = self._name2nameID(name)+'_%s' % c
                c += 1
                if isinstance(option, (tuple, list)):
                    option, label = option
                elif isinstance(option, dict):
                    option, label = option['key'], option['value']
                else:
                    option, label = option, option

                if isEqual(option, value):
                    template = u'<input type="%(type_)s" name="%(name)s" id="%(valueid)s" value="%(value)s" checked="checked" '
                else:
                    template = u'<input type="%(type_)s" name="%(name)s" id="%(valueid)s" value="%(value)s" '
                html += template % dict(name=name_full, value=option, valueid=valueid, type_=type_)
                for key, value_ in kw.items():
                    if key.endswith('__'):
                        # special parameter
                        continue
                    if key in (u'posttext', u'multiple'):
                        continue
                    html += u'%s="%s" ' % (key, value_)

                html = html.strip() + u' />'
                html += '<label style="display:inline" for="%(valueid)s">%(label)s</label>' %\
                   dict(valueid=valueid, label=label)
                html += kw.get('radio_label_delimiter__','<br/>')
            html = html.strip()

        elif options and isinstance(options, (list, tuple)):
            html = html.strip() + u'>\n'
            preval = value
            if isinstance(preval, (tuple, list)) and not kw.get(u'multiple'):
                raise InputwidgetValueError, "Pass multiple='multiple' if the value is an iterable"
            for option in options:

                if isinstance(option, (tuple, list)):
                    option, label = option
                elif isinstance(option, dict):
                    option, label = option['key'], option['value']
                else:
                    option, label = option, option

                if isEqual(option, preval) or (kw.get(u'multiple') and option in preval):
                    html += u'<option value="%s" selected="selected">%s</option>\n'%\
                             (option, label)
                else:
                    html += u'<option value="%s">%s</option>\n' % (option, label)

            html += u'</select>'
        elif type_ == 'select':
            # The type was 'select' but there weren't any options!
            raise ValueError, "Type 'select' but no options provided"
        else:
            if type_ != 'radio':
                html += u'/>'

        if kw.get(u'posttext'):
            html += '<span class="input-posttext">%s</span>' % kw.get(u'posttext')


        # error_message is in most cases a empty string
        html += error_message

        return html


    def _name2nameID(self, name):
        """ return a suitable id based on the name """

        return u'id_%s' % name

    def _name2label(self, name):
        """ if name is 'first_name' return 'First name' """
        return name.replace('_',' ').capitalize()

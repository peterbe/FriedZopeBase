#!/usr/bin/python 
"""
 postcodeeverywhere.py
 Fry-IT Ltd. (c) 2007
 by Peter Bengtsson
 
 This module lets you do lookups on AFD's postcodeeverywhere XML
 server. 
 
 The Postcodefinder class has these important methods:
     - AddressLookup
     
"""
import re, sys
from urllib import urlopen, urlencode

from cStringIO import StringIO

try:
    import cElementTree as ElementTree
except ImportError:
    print >>sys.stderr, "cElementTree not installed"
    from elementtree import ElementTree

try:
    from ukpostcode import parse_uk_postcode
except ImportError:
    def parse_uk_postcode(s):
        if len(s.split()) != 2:
            raise ValueError, "use ukpostcode instead!"
        return s.split()
    

COUNTY_EQUIVS = {
    'Bath and North East Somerset':'Somerset',
    'County of Herefordshire':'Herefordshire',
    
    }


def getCountyEquivalent(county):
    if COUNTY_EQUIVS.has_key(county):
        return COUNTY_EQUIVS.get(county)
    elif county.lower() in [x.lower() for x in COUNTY_EQUIVS.keys()]:
        county = county.lower()
        for k,v in COUNTY_EQUIVS.items():
            if k.lower()==county:
                return v
    else:
        return county
    
SERVER = "pce.afd.co.uk"
SERIAL = "811771"
PASSWORD = "test123"
USERID = "FRYIT01"
COUNTYTYPE = "0"
#0 Omit Counties
#1 Postal Counties
#2 Abbreviated Postal Counties
#3 Postal Including Optional Counties
#4 Abbreviated Postal Including Optional Counties
#5 Traditional Counties
#6 Administrative Counties




def _clearUpXMLString(s):
    """ make sure everything between >...< tags are things we recognize """
    ok=r'\W' # [^a-zA-Z0-9_]
    alsook = [',','.',"'",'"',' ','\n','\r','&',';']
    regex = re.compile(ok, re.I)
    parts =[]
    for each in s.split('>'):
        if each.rfind('</') > 0:
            t = each[:each.rfind('</')]
            tmp_t = t
            for bad in regex.findall(t):
                if bad and bad not in alsook:
                    t = t.replace(bad,'')
            each = t+each[each.find('</'):]
        parts.append(each)
    return '>'.join(parts)
    


class ParameterError(Exception):
    """ when some parameter is wrong """
    pass


#------------------------------------------------------------------------------------

class Postcodefinder:
    def __init__(self, server=SERVER, serial=SERIAL, password=PASSWORD, 
                 userid=USERID, countytype=COUNTYTYPE):
        self.server = server
        self.serial = serial
        self.password = password
        self.userid = userid
        self.countytype = countytype
        
    def _getQS(self, **kwd):
        autoinclude = {'serial':self.serial,
                       'password':self.password,
                       'userid':self.userid,
                       'countytype':self.countytype}
        
        for k,v in autoinclude.items():
            if not kwd.has_key(k):
                kwd[k] = v
        
        return urlencode(kwd)

    def getURL(self, page, **kwd):
        """ return full URL """
        u = 'http://%s/%s?'%(self.server, page)
        u += apply(self._getQS, (), kwd)
        return u

    def AddressLookup(self, postcode=None, postkey=None, 
                      property=None, countytype=None):
        """ Takes either a postcode and optional property or a postkey and 
        returns a single address record.
        """
        if countytype is None:
            countytype = self.countytype
            
        if postcode is not None:
            kw = {'postcode':postcode}
        elif postkey is not None:
            kw = {'postkey':postkey}
        else:
            raise ParameterError, "Neither postcode or postkey :("
            
        kw['countytype'] = countytype
        if property:
            kw['property'] = property
            
        url = self.getURL('addresslookup.pce', **kw)

        page = urlopen(url)
        xmlstring = page.read()
        xmlfile = StringIO(xmlstring)
        try:
            doc = ElementTree.ElementTree(file=xmlfile)
        except:
            print >>sys.stderr, "Failed to parse XML file"
            return {}
        
        root = doc.getroot()
        record = {}
        conversions = {'GridEast':'grid_ref_x',
                       'GridNorth':'grid_ref_y',
                       'Street':'street',
                       'Town':'town',
                       'County':'county',
                       'Postcode':'postcode',
                       }
        for element in doc.getiterator():
            if element.tag in conversions:
                text = element.text
                if text is not None and text.isdigit():
                    try:
                        text = int(text)
                    except ValueError:
                        pass
                record[conversions.get(element.tag)] = text
                
        if not [x for x in record.values() if x is not None]:
            return {}
        
        if record.get('postcode') == 'Error: Postcode Not Found':
            return {}
                
        return record
    
    
    def AddressFastFind(self, searchterm, countytype=None,
                        max_sub_lookups=3, approximate=False):
        """ return a list of records like this basically
        [AddressLookup(), AddressLookup()]
        """
        if countytype is None:
            countytype = self.countytype
            
        kw = {'fastfind': searchterm}
        kw['countytype'] = countytype
        
        url = self.getURL('addressfastfind.pce', **kw)
        
        page = urlopen(url)
        xmlstring = page.read()
        xmlfile = StringIO(xmlstring)
        try:
            doc = ElementTree.ElementTree(file=xmlfile)
        except:
            print >>sys.stderr, "Failed to parse XML file"
            return []
        
        root = doc.getroot()
        postkeys = []
        for node in root.findall('AddressListItem'):
            for node2 in node.findall('PostKey'):
                if node2.text is not None:
                    postkeys.append(node2.text)		    
                
        records = []
        records_hash_x = {}
        records_hash_y = {}
        if approximate:
            for i in range(0, len(postkeys), max(len(postkeys)/max_sub_lookups, 1)):
                record = self.AddressLookup(postkey=postkeys[i])
                records.append(record)
        else:
            for postkey in postkeys:
                record = self.AddressLookup(postkey=postkey)
                records.append(record)
            
        if approximate:
            # insert one record in the begining whose grid refs is the
            # average of all other grid refs
            
            all_x = [x['grid_ref_x'] for x in records]
            all_y = [x['grid_ref_y'] for x in records]
            average_x = int(sum(all_x)/float(len(all_x)))
            average_y = int(sum(all_y)/float(len(all_y)))
            
            r = records[0]

            postcode = r['postcode']
            try:
                postcode, __ = parse_uk_postcode(postcode)
            except ValueError:
                pass

            records.insert(0, dict(postcode=postcode,
                                   grid_ref_x=average_x,
                                   grid_ref_y=average_y,
                                   county=r['county'],
                                   town=r['town']))
                

        keep = []
        for record in records:
            if [x for x in record.values() if x is not None]:
                if 'street' not in record:
                    record['street'] = None
                keep.append(record)
        return keep
            
    def Postcode2Addresses(self, postcode):
        """
	Return list of addresses for postcode
        """            
        kw = {'fastfind': postcode}
        kw['countytype'] = self.countytype
        
        url = self.getURL('addressfastfind.pce', **kw)
        
        page = urlopen(url)
        xmlstring = page.read()
        xmlfile = StringIO(xmlstring)
        try:
            doc = ElementTree.ElementTree(file=xmlfile)
        except:
            print >>sys.stderr, "Failed to parse XML file"
            return []
        
        root = doc.getroot()
        addresses = []
        for node in root.findall('AddressListItem'):
	    for node2 in node.findall('Address'):
		if node2.text is not None:
                    parts = node2.text.split('\t')
                    if len(parts) > 1:
		        addresses.append(parts[1])	     
	return addresses
        
#------------------------------------------------------------------------------------
            

def get_gridref(term, alternatives=1, onlyfullpostcode=0, accurate=0):
    """ wrap class for external scripts """
    finder = Postcodefinder()
    get_g = finder.get_gridref
    if type(term)==type([]):
        results = []
        for t in term:
            result = get_g(term, alternatives=alternatives, 
                           onlyfullpostcode=onlyfullpostcode,
                           accurate=accurate)
            results.append(result)
        return results
    else:
        return get_g(term, alternatives=alternatives,
                         onlyfullpostcode=onlyfullpostcode,
                     accurate=accurate)
            
        
def address_search_postkey(postkey, ret=None):
    """ wrap class for external scripts """
    finder = Postcodefinder()
    return finder.address_search_postkey(postkey, ret=ret)
            

#------------------------------------------------------------------------------------

def test():
    # Run some tests

    ps = [#'ec1v8dd','nonexist',
          #'ox9','ox9 3wh','ox93ep',
          'sw5',
          #'ec1v 8dd','ec1v8dd','ec1v',
          #'sw7','sw7 4ub','sw74ub',
          'ox8 4js', 'ox8',
          ]

    finder = Postcodefinder()
    for p in ps:
        t0 = time.time()
        t='\t'
        if len(p)<7:
            t+='\t'
        print p, "%s-->"%t, finder.get_gridref(p), "  (%s seconds)"%str(round(time.time()-t0, 3))
    
def test2():
    # Run some tests
    
    ls = ['beaconsfield',
          'gerrards cross',
	  'worcester',
	  'coombe',
         ]
    finder = Postcodefinder()
    for l in ls:
        t0 = time.time()
        t='\t'
        if len(l)<7:
            t+='\t'
        print l, "%s-->"%t, finder.get_gridref(l), "  (%s seconds)"%str(round(time.time()-t0, 3))

	
def test_postcodes(postcodelist, geocodes=False):
    finder = Postcodefinder()
    lookup = finder.AddressLookup
    search = finder.AddressFastFind
    for arg in postcodelist:
        r = lookup(postcode=arg)
        if not r:
            r = search(arg)
        yield r
        
	
def test_postcode(postcode, geocodes=False):
    finder = Postcodefinder()
    if geocodes:
        return finder.get_geocode(postcode)
    else:
        return finder.AddressLookup(postcode)
	
	
	
def run():
    """ where the arguments to this script is a comma 
    separated list of postcodes """
    args = ' '.join(sys.argv[1:])
    
    _get_geocodes = False
    if args.find('--geo') > -1:
        _get_geocodes = True
        args = args.replace('--geo','')
        
    
    args = args.split(',')
    args = [x.strip() for x in args if x.strip()]
    if args:
        for each in test_postcodes(args):
            print each
	
def run2():
    args = sys.argv[1:]
    
    exactly = False
    if '--exactly' in args:
        exactly = True
        args.remove('--exactly')
    elif '-e' in args:
        exactly = True
        args.remove('-e')
    
    if ' '.join(args).find(',') > -1:
        args = ' '.join(args).split(',')
    
    args = [x.strip() for x in args if x.strip()]
    
    finder = Postcodefinder()
    search = finder.AddressFastFind
    skip_next = False
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        
        results = search(arg)
        grep_house_number = None
        try:
            if args[i+1].isdigit():
                grep_house_number = args[i+1]
                skip_next = True
        except IndexError:
            pass
        
        for result in results:
            if result['street'] is None:
	    	continue
            if grep_house_number and not result['street'].startswith('%s ' % grep_house_number):
	    	continue
            print '\t'.join([result['street'], result['town'], result['postcode']])
            
        
        #if not exactly and not r:
        #    r = search(arg)
            
    return 0

def run3():
	postcode = ""
	number = ""
	args = ' '.join(sys.argv[1:])
	pcf = re.compile('^.*postcodefrom *= *\"*(.*?)\"*(postcodeto.*$|property.*$|$)')
	pct = re.compile('^.*postcodeto *= *\"*(.*?)\"*(postcodefrom.*$|property.*$|$)')
	prp = re.compile('^.*property *= *\"*(.*?)\"*(postcodefrom.*$|postcodeto.*$|$)')
	m1 = pcf.match(args)
	m2 = pct.match(args)
	m3 = prp.match(args)
	if m1: postcode=m1.group(1)
	if m2: postcode=m2.group(1)
	if m3: number=m3.group(1)
	if postcode <> "":
    		finder = Postcodefinder()
		if number <> "":
			result = finder.AddressLookup(postcode=postcode,property=number)
			if result['street'] is not None:
				print '\t'.join([result['street'], result['town'], result['postcode']])
		else :
			results = finder.AddressFastFind(postcode)
			for result in results:
				if result['street'] is None: continue
				print '\t'.join([result['street'], result['town'], result['postcode']])
	return 0

if __name__ == '__main__':
    import time
    #test()
    #test2()
    #run()
    sys.exit(run3())
    



COUNTIES = ['Aberdeenshire',
 'Anglesey',
 'Angus',
 'Argyll & Bute',
 'Ayrshire',
 'Bedfordshire',
 'Berkshire',
 'Blaenau Gwent',
 'Bridgend',
 'Bristol',
 'Buckinghamshire',
 'Caerphilly',
 'Cambridgeshire',
 'Cardiff',
 'Carmarthenshire',
 'Ceredigion',
 'Channel Islands',
 'Cheshire',
 'Clackmannanshire',
 'Conwy',
 'Cornwall',
 'County Antrim',
 'County Armagh',
 'County Down',
 'County Fermanagh',
 'County Londonderry',
 'County Tyrone',
 'Cumbria',
 'Denbighshire',
 'Derbyshire',
 'Devon',
 'Dorset',
 'Dumfries & Galloway',
 'Dunbartonshire',
 'Dundee',
 'Durham',
 'East Lothian',
 'Edinburgh',
 'Essex',
 'Falkirk',
 'Fife',
 'Flintshire',
 'Glasgow',
 'Gloucestershire',
 'Greater London',
 'Greater Manchester',
 'Gwynedd',
 'Hampshire',
 'Herefordshire',
 'Hertfordshire',
 'Highland',
 'Inverclyde',
 'Isle of Man',
 'Isle of Wight',
 'Isles of Scilly',
 'Kent',
 'Lanarkshire',
 'Lancashire',
 'Leicestershire',
 'Lincolnshire',
 'London',
 'Merseyside',
 'Merthyr Tydfil',
 'Midlothian',
 'Monmouthshire',
 'Moray',
 'Neath & Port Talbot',
 'Norfolk',
 'Northamptonshire',
 'Northumberland',
 'Nottinghamshire',
 'Oxfordshire',
 'Pembrokeshire',
 'Perth & Kinross',
 'Powys',
 'Renfrewshire',
 'Rhondda Cynon Taff',
 'Scottish Borders',
 'Scottish Islands',
 'Shropshire',
 'Somerset',
 'Staffordshire',
 'Stirling',
 'Suffolk',
 'Surrey',
 'Sussex',
 'Swansea',
 'Torfaen',
 'Tyne & Wear',
 'Vale of Glamorgan',
 'Warwickshire',
 'West Lothian',
 'West Midlands',
 'Wiltshire',
 'Worcestershire',
 'Wrexham',
 'Yorkshire']

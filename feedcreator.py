from types import InstanceType
import time

RSS_START="""
<?xml version="1.0" encoding="ISO-8859-1"?>
<rdf:RDF
 xmlns="http://purl.org/rss/1.0/"
 xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:sy="http://purl.org/rss/1.0/modules/syndication/"
>
<channel rdf:about="%(abouturl)s">
  <title>%(title)s</title>
  <link>%(webpage)s</link>
  <description>%(description)s</description>
  <dc:language>%(language)s</dc:language>
  <dc:publisher>%(webmaster)s</dc:publisher>
"""
#" bug in jed editor (peter)

RSS_END='</rdf:RDF>'
RDF_LI_ITEM = '  <rdf:li rdf:resource="%(url)s" />'
RDF_ITEM = """
<item rdf:about="%(abouturl)s">
  <title>%(title)s</title>
  <description>%(description)s</description>
  <link>%(link)s</link>
  <dc:subject>%(subject)s</dc:subject>
  <dc:date>%(date)s</dc:date>
  %(extras)s
</item>
"""


class Item:
    def __init__(self, title, link, description='', subject='',
                 abouturl=None, date=None, timestamp=None, **extras):
        
        if not date:
            date = time.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        elif hasattr(date, 'strftime'):
            date = date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        if not abouturl:
            abouturl = link
        self.title = title
        self.link = link
        self.description = description
        self.subject = subject
        self.abouturl = abouturl
        self.date = date
        if not timestamp:
            timestamp = time.time()
        self.timestamp = timestamp
        self._extras = extras

    def out(self):
        info = {'extras':''}
        if self._extras:
            for k, v in self._extras.items():
                info['extras'] += "<fry:%s>%s</fry:%s>\n"%(k,v,k)
        for each in ('title','link','description','subject',
                     'abouturl','date'):
            value = getattr(self, each)
            if value.find('<') > -1 or value.find('>') > -1 or value.find('&') > -1:
                value = '<![CDATA[%s]]>' % value
            info[each] = value
        return (RDF_ITEM%(info)).strip()
    __str__=__call__=out
        

class Feed:
    def __init__(self, URL,
                 title='Intranet', 
                 webpage=None, description='', language='en-uk',
                 webmaster='root@localhost',
                 abouturl=None
                 ):
        self.URL = URL
        self.title = title
        if not abouturl:
            abouturl = URL
        self.abouturl = abouturl
        if not webpage:
            webpage = '/'.join(URL.split('/')[:-1])
        self.webpage = webpage
        self.description = description
        self.language = language
        self.webmaster = webmaster        
        self.items = []
        
    def append(self, itemobject):
        """ add one more item object """
        assert type(itemobject)==InstanceType
        assert itemobject.__class__.__name__=='Item'
        items = self.items
        items.append(itemobject)
        self.items = items
        
        
    def out(self):
        """ return the who XML string """
        head_info = {}
        for each in ('abouturl','title','webpage','description',
                     'language','webmaster'):
            head_info[each] = getattr(self, each)
        header = RSS_START%(head_info)
        items_list = ['<items>','<rdf:Seq>']
        all_items = []
        for item in self.items:
            items_list.append(RDF_LI_ITEM%{'url':item.link})
            all_items.append(str(item))
            
        all_items = '\n\n'.join(all_items)
            
        items_list.extend(['</rdf:Seq>','</items>'])
        items_list = '\n'.join(items_list)
        
        return '\n'.join([header, items_list, '</channel>', all_items, RSS_END])

    __str__=__call__=out

    def save(self, filename='intranet.xml'):
        """ save to file """
        open(filename, 'w').write(self.__str__().strip()+'\n')


def test_test1():
    feed = Feed("http://www.stuff.com/rss.xml",
                "Stuff", description="Bla bla bla",
                webmaster="peter@fry-it.com")
    
    item1 = Item("Gozilla", "http://news.com/gozilla",
                 "Gozilla is in town rampaging and destroying!",
                 "News & Entertainment")
    feed.append(item1)
    item2 = Item("Blondes", "http://sexyblondes.org/page3",
                 "Beautiful tall and volumtious blondes",
                 date="2004-12-13T15:45")
    feed.append(item2)
        

    print feed

if __name__=='__main__':
    test_test1()

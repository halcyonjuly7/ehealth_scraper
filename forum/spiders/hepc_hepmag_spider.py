import scrapy
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors import LinkExtractor
from scrapy.selector import Selector
from forum.items import PostItemsList
import re
import logging
import lxml.html
from lxml.etree import ParserError
from lxml.cssselect import CSSSelector
from bs4 import BeautifulSoup
import urlparse


## LOGGING to file
#import logging
#from scrapy.log import ScrapyFileLogObserver

#logfile = open('testlog.log', 'w')
#log_observer = ScrapyFileLogObserver(logfile, level=logging.DEBUG)
#log_observer.start()


class ForumsSpider(CrawlSpider):
    name = "hepc_hepmag_spider"
    _allowed_domain = {"forums.hepmag.com" }
    start_urls = [
        "http://forums.hepmag.com/index.php?board=31.0"
    ]

    rules = (
            # Rule to go to the single product pages and run the parsing function
            # Excludes links that end in _W.html or _M.html, because they point to 
            # configuration pages that aren't scrapeable (and are mostly redundant anyway)
            Rule(LinkExtractor(
                    restrict_xpaths='//span[contains(@id,"msg_")]/a',
                ), callback='parsePostsList'),
            # Rule to follow arrow to next product grid
            Rule(LinkExtractor(
                    restrict_xpaths='//a[@class="navPages"]',
                    deny=(r'profile',)
                ), follow=True),
        )
    
    def urlRemove(self,url,keyToRemove):
        urlcomponents = urlparse.urlparse(url)
        params=urlparse.parse_qs(urlcomponents.query)
        newparams=""
        for key in params.keys():
            if not key==keyToRemove:
                newparams = newparams+ key+"="+params.get(key)[0]
        urlcomponents.query = newparams
        return urlparse.urlunparse(urlcomponents)

    def cleanText(self,text):
        soup = BeautifulSoup(text,'html.parser')
        text = soup.get_text();
        text = re.sub("( +|\n|\r|\t|\0|\x0b|\xa0|\xbb|\xab)+",' ',text).strip()
        return text 
    
    # https://github.com/scrapy/dirbot/blob/master/dirbot/spiders/dmoz.py
    # https://github.com/scrapy/dirbot/blob/master/dirbot/pipelines.py
    def parsePostsList(self,response):
        try:
            document = lxml.html.fromstring(response.body)
            document.make_links_absolute(base_url=response.url, resolve_base_href=True)
        except ParserError:
            return
        items =[]
        postWrappers = CSSSelector('.post_wrapper')(document)
        for postWrapper in postWrappers:
            post = PostItemsList()
            keyinfo = postWrapper.cssselect(".keyinfo")[0]
            poster = postWrapper.cssselect(".poster")[0]
            post['author'] = poster.xpath("./h4/a/text()")[0]
            post['author_link'] = poster.xpath("./h4/a/@href")[0]
            post['create_date'] = self.cleanText(" ".join(keyinfo.cssselect('.smalltext')[0].xpath("text()")))
            post['topic'] = keyinfo.cssselect('h5')[0].xpath("./a/text()")[0]
            post['post'] = self.cleanText(" ".join(postWrapper.cssselect(".post")[0].xpath("./div/text()")))
            post['url'] = self.urlRemove(response.url,"PHPSESSID")
            items.append(post)
        return items
        


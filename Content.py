# -*- coding: utf-8 -*-
'''
    Torrenter plugin for Kodi
    Copyright (C) 2012 DiMartino

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import abc
import urllib
import urllib2
import cookielib
import re
from StringIO import StringIO
import gzip
import HTMLParser

import Localization


class Content:
    __metaclass__ = abc.ABCMeta

    searchIcon = '/icons/video.png'
    sourceWeight = 1
    cookieJar = None
    baseurl = ''

    def isLabel(self):
        return 'Should search on ruhunt?'

    def isPages(self):
        return False

    def isSort(self):
        return False

    def isScrappable(self):
        return True

    def isInfoLink(self):
        return False

    def isSearchOption(self):
        return True

    category_dict = {
        'sites': ('[B]by Site[/B]',),
        'search': ('[B]Search[/B]',),
        'movies': ('Movies',),
        'rus_movies': ('Russian Movies',),
        'tvshows': ('TV Shows',),
        'cartoons': ('Cartoons',),
        'hot': ('Most Recent',),
        'top': ('Top All Time',),
        'anime': ('Anime',),
        'year': {'year': 'by Year', },
        'genre': {'genre': 'by Genre',
                  'action': ('Action',),
                  'comedy': ('Comedy',),
                  'documentary': ('Documentary',),
                  'drama': ('Drama',),
                  'fantasy': ('Fantasy',),
                  'horror': ('Horror',),
                  'romance': ('Romance',),
                  'thriller': ('Thriller',),
        }
    }

    for y in range(2015, 1970, -1):
        category_dict['year'][str(y)] = (str(y), '/top/y/%s/' % str(y))

    def get_contentList(self, category, subcategory=None, apps_property=None):
        '''
        Retrieve keyword from the input and return a list of tuples:
        filesList.append((
            int(weight),
            int(seeds),
            str(title),
            str(link),
            str(image),
        ))
        '''
        return

    def has_category(self, category, subcategory=None):
        has_category = False
        if not subcategory or subcategory == True:
            if category in self.category_dict.keys():
                has_category = True
        else:
            if category in self.category_dict:
                cat_con = self.category_dict[category]
                if isinstance(cat_con, dict):
                    if subcategory in cat_con.keys():
                        has_category = True
        return has_category

    def get_url(self, category, subcategory, apps_property):
        page=None
        sort=None
        if apps_property:
            page=apps_property.get('page')
            sort=apps_property.get('sort')

        if not subcategory or subcategory == True or category == 'search':
            get = self.category_dict[category]
        else:
            get = self.category_dict[category][subcategory]

        if category == 'search': get = (get[0], get[1] % urllib.quote_plus(subcategory.encode('utf-8')))

        property = self.get_property(category, subcategory)

        if not page or page == 1:
            url = self.baseurl + get[1]
        elif property:
            page_url = property['page'] % (property['second_page'] + ((page - 2) * property['increase']))
            url = self.baseurl + str(page_url)

        if property and property.get('sort'):
            sort_dict=property['sort'][sort]
            if sort_dict.get('url_after'):
                page_url = sort_dict['url_after']
                url = url + page_url
        return url


    def get_property(self, category, subcategory=None):
        has_property = False
        property = {}
        if not subcategory or subcategory == True:
            if category in self.category_dict.keys():
                try:
                    property = self.category_dict[category][2]
                    if isinstance(property, dict):
                        has_property = True
                except:
                    pass
        else:
            if category in self.category_dict:
                cat_con = self.category_dict[category]
                if isinstance(cat_con, dict):
                    if subcategory in cat_con.keys():
                        try:
                            property = cat_con[subcategory][2]
                            if isinstance(property, dict):
                                has_property = True
                        except:
                            pass
        if has_property:
            if category == 'search': property['page'] = property['page'] % urllib.quote_plus(
                subcategory.encode('utf-8'))
            return property


    def makeRequest(self, url, data={}, headers=[]):
        self.cookieJar = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookieJar))
        opener.addheaders = headers
        if 0 < len(data):
            encodedData = urllib.urlencode(data)
        else:
            encodedData = None
        try:
            response = opener.open(url, encodedData)
        except urllib2.HTTPError as e:
            if e.code == 404:
                print '[makeRequest]: Not Found! HTTP Error, e.code=' + str(e.code)
                return
            elif e.code in [503]:
                print '[makeRequest]: Denied, HTTP Error, e.code=' + str(e.code)
                return
            else:
                print '[makeRequest]: HTTP Error, e.code=' + str(e.code)

        if response.info().get('Content-Encoding') == 'gzip':
            buf = StringIO(response.read())
            f = gzip.GzipFile(fileobj=buf)
            response = f.read()
        else:
            response = response.read()
        return response

    htmlCodes = (
        ('&', '&amp;'),
        ('<', '&lt;'),
        ('>', '&gt;'),
        ('"', '&quot;'),
        ("'", '&#39;'),
        (' ', '&nbsp;',),
        ('"', '&laquo;', ),
        ('"', '&raquo;', ),
        ('·', '&#183;',),
        ('e', '&#233;',),
        ('e', '&#232;',),
        ('&', '&#38;',),
        ('u', '&#249;',),
        ('u', '&#250;',),
        ('o', '&#244;',),
        ('u', '&#251;'),
        ('-', '&ndash;'),
    )
    stripPairs = (
        ('<p>', '\n'),
        ('<li>', '\n'),
        ('<br>', '\n'),
        ('<.+?>', ' '),
        ('</.+?>', ' '),
        ( '&nbsp;', ' ',),
        ('&laquo;', '"',),
        ('&raquo;', '"', ),
        ('&ndash;', '-'),
    )

    def unescape(self, string):
        try:
            pars = HTMLParser.HTMLParser()
            return pars.unescape(string)
        except:
            return string

    def stripHtml(self, string):
        for (html, replacement) in self.stripPairs:
            string = re.sub(html, replacement, string)
        return string

    def translate(self, category, subcategory=None):
        if not subcategory:
            if isinstance(self.category_dict.get(category), dict):
                return self.localize(self.category_dict.get(category).get(category))
            else:
                return self.localize(self.category_dict.get(category)[0])
        else:
            return self.localize(self.category_dict.get(category).get(subcategory)[0])

    def localize(self, string):
        if string:
            try:
                return Localization.localize(string)
            except:
                return string
        else:
            return 'Empty string'

    def sizeConvert(self, sizeBytes):
        if long(sizeBytes) >= 1024 * 1024 * 1024:
            size = str(long(sizeBytes) / (1024 * 1024 * 1024)) + 'GB'
        elif long(sizeBytes) >= 1024 * 1024:
            size = str(long(sizeBytes) / (1024 * 1024)) + 'MB'
        elif sizeBytes >= 1024:
            size = str(long(sizeBytes) / 1024) + 'KB'
        else:
            size = str(long(sizeBytes)) + 'B'

        return size
#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import urllib.request  # needed for web requests
import json  # needed for json decoding
import ssl  # needed for web request with SSl
from bs4 import BeautifulSoup  # needed for html analysing


class ftDB():
    # class to abstract the main functionnalitys of the fischertechnik Datenbak

    def __init__(self, url):
        # check whether URL is delivered
        if url == '':
            raise ValueError('No ftDB URL given')
            exit()
        # clean up URL
        if not url.endswith('/'):
            url = url + '/'
        # set URL
        self.base_url = url
        # initialize SSL
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def call_server_json(self, call):
        # download JSON from the server
        print('Loading:' + self.base_url + call)
        # download and decode JSON
        try:
            data = json.loads(urllib.request.urlopen(self.base_url + call, context=self.ctx).read().decode('utf-8'))
            # return data
            return(data)
        except:
            # error
            # return empty dict
            return({})

    def call_server_html(self, call):
        # download html
        print('Loading: ' + self.base_url + call)
        data = urllib.request.urlopen(self.base_url + call, context=self.ctx).read().decode('utf-8', 'replace')
        # return data
        return(data)

    def get_main_page_from_html(self, html):
        # abstract main page from the html
        # initialize bs4 DOM explorer
        dom = BeautifulSoup(html.encode(), 'html.parser', from_encoding='utf-8')
        # find main page
        data = dom.find(None, {'class': 'drn-main-page'}).renderContents()
        # return data
        return(data)

    def fulltext_search(self, search, page=1):
        # fulltext search with page selection in the database
        # generate URL
        call_string = 'api/tickets?fulltext=' + search
        # generate URL for page >1
        if page != 1:
            call_string = call_string + '&page=' + str(page)
        # call server
        data = self.call_server_json(call_string)
        # return data
        return(data)

    def find_string_in_list(self, data, string):
        # help sript for returning list item which contains specific string
        # do for each iten
        for entry in data:
            # check if string is in item
            if string in str(entry):
                # return iten
                return(str(entry))
        # abort if not found
        return(None)

    def get_ticket_data(self, id):
        # get ticket data
        # call server
        web = self.call_server_html('ticket/' + str(id))
        # get main page
        main_page = self.get_main_page_from_html(web)
        # initailize return variable and DOM explorer
        data = {}
        dom = BeautifulSoup(main_page, 'html.parser', from_encoding='utf-8')
        # get tickt title
        data['title'] = dom.find(None, {'class': 'page-header'}).text.strip()
        # get all "rows" There all data is saved
        rows = dom.findAll(None, {'class': 'row'}, recursive=False)
        # get description
        # find description row
        desc_html_str = self.find_string_in_list(rows, '<!-- begin row for description -->')
        # check whether description row exists
        if desc_html_str != None:
            # get description row data
            desc_dom = BeautifulSoup(desc_html_str, 'html.parser')
            # check if string contains characters
            if desc_dom.find(None, {'class': 'col-md-9'}).text.strip() != '':
                # save description
                data['description'] = desc_dom.find(None, {'class': 'col-md-9'}).text.strip()
        # get main image
        # find image row
        image_html_str = self.find_string_in_list(rows, '<!-- begin row for ft_icon -->')
        # check whether image row exists
        if image_html_str != None:
            # get image row data
            image_dom = BeautifulSoup(image_html_str, 'html.parser')
            # cut out image id and save
            data['image_id'] = image_dom.find(None, {'class': 'col-xs-9'}).renderContents().decode('utf-8', 'replace').split('thumbnail/')[1].split('?')[0]
        # get article numbers
        # get article numbers row
        article_nos_html_str = self.find_string_in_list(rows, '<!-- begin row for ft_article_nos -->')
        # check whether article numbers row exists
        if article_nos_html_str != None:
            # get article numbers row data
            article_nos_dom = BeautifulSoup(article_nos_html_str, 'html.parser')
            # initailize article numbers dict
            article_nos_dict = {}
            # check all lines for article numbers
            for line in article_nos_dom.find(None, {'class': 'col-xs-9'}).text.split('\n'):
                # split year from the article number
                line_split = line.split(': ')
                # save article number in article numbers dict
                article_nos_dict[line_split[0]] = line_split[1]
            # save all article numbers
            data['article_nos'] = article_nos_dict
        # get article parents
        # get article parents row
        parents_html_str = self.find_string_in_list(rows, '<!-- begin row for ft_contained_in -->')
        # check whether article parents row exists
        if parents_html_str != None:
            # get article parents row data
            parents_dom = BeautifulSoup(parents_html_str, 'html.parser')
            # initailize article parents dirct
            parents_dict = {}
            # get prototype parents list
            for parent in parents_dom.find(None, {'class': 'col-xs-9'}).renderContents().decode('utf-8', 'replace').split(', '):
                # check for link in entry
                if 'href' in parent:
                    # save parent in parents dict
                    parents_dict[parent.split('ticket/')[1].split('"')[0]] = parent.split('">')[1].split('</a>')[0]
            # save all article parents
            data['parents'] = parents_dict
        # get article childs
        # get article childs row
        childs_html_str = self.find_string_in_list(rows, '<!-- begin row for ft_contains -->')
        # check whether row exists and save
        if childs_html_str != None:
            data['has_childs'] = True
        else:
            data['has_childs'] = False
        # return data
        return(data)

    def get_ticket_childs(self, part_id):
        # get ticket childs
        # genarate initial URL
        basic_call_string = 'api/ft-partslist/' + str(part_id)
        # initialize variables
        page = 1
        partslist = []
        return_data = {}
        # call server
        data = self.call_server_json(basic_call_string)
        # check whether article has childs
        if data['cTotal'] == 0:
            # abort if no childs
            print('no childs')
            return({})
        # get pages count
        total_pages = data['cPages']
        # get childs statistics and save
        return_data['total'] = data['cTotalParts']
        return_data['total_unique'] = data['cTotal']
        # save first page childs
        partslist.extend(data['results'])
        # if avaible get next pages
        while page < total_pages:
            # increase page count
            page += 1
            # call server
            data = self.call_server_json(basic_call_string + '?page=' + str(page))
            # save page childs
            partslist.extend(data['results'])
        # save childs in dict
        return_data['parts'] = partslist
        # return data
        return(return_data)

    def img_url(self, img_id, height):
        return(self.base_url + 'thumbnail/' + str(img_id) + '?size=' + str(height))

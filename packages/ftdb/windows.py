#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import __main__ as main
from style import *
import urllib.request


class SearchResultDialog(TouchDialog):

    def __init__(self, parent, search_str):
        TouchDialog.__init__(self, "Search", parent)
        self.search_str = search_str
        search_result = main.db.fulltext_search(self.search_str)
        self.vbox = QVBoxLayout()
        self.ListWidget = SearchResultListWidget(result=search_result, parent=self)
        self.ListWidget.click.connect(self.ticket_info)
        self.vbox.addWidget(self.ListWidget)
        self.centralWidget.setLayout(self.vbox)

    def ticket_info(self, ticket_data):
        print(str(ticket_data).encode())
        dialog = TicketInfoDialog(self, ticket_data)
        dialog.exec_()


class ParentsDialog(TouchDialog):

    def __init__(self, parent, data):
        TouchDialog.__init__(self, "Parents", parent)
        self.vbox = QVBoxLayout()
        self.ListWidget = ParentsListWidget(result=data, parent=self)
        self.ListWidget.click.connect(self.ticket_info)
        self.vbox.addWidget(self.ListWidget)
        self.centralWidget.setLayout(self.vbox)

    def ticket_info(self, ticket_data):
        print(str(ticket_data).encode())
        dialog = TicketInfoDialog(self, ticket_data)
        dialog.exec_()


class ChildsDialog(TouchDialog):

    def __init__(self, parent, ticket_id):
        TouchDialog.__init__(self, "Childs", parent)
        self.vbox = QVBoxLayout()
        x = main.time.time()
        data = main.db.get_ticket_childs(ticket_id)
        print(main.time.time() - x)
        self.ListWidget = ChildsListWidget(result=data, parent=self)
        self.ListWidget.click.connect(self.ticket_info)
        self.vbox.addWidget(self.ListWidget)
        self.centralWidget.setLayout(self.vbox)

    def ticket_info(self, ticket_data):
        print(str(ticket_data).encode())
        dialog = TicketInfoDialog(self, ticket_data)
        dialog.exec_()


class TicketInfoDialog(TouchDialog):

    def __init__(self, parent, ticket_pre_data):
        TouchDialog.__init__(self, "Article", parent)
        self.title, self.ticket_id = ticket_pre_data
        self.txt = QTextEdit()
        self.text = '<h2><font color="#fcce04">' + self.title + '</font></h2><b><font color="#fcce04">Loading...</b>'
        self.txt.setReadOnly(True)
        self.font = QFont()
        self.font.setPointSize(16)
        self.txt.setFont(self.font)
        self.txt.setHtml(self.text)
        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.txt)
        self.menu = self.addMenu()
        self.centralWidget.setLayout(self.vbox)
        self.ticket_data = {}
        self.new_html = ''
        self.set_menu = False
        self.set_html = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.build_menu)
        self.timer.start(100)
        self.HtmlBuilder = HtmlBuilder(self)
        self.HtmlBuilder.start()

    def build_menu(self):
        if self.set_menu and self.set_html:
            self.timer.stop()
            return
        if not self.set_menu:
            if 'has_childs' in self.ticket_data or 'parents' in self.ticket_data:
                print('create menu')
                if self.ticket_data['has_childs']:
                    menu_childs = self.menu.addAction('Contains')
                    menu_childs.triggered.connect(self.show_childs)
                if 'parents' in self.ticket_data:
                    menu_parents = self.menu.addAction('Included in')
                    menu_parents.triggered.connect(self.show_parents)
                self.set_menu = True
        if not self.set_html:
            if self.new_html != '':
                print('set html')
                self.txt.setHtml(self.new_html)
                self.set_html = True

    def show_parents(self):
        dialog = ParentsDialog(self, self.ticket_data)
        dialog.exec_()

    def show_childs(self):
        dialog = ChildsDialog(self, self.ticket_id)
        dialog.exec_()


class HtmlBuilder(QThread):

    def __init__(self, parent):
        super(HtmlBuilder, self).__init__(parent)
        self.parent = parent

    def run(self):
        title_html = ''
        description_html = ''
        image_html = ''
        article_nos_html = ''
        html = ''
        self.parent.ticket_data = main.db.get_ticket_data(self.parent.ticket_id)
        if 'title' in self.parent.ticket_data:
            title_html = '<h2><font color="#fcce04">' + self.parent.ticket_data['title'] + '</font></h2>'
        if 'image_id' in self.parent.ticket_data:
            target_file = main.temp_folder + main.image_temp + self.parent.ticket_data['image_id']
            if not main.os.path.isfile(target_file):
                image_url = main.db.img_url(self.parent.ticket_data['image_id'], main.image_size)
                print('Loading:', image_url)
                response = urllib.request.urlopen(image_url, context=main.db.ctx)
                with open(target_file, 'wb') as file_object:
                    file_object.write(response.read())
            image_html = '<b>Image<b><center><img src="/tmp/ftdb/images/' + self.parent.ticket_data['image_id'] + '" alt="Image Error"></center>'
        if 'description' in self.parent.ticket_data:
            description_html = '<b>Description<b>' + self.parent.ticket_data['description']
        if 'article_nos' in self.parent.ticket_data:
            article_nos_html = '<tr><th>Year</th><th>Article No</th></tr>'
            for year in sorted(self.parent.ticket_data['article_nos']):
                article_nos_html = article_nos_html + '<tr><td>' + year + '</td><td>' + self.parent.ticket_data['article_nos'][year] + '</td>'
        print(title_html.encode())
        print(image_html.encode())
        print(description_html.encode())
        print(article_nos_html.encode())
        order_list_translation = {'title': title_html, 'description': description_html, 'image': image_html, 'article_nos': article_nos_html}
        for item in main.ticket_info_order:
            html = html + order_list_translation[item]
        self.parent.new_html = html

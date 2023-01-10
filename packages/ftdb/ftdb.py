#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

import sys
from TouchStyle import *
from urllib.request import *
import ssl
import json


search_url = "https://ft-datenbank.de/api/tickets?fulltext="
icon_url = "https://ft-datenbank.de/thumbnail/"
big_icon_url = "https://ft-datenbank.de/binary/"
article_url = "https://ft-datenbank.de/api/ticket/"

class PicDialog(TouchDialog):
    def __init__(self, parent, img_name):
        TouchDialog.__init__(self, "Picture", parent)
        
        self.vbox = QVBoxLayout()
        
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        
        data = urlopen(big_icon_url + img_name, context=self.ctx).read()
        image = QImage()
        image.loadFromData(data)
        t = QPixmap(image)
        
        lb = QLabel()
        lb.setPixmap(t)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(lb)
        QScroller.grabGesture(self.scroll.viewport(), QScroller.LeftMouseButtonGesture)
        
        self.vbox.addWidget(self.scroll)
        self.centralWidget.setLayout(self.vbox)
        

class PicButton(QLabel):
    def __init__(self, pix, img_name):
        super().__init__()
        
        
        self.img_name = img_name
        self.setPixmap(pix)
        
    def mouseReleaseEvent(self, event):
        dialog = PicDialog(self, self.img_name)
        dialog.exec_()

class TicketDialog(TouchDialog):
    def __init__(self, parent, id):
        TouchDialog.__init__(self, "Article", parent)
        
        self.vbox = QVBoxLayout()
        
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        
        with urlopen(article_url + str(id), context=self.ctx) as r:
            res = r.read()
        dt = json.loads(res)["results"]
        
        
        with urlopen(icon_url + dt["ft_icon"], context=self.ctx) as r:
            data = r.read()
        image = QImage()
        image.loadFromData(data)
        t = QPixmap(image)
        lb = PicButton(t, dt["ft_icon"])
        
        infos = QTextEdit()
        infos.setReadOnly(True)
        infos.setHtml(self.get_html(dt))
        
        self.sc = QWidget()
        
        self.vbox.addWidget(lb, alignment=Qt.AlignCenter)
        self.vbox.addWidget(infos)
        self.centralWidget.setLayout(self.vbox)
        
        
    def get_html(self, dt):
        html = ""
        try:
            html += "<h3>" + dt["title"] + "</h3>"
        except:
            pass
        try:
            html += "<br><b>Description: </b>" + dt["description"]
        except:
            pass
        try:
            html += "<b>Category: </b>" + dt["ft_cat_all_formatted"]
        except:
            pass
        try:
            html += "<br><b>Created: </b>" + dt["createdDate"] + " by " + dt["createdByUserName"]
        except:
            pass
        try:
            html += "<br><b>Wight in g: </b>" + dt["weight"]
        except:
            pass
        try:
            nos = dt["ft_article_nos"].replace("[", "").replace("]", "").replace("\"", "").split(",")
            form = ""
            i = 0
            for x in nos:
                i += 1
                if i % 2:
                    form += str(x) + ": "
                elif x == "null":
                    form += "—, "
                else:
                    form += str(x) + ", "
            print(form)
            print(form[:-2])
            form = form[:-2]
            print(str(form))
            html += "<br><b>Article No: </b>" + form
        except:
            pass
            
        return html
        

class SearchResultDialog(TouchDialog):
    def __init__(self, parent, search_str):
        TouchDialog.__init__(self, "Search", parent)
        
        
        self.vbox = QVBoxLayout()
        
        self.list = QListWidget()
        self.list.setIconSize(QSize(50, 50))
        self.list.itemClicked.connect(self.art)
        QScroller.grabGesture(self.list.viewport(), QScroller.LeftMouseButtonGesture)
        self.list.setVerticalScrollMode(self.list.ScrollPerPixel)
        try:
            search_str = search_str.replace(" ", "+")
            self.search(search_str)
            self.vbox.addWidget(self.list)
        except:
            err_lb = QLabel("Nothing found.")
            self.vbox.addWidget(err_lb)
        self.centralWidget.setLayout(self.vbox)
        
    def search(self, search_str):
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        with urlopen(search_url + search_str, context=self.ctx) as r:
            res = r.read()
        l = json.loads(res)
        for x in l["results"]:
            data = urlopen(icon_url + x["ft_icon"], context=self.ctx).read()
            image = QImage()
            image.loadFromData(data)
            t = QPixmap(image)
            i = QIcon()
            i.addPixmap(t)
            item = QListWidgetItem(i, x["htmlLongerTitle"])
            item.setData(Qt.UserRole, (str(x["ticket_id"])))
            self.list.addItem(item)
            
    def art(self, item):
        ticket_id = item.data(Qt.UserRole)
        print(ticket_id)
        dialog = TicketDialog(self, ticket_id)
        dialog.exec_()


class FtcGuiApplication(TouchApplication):
    def __init__(self, args):
        TouchApplication.__init__(self, args)
        
        self.w = TouchWindow('ft:Datenbank')
        self.vbox = QVBoxLayout()
        self.vbox.addStretch()
        self.search_label = QLabel('Search:')
        self.vbox.addWidget(self.search_label)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText('Search')
        self.vbox.addWidget(self.edit)
        self.vbox.addStretch()
        self.search_but = QPushButton('search')
        self.search_but.clicked.connect(self.search)
        self.vbox.addWidget(self.search_but, alignment=Qt.AlignCenter)
        self.vbox.addStretch()
        self.w.centralWidget.setLayout(self.vbox)
        self.w.show()
        self.exec_()

    def search(self):
        search_str = self.edit.text()
        print('Searching:' + search_str)
        dialog = SearchResultDialog(self.w, search_str)
        dialog.exec_()

if __name__ == "__main__":
    FtcGuiApplication(sys.argv)

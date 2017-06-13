#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#

from TouchStyle import *


class ShadowButton(QToolButton):
    # generate a nice looking button with shadow

    def __init__(self, iconname):
        QToolButton.__init__(self)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setOffset(QPointF(3, 3))
        self.setGraphicsEffect(shadow)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        pix = QPixmap(os.path.join(os.path.dirname(os.path.realpath(__file__)), iconname))
        icon = QIcon(pix)
        self.setIcon(icon)
        self.setIconSize(pix.size())

    def mousePressEvent(self, event):
        self.graphicsEffect().setEnabled(False)
        QToolButton.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.graphicsEffect().setEnabled(True)
        QToolButton.mouseReleaseEvent(self, event)


class TicketListWidget(QListWidget):
    click = pyqtSignal(tuple)

    def __init__(self, result={}, parent=None):
        super(TicketListWidget, self).__init__(parent)
        for name, ticket_id in self.transform_dict(result):
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, (name, int(ticket_id)))
            self.addItem(item)
        self.itemClicked.connect(self.onItemClicked)

    def onItemClicked(self, item):

        name, ticket_id = item.data(Qt.UserRole)
        print('Clicked on:', str(name).encode(), str(ticket_id).encode())
        self.click.emit(item.data(Qt.UserRole))

    def transform_dict(self, data):
        print('TicketListWidget cannot be accessed this way!')
        return(('BAD', 0), ('ACCESS', 0))


class SearchResultListWidget(TicketListWidget):

    def transform_dict(self, data):
        return_data = []
        if 'results' in data:
            for ticket in data['results']:
                return_data.append((ticket['title'], ticket['ticket_id']))
        return(return_data)


class ParentsListWidget(TicketListWidget):

    def transform_dict(self, data):
        return_data = []
        if 'parents' in data:
            for ticket_id, name in data['parents'].items():
                return_data.append((name, ticket_id))
        print(str(return_data).encode())
        return(return_data)


class ChildsListWidget(TicketListWidget):

    def transform_dict(self, data):
        return_data = []
        if 'parts' in data:
            for ticket in data['parts']:
                return_data.append((ticket['title'], ticket['ticket_id']))
        return(return_data)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
from bs4 import BeautifulSoup
from roSubroutine import RoboProSubroutine
from roIOWrap import RoboProIOWrap

__author__     = "Leon Schnieber"
__copyright__  = "Copyright 2018-2019"
__credits__    = "fischertechnik GmbH"
__maintainer__ = "Leon Schnieber"
__email__      = "olaginos-buero@outlook.de"
__status__     = "Developement"


class RoboProProgram(object):
    """
    The RoboProProgram-Class is able to parse and execute a .rpp-File generated
    from the RoboPro-Software. At least one input parameter needs to be passed:
    - a filename/path of a RoboPro-File or its corresponding XML file
    - or the XML-String itself, e.g. directly read from a file, hardcoded…
    The second (optional) parameter expects a dictionary configuring the IO for
    all interfaces. As a default, IF1 is set to a locally configured ftrobopy-
    Library in auto-Mode.
    """


    def __init__(self, xmlstr, ifconfig=None):
        if "<" not in xmlstr:  # check if file is XML or path
            try:
                with open(xmlstr, "r") as file:
                    xmlstr = "".join(file.readlines())
                    file.close()
            except BaseException as e:
                print("ERROR", e)
        self.soup = BeautifulSoup(xmlstr, "xml")
        self._subroutines = {}
        self._data = None
        self._io = RoboProIOWrap(ifconfig)
        self.parse()

    def parse(self):
        """
        Parsing the XML-Structure for Subroutines. For each found subroutine a
        new instance of the Subroutine-Class is initialized.
        """
        subroutinesRaw = self.soup.find_all("o", attrs={
            "classname": "ftProSubroutineFunction"})
        for subRaw in subroutinesRaw:
            self.addNewSubroutine(subRaw)
        # print("Found", len(subroutinesRaw), "subroutine(s).")

    def addNewSubroutine(self, subRaw):
        """
        Adding a new subroutine to the programs subroutine-list and setting it's
        partially optional parameters.
        """
        subRtName = subRaw.attrs["name"]
        subRtObj = RoboProSubroutine(subRaw)
        subRtObj._subrts = self._subroutines
        subRtObj._roProg = self
        subRtObj.setIO(self._io)
        self._subroutines[subRtName] = subRtObj

    def run(self, subroutine="Hauptprogramm"):
        """
        the run functions starts the run()-Functions of a given subroutine. If
        no parameter is given it assumes the user wants to run the "Hauptprogramm"
        """
        if subroutine in self._subroutines:
            subObj = self._subroutines[subroutine]
            subObj.run()

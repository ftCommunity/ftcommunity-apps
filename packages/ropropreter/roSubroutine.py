#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
from bs4 import BeautifulSoup
import threading
from roObject import RoboProObject
from roWire import RoboProWire

__author__     = "Leon Schnieber"
__copyright__  = "Copyright 2018-2019"
__credits__    = "fischertechnik GmbH"
__maintainer__ = "Leon Schnieber"
__email__      = "olaginos-buero@outlook.de"
__status__     = "Developement"


class RoboProSubroutine(object):
    """
    The subroutineObject handles all wires and objects inside a subroutine in-
    stanciated by the RoboProProgram-Class. It is instanciated by the roProgram-
    class and is also controlled from there (e.g. run()-function).
    """


    objectTypeList = [
        # Start-Stop-Blocks: basic elements
        "ftProProcessStart",
        "ftProProcessStop",
        "ftProFlowIf",
        "ftProFlowDelay",
        # Data transmission
        "ftProDataIn",
        "ftProDataOutDual",
        "ftProDataOutDualEx",
        "ftProDataOutSngl",
        "ftProFlowWaitChange",
        "ftProFlowWaitCount",
        "ftProFlowCountLoop",
        "ftProFlowSound",
        # = Send stuff-Command
        "ftProDataMssg",
        "ftProFlowWaitChange",
        # Subroutine-Specific-Blocks
        "ftProSubroutineFlowIn",
        "ftProSubroutineFlowOut",
        "ftProSubroutineDataIn",
        "ftProSubroutineDataOut",
        "ftProSubroutineRef",
        # Variable and stuff
        "ftProDataVariable",
        "ftProDataConst",
        "ftProDataOprt", # operator
        ""
    ]

    wireTypeList = [
        "ftProFlowWire",
        "ftProDataWire"
    ]

    def __init__(self, subroutineXmlSoup):
        self._objects = []
        self._wires = []
        self._subroutineRaw = subroutineXmlSoup
        # self._connectionChains = []
        # self._connectionFragments = []
        self._io = None
        self._lastPin = None
        self._subrts = None
        self._roProg = None
        self._data = None
        self._threads = []
        self._name = self._subroutineRaw.attrs["name"]
        self.parse()

    def parse(self):
        """
        It parses the subroutines XML-Structure and extracts all wires and objects
        connecting each other. Therefor it uses primarily the addNewObject and
        addNewWire-methods.
        """
        objectsRaw = []
        # collect all objects in the xml
        for objectType in self.objectTypeList:
            data = self._subroutineRaw.find_all("o", attrs={
                "classname": objectType
            })
            for objectRaw in data:
                self.addNewObject(objectRaw)
        wiresRaw = []
        # collect all wires in the xml
        for wireType in self.wireTypeList:
            data = self._subroutineRaw.find_all("o", attrs={
                "classname": wireType
            })
            for wireRaw in data:
                self.addNewWire(wireRaw)
        # print("Found", len(objectsRaw), "objects and", len(wiresRaw), "wires.")

    def setIO(self, io):
        self._io = io

    def addNewObject(self, objRaw):
        """ Instanciates a new RoboProObject to be later used"""
        obj = RoboProObject(self, objRaw)
        self._objects.append(obj)

    def addNewWire(self, wireRaw):
        wire = RoboProWire(wireRaw)
        wList, oList = wire.getObjectWireList()
        self.addNewWireObject(wList, oList)
        self._wires.append(wire)

    def addNewWireObject(self, wList, oList):
        """Generate a new Object with the dynamic-id and the wire connecting from the dynamic point to the 'begin' of the wire"""
        # generate a set of new wires
        for wireDat in wList:
            wireNew = RoboProWire()
            wireNew._type = wireDat["type"] + "Helper"
            wireNew._wireinput = wireDat["wireinput"]
            wireNew._wireoutput = wireDat["wireoutput"]
            wireNew._points = [
                {"id": "autogen", "name": "begin", "type": "flowwireinput", "resolve": wireNew._wireinput},
                {"id": "autogen", "name": "end", "type": "flowwireoutput", "resolve": wireNew._wireoutput}
            ]
            self._wires.append(wireNew)
        # generate a set of dummy-objects
        for objDat in oList:
            objNew = RoboProObject(self)
            objNew._type = objDat["type"]
            for objDatPin in objDat["pin"]:
                dat = {
                    "id": objDatPin["id"],
                    "name": objDatPin["type"],
                    "pinclass":  ""
                }
                objNew._pins.append(dat)
            self._objects.append(objNew)

    def _followWire(self, inputID):
        """
        The _followWire function takes an input-ID and follows the wire to the
        next element in the chain and returns the ID of the Block-Input
        """
        for wire in self._wires:
            if wire._wireoutput == inputID:
                return wire._wireinput
        return None

    def _followWireReverse(self, outputID):
        """
        The _followWireReverse function takes an output-ID and follows the wire to the
        next element in the chain to return the ID of the Block-Output connected to it.
        """
        for wire in self._wires:
            if wire._wireinput == outputID:
                return wire._wireoutput
        return None

    def _followWireList(self, inputID):
        """
        The _followWireList-Function finds all outgoing connections from a given
        Pin-ID and returns a list of new endpoints (the in-ID of the next block)
        """
        list = []
        for wire in self._wires:
            if wire._wireoutput == inputID:
                list.append(wire._wireinput)
        return list

    def _findObject(self, objectID):
        """
        The function cycles through all elements in the subroutine and looks for
        the corresponding input ID. It returns a reference to the object (its ID)
        and the outgoing IDs.
        """
        for object in self._objects:
            for pin in object._pins:
                if pin["id"] == objectID:
                    outPinList = object.getPinIdByClass("flowobjectoutput")
                    return outPinList, object
        return None, None

    def _findSubrtInputObject(self, pinID):
        """
        The function looks for a specific input of the subroutine. This is reali-
        zed via a unique Pin-ID given in the Subroutine-Object and the Subroutine-
        Class.
        """
        for object in self._objects:
            if object._type == "ftProSubroutineFlowIn":
                if object._objectRaw.attrs["uniqueID"] == pinID:
                    outPinList = object.getPinIdByClass("flowobjectoutput")
                    return outPinList, object
        return None, None

    def debugPrint(self):
        """
        This function is mainly used for testing purposes. It outputs all objects
        and wires so you can backpropagate all paths by hand to check if the pro-
        gram works correctly.
        """
        print("SUBROUTINE HERE\n" +50 * "=")
        for obj in self._objects:
            print("OBJ ", obj._type, "(" + obj._id + ")")
            for pin in obj._pins:
                print(pin)
                print(" >", "ID" + pin["id"], pin["pinclass"], pin["name"], "(pinid" + str(pin["pinid"]) + ")")
        for wire in self._wires:
            print("WIRE", wire._type)
            for point in wire._points:
                print(" |", "ID" + point["id"], "RE" + point["resolve"], point["type"], point["name"])

    def buildGraph(self):
        '''
        This function builds a multidimensional, partly kind of recursive graph
        to representate the general structure of the main blocks. It partially
        ignores data-wires and its connections so the path is kept very slim
        '''
        for startobject in self._objects:
            if startobject._type in ["ftProProcessStart", "ftProSubroutineFlowIn"]:
                elChain = {"obj": "start", "next": []}
                elementChain = self.__buildGraphRec(startobject)
                self._connectionChains.append(elementChain)
        return self._connectionChains

    def __buildGraphRec(self, startObj):
        '''
        This is a helper function of the buildGraph-function. It fetches all out-
        going objects and adds them to a list so the main function can follow
        those traces.
        '''
        elChain = {"aobj": startObj, "next": []}
        followIdList = startObj.getPinIdByClass("flowobjectoutput")
        followIdList += startObj.getPinIdByClass("dataobjectoutput")
        for beginPin in followIdList:
            endPin = self._followWire(beginPin)
            endObj = self._findObject(endPin)[1]
            if endObj is not None:
                # print(endObj)
                elChain["next"].append(self.__buildGraphRec(endObj))
        return elChain


    def run(self, startObj=None, referenceSubprogram=None, referenceObject=None):
        '''
        The run function is mainly called in two situations.
        1) The subroutine is started as an Main-Program. It doesn't have a Sub-
        program-Input-Block but one or more main start-blocks. Each block should
        be run in an own thread, following all elements down the logical structure.
        2) The subroutine is referenced and called by another subprogram. To run
        smoothly it needs the name and objectID of the Subprogram-Block that called
        the function and the object inside the subroutine where it should start
        (because subprograms can have multiple inputs. the references are needed
        to enable the backpropagation of input/output-Blocks).
        '''
        if startObj is None:
            processCount = 0
            for startobject in self._objects:
                processCount += 1 if startobject._type == "ftProProcessStart" else 0
            threadCreateCount = 0
            # print(processCount)
            for startobject in self._objects:
                if startobject._type == "ftProProcessStart":
                    # if it is only one process, the only thread can be run directly here
                    # if there are n processes, create n threads for them
                    # Optional TODO: Only create n-1 threads, the last one can run directly
                    if processCount == 1:
                        startObj = self._runObjectStructure(startobject)
                    else:
                        # print("Thread created")
                        newThread = threading.Thread(target=self._runObjectStructure, args=(startobject, threadCreateCount))
                        newThread.start()
                        self._threads.append(newThread)
                        threadCreateCount += 1
                    # TODO: create new thread for the following while-lool/start block
                    processCount += 1
                else:
                    return None
        else:
            self._subrtReference = (referenceSubprogram, referenceObject)
            return self._runObjectStructure(startObj)

    def _runObjectStructure(self, startobject, thr=0):
        """
        This function tries to follow element for element down the structure and
        executes each single block.
        """
        outputID, arguments = startobject.run(self)
        while outputID is not None:
            # follow the output-wire
            nextPin = self._followWire(outputID)
            nextObj = self._findObject(nextPin)[1]
            # TODO: check, if object has input-values.
            # if so, backpropagate to get these values
            if nextObj is not None:
                if nextObj._type == "ftProSubroutineFlowOut":
                    return nextObj
                else:
                    self._lastPin = nextPin  # save last object
                    # print("Thr", thr)
                    outputID, arguments = nextObj.run(self, arguments=arguments)
            else:
                break
        return

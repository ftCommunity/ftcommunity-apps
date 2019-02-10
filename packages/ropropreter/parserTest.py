from bs4 import BeautifulSoup

# Initialize the File
file =open("../test/testprogramm.xml", "r")
soup = BeautifulSoup("".join(file.readlines()), 'xml')
# Find all Subroutines
central = soup.find_all("o", attrs={"classname": "ftProSubroutineFunction"})
hauptprogramm = central[0]
# Find all objects inside the subroutine
objects = []

# Find all New-Process-Elements
elementList = [
    "ftProProcessStart",
    "ftProProcessStop",
    "ftProFlowIf",
    "ftProDataIn",
    "ftProDataOutDual",
    "ftProProcessStop",
    "ftProDataMssg"]
starts = []
for element in elementList:
    starts += hauptprogramm.find_all("o", attrs={"classname": element})

for startEl in starts:
    obj = {
        "type": startEl.attrs["classname"],
    } #, "id": startEl.attrs["id"]}
    pins = startEl.find_all("o", attrs={"classname": "ftProObjectPin"})
    pinList = []
    for x in pins:
        data = {
            "id": x.attrs["id"],
            "pinid": x.attrs["pinid"],
            "name": x.attrs["name"],
            "pinclass": x.attrs["pinclass"]
        }
        pinList.append(data)
    print("ELEMENT", obj["type"])
    for pin in pinList:
        print(" -> PIN", "I" + pin["id"], pin["pinclass"], pin["name"])

wireTypes = ["ftProFlowWire", "ftProDataWire"]
wires = []
for wireType in wireTypes:
    wires += hauptprogramm.find_all("o", attrs={"classname": wireType})

for wireEl in wires:
    pins = wireEl.find_all("o", attrs={"classname": "wxCanvasPin"})
    pointList = []
    for x in pins:
        data = {
            "id": x.attrs["id"],
            "name": x.attrs["name"],
            "resolve": x.attrs["resolveid"],
            "type": x.attrs["pinclass"]
        }
        pointList.append(data)
    print("WIRE")
    for pin in pointList:
        print("-|-", "I" + pin["id"], "R" + pin["resolve"], pin["type"])

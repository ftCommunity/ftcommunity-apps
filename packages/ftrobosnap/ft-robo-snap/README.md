FT-Robo-Snap
============

A web interface and IDE for the [Fischertechnik ROBOTICS TXT Controller](http://www.fischertechnik.de/desktopdefault.aspx/tabid-21/39_read-309/usetemplate-2_column_pano/) based on [Snap!](http://snap.berkeley.edu/)

Installation
============

Prerequisites: Python, a reasonably modern browser, and a ROBOTICS TXT Controller.

* Clone this repository or download and unpack https://github.com/rkunze/ft-robo-snap/archive/master.zip
* Change to the the ft-robo-snap directory and run ```python ./robo-snap.py 192.168.7.2```

* Point your browser at http://localhost:65003 to start the Snap! IDE with control blocks for the Robo TXT preloaded

This assumes that your Robo TXT is connected via USB and uses the standard network setup. If you use a Bluetooth or WLAN connection, change "192.168.7.2" to the appropriate adress.

A simple demo project is included in the Examples folder.

License
=======

Copyright (C) 2016 by Richard Kunze

FT-Robo-Snap is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see http://www.gnu.org/licenses/.

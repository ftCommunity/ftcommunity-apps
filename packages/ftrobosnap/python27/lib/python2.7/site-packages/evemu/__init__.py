"""
The evemu module provides the Python interface to the kernel-level input device
raw events.
"""

# Copyright 2011-2012 Canonical Ltd.
#
# This library is free software: you can redistribute it and/or modify it 
# under the terms of the GNU Lesser General Public License version 3 
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from ctypes.util import find_library

import ctypes
import evemu.base
import evemu.const
import glob
import os
import re
import stat

__all__ = ["Device"]


class Device(object):
    """
    Encapsulates a raw kernel input event device, either an existing one as
    reported by the kernel or a pseudodevice as created through a .prop file.
    """

    def __init__(self, f):
        """
        Initializas an evemu Device.

        args:
        f -- a file object or filename string for either an existing input
        device node (/dev/input/eventNN) or an evemu prop file that can be used
        to create a pseudo-device node.
        """

        if type(f).__name__ == 'str':
            self._file = open(f, 'r+b')
        elif type(f).__name__ == 'file':
            self._file = f
        else:
            raise TypeError("expected file or file name")

        self._is_propfile = self._check_is_propfile(self._file)
        self._evemu = evemu.base.EvEmuBase(find_library(evemu.const.LIB))
        self._uinput = None

        libevemu_new = self._evemu.get_lib().evemu_new
        libevemu_new.restype = ctypes.c_void_p
        self._evemu_device = libevemu_new("")

        if self._is_propfile:
            fs = self._evemu._call0(self._evemu.get_c_lib().fdopen,
                                    self._file.fileno(),
                                    'r')
            self._evemu._call(self._evemu.get_lib().evemu_read,
                              self._evemu_device,
                              fs)
            self._uinput = os.open(evemu.const.UINPUT_NODE, os.O_WRONLY)
            self._file = self._create_devnode()
        else:
            self._evemu._call(self._evemu.get_lib().evemu_extract,
                             self._evemu_device,
                             self._file.fileno())

    def __del__(self):
        if hasattr(self, "_is_propfile") and self._is_propfile:
            self._file.close()
            self._evemu._call(self._evemu.get_lib().evemu_destroy,
                              self._uinput)

    def _create_devnode(self):
        self._evemu._call(self._evemu.get_lib().evemu_create,
                          self._evemu_device,
                          self._uinput)
        return open(self._find_newest_devnode(self.name), 'r+')

    def _find_newest_devnode(self, target_name):
        newest_node = (None, float(0))
        for sysname in glob.glob("/sys/class/input/event*/device/name"):
            with open(sysname) as f:
                name = f.read().rstrip()
                if name == target_name:
                    ev = re.search("(event\d+)", sysname)
                    if ev:
                       devname = os.path.join("/dev/input", ev.group(1))
                       ctime = os.stat(devname).st_ctime
                       if ctime > newest_node[1]:
                           newest_node = (devname, ctime)
        return newest_node[0]

    def _check_is_propfile(self, f):
        if stat.S_ISCHR(os.fstat(f.fileno()).st_mode):
            return False

        result = False
        for line in f.readlines():
            if line.startswith("N:"):
                result = True
                break
            elif line.startswith("# EVEMU"):
                result = True
                break
            elif line[0] != "#":
                raise TypeError("file must be a device special or prop file")

        f.seek(0)
        return result

    def describe(self, prop_file):
        """
        Gathers information about the input device and prints it
        to prop_file. This information can be parsed later when constructing
        a Device to create a virtual input device with the same properties.

        Scripts that use this method need to be run as root.
        """
        if type(prop_file).__name__ != 'file':
            raise TypeError("expected file")

        fs = self._evemu._call0(self._evemu.get_c_lib().fdopen,
                                prop_file.fileno(),
                                "w")
        self._evemu._call(self._evemu.get_lib().evemu_write,
                          self._evemu_device,
                          fs)
        self._evemu.get_c_lib().fflush(fs)

    def play(self, events_file):
        """
        Replays an event sequence, as provided by the events_file,
        through the input device. The event sequence must be in
        the form created by the record method.

        Scripts that use this method need to be run as root.
        """
        if type(events_file).__name__ != 'file':
            raise TypeError("expected file")

        fs = self._evemu._call0(self._evemu.get_c_lib().fdopen,
                                events_file.fileno(),
                                "r")
        self._evemu._call(self._evemu.get_lib().evemu_play,
                          fs,
                          self._file.fileno())

    def record(self, events_file, timeout=10000):
        """
        Captures events from the input device and prints them to the
        events_file. The events can be parsed by the play method,
        allowing a virtual input device to emit the exact same event
        sequence.

        Scripts that use this method need to be run as root.
        """
        if type(events_file).__name__ != 'file':
            raise TypeError("expected file")

        fs = self._evemu._call0(self._evemu.get_c_lib().fdopen,
                                events_file.fileno(),
                                "w")
        self._evemu._call(self._evemu.get_lib().evemu_record,
                          fs,
                          self._file.fileno(),
                          timeout)
        self._evemu.get_c_lib().fflush(fs)

    @property
    def version(self):
        """
        Gets the version of the evemu library used to create the Device.
        """
        return self._evemu._call(self._evemu.get_lib().evemu_get_version,
                                 self._evemu_device)

    @property
    def devnode(self):
        """
        Gets the name of the /dev node of the input device.
        """
        return self._file.name

    @property
    def name(self):
        """
        Gets the name of the input device (as reported by the device).
        """
        func = self._evemu.get_lib().evemu_get_name
        func.restype = ctypes.c_char_p
        return self._evemu._call(func, self._evemu_device)

    @property
    def id_bustype(self):
        """
        Identifies the kernel device bustype.
        """
        return self._evemu._call(self._evemu.get_lib().evemu_get_id_bustype,
                                 self._evemu_device)

    @property
    def id_vendor(self):
        """
        Identifies the kernel device vendor.
        """
        return self._evemu._call(self._evemu.get_lib().evemu_get_id_vendor,
                                 self._evemu_device)

    @property
    def id_product(self):
        """
        Identifies the kernel device product.
        """
        return self._evemu._call(self._evemu.get_lib().evemu_get_id_product,
                                 self._evemu_device)

    @property
    def id_version(self):
        """
        Identifies the kernel device version.
        """
        return self._evemu._call(self._evemu.get_lib().evemu_get_id_version,
                                 self._evemu_device)

    def get_abs_minimum(self, event_code):
        return self._evemu._call(self._evemu.get_lib().evemu_get_abs_minimum,
                                 self._evemu_device,
                                 int(event_code))

    def get_abs_maximum(self, event_code):
        return self._evemu._call(self._evemu.get_lib().evemu_get_abs_maximum,
                                 self._evemu_device,
                                 event_code)

    def get_abs_fuzz(self, event_code):
        return self._evemu._call(self._evemu.get_lib().evemu_get_abs_fuzz,
                                 self._evemu_device,
                                 event_code)

    def get_abs_flat(self, event_code):
        return self._evemu._call(self._evemu.get_lib().evemu_get_abs_flat,
                                 self._evemu_device,
                                 event_code)

    def get_abs_resolution(self, event_code):
        return self._evemu._call(self._evemu.get_lib().evemu_get_abs_resolution,
                                 self._evemu_device,
                                 event_code)

    def has_prop(self, event_code):
        return self._evemu._call(self._evemu.get_lib().evemu_has_prop,
                                 self._evemu_device,
                                 event_code)

    def has_event(self, event_type, event_code):
        """
        This method's 'even_type' parameter is expected to mostly take the
        value for EV_ABS (i.e., 0x03), but may on occasion EV_KEY (i.e., 0x01).
        If the former, then the even_code parameter will take the same values
        as the methods above (ABS_*). However, if the latter, then the legal
        values will be BTN_*.

        The reason for including the button data, is that buttons are sometimes
        used to simulate gestures for a higher number of touches than are
        possible with just 2-touch hardware.
        """
        return self._evemu._call(self._evemu.get_lib().evemu_has_event,
                                 self._evemu_device,
                                 event_type,
                                 event_code)


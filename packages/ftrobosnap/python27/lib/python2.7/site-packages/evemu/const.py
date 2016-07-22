LIB = "libevemu.so"
DEFAULT_LIB = "/usr/lib/libevemu.so"
LOCAL_LIB = "../src/.libs/libevemu.so"
UINPUT_NODE = "/dev/uinput"
MAX_EVENT_NODE = 32
UINPUT_MAX_NAME_SIZE = 80 # defined in linux/uinput.h
DEVICE_PATH_TEMPLATE = "/dev/input/event%d"
DEVICE_NAME_PATH_TEMPLATE = "/sys/class/input/event%d/device/name"
# The following should be examined every release of evemu
API = [
    "evemu_new",
    "evemu_delete",
    "evemu_extract",
    "evemu_write",
    "evemu_read",
    "evemu_write_event",
    "evemu_record",
    "evemu_read_event",
    "evemu_play",
    "evemu_create",
    "evemu_destroy",
    # Device settrs
    "evemu_set_name",
    # Device gettrs
    "evemu_get_version",
    "evemu_get_name",
    "evemu_get_id_bustype",
    "evemu_get_id_vendor",
    "evemu_get_id_product",
    "evemu_get_id_version",
    "evemu_get_abs_minimum",
    "evemu_get_abs_maximum",
    "evemu_get_abs_fuzz",
    "evemu_get_abs_flat",
    "evemu_get_abs_resolution",
    # Device hasers
    "evemu_has_prop",
    "evemu_has_event",
    "evemu_has_bit",
    ]

event_types = {
    "EV_SYN": 0x00,
    "EV_KEY": 0x01,
    "EV_REL": 0x02,
    "EV_ABS": 0x03,
    "EV_MSC": 0x04,
    "EV_SW": 0x05,
    "EV_LED": 0x11,
    "EV_SND": 0x12,
    "EV_REP": 0x14,
    "EV_FF": 0x15,
    "EV_PWR": 0x16,
    "EV_FF_STATUS": 0x17,
    "EV_MAX": 0x1f,
    }
event_types["EV_CNT"] = event_types["EV_MAX"] + 1,

event_names = {
    "EV_SYN": "Sync",
    "EV_KEY": "Keys or Buttons",
    "EV_REL": "Relative Axes",
    "EV_ABS": "Absolute Axes",
    "EV_MSC": "Miscellaneous",
    "EV_SW": "Switches",
    "EV_LED": "Leds",
    "EV_SND": "Sound",
    "EV_REP": "Repeat",
    "EV_FF": "Force Feedback",
    "EV_PWR": "Power Management",
    "EV_FF_STATUS": "Force Feedback Status",
}

absolute_axes = {
    "ABS_X": 0x00,
    "ABS_Y": 0x01,
    "ABS_Z": 0x02,
    "ABS_RX": 0x03,
    "ABS_RY": 0x04,
    "ABS_RZ": 0x05,
    "ABS_THROTTLE": 0x06,
    "ABS_RUDDER": 0x07,
    "ABS_WHEEL": 0x08,
    "ABS_GAS": 0x09,
    "ABS_BRAKE": 0x0a,
    "ABS_HAT0X": 0x10,
    "ABS_HAT0Y": 0x11,
    "ABS_HAT1X": 0x12,
    "ABS_HAT1Y": 0x13,
    "ABS_HAT2X": 0x14,
    "ABS_HAT2Y": 0x15,
    "ABS_HAT3X": 0x16,
    "ABS_HAT3Y": 0x17,
    "ABS_PRESSURE": 0x18,
    "ABS_DISTANCE": 0x19,
    "ABS_TILT_X": 0x1a,
    "ABS_TILT_Y": 0x1b,
    "ABS_TOOL_WIDTH": 0x1c,
    "ABS_VOLUME": 0x20,
    "ABS_MISC": 0x28,
    "ABS_MT_SLOT": 0x2f,  # MT slot being modified
    "ABS_MT_TOUCH_MAJOR": 0x30,  # Major axis of touching ellipse
    "ABS_MT_TOUCH_MINOR": 0x31,  # Minor axis (omit if circular)
    "ABS_MT_WIDTH_MAJOR": 0x32,  # Major axis of approaching ellipse
    "ABS_MT_WIDTH_MINOR": 0x33,  # Minor axis (omit if circular)
    "ABS_MT_ORIENTATION": 0x34,  # Ellipse orientation
    "ABS_MT_POSITION_X": 0x35,  # Center X ellipse position
    "ABS_MT_POSITION_Y": 0x36,  # Center Y ellipse position
    "ABS_MT_TOOL_TYPE": 0x37,  # Type of touching device
    "ABS_MT_BLOB_ID": 0x38,  # Group a set of packets as a blob
    "ABS_MT_TRACKING_ID": 0x39,  # Unique ID of initiated contact
    "ABS_MT_PRESSURE": 0x3a,  # Pressure on contact area
    "ABS_MT_DISTANCE": 0x3b, # Contact hover distance
    "ABS_MAX": 0x3f,
    }
# XXX ABS_CNT doesn't always give the same value from test data; disabling it
# for now.
#absolute_axes["ABS_CNT"] = absolute_axes["ABS_MAX"] + 1

buttons = {
    "BTN_MISC": 0x100,
    "BTN_0": 0x100,
    "BTN_1": 0x101,
    "BTN_2": 0x102,
    "BTN_3": 0x103,
    "BTN_4": 0x104,
    "BTN_5": 0x105,
    "BTN_6": 0x106,
    "BTN_7": 0x107,
    "BTN_8": 0x108,
    "BTN_9": 0x109,

    "BTN_MOUSE": 0x110,
    "BTN_LEFT": 0x110,
    "BTN_RIGHT": 0x111,
    "BTN_MIDDLE": 0x112,
    "BTN_SIDE": 0x113,
    "BTN_EXTRA": 0x114,
    "BTN_FORWARD": 0x115,
    "BTN_BACK": 0x116,
    "BTN_TASK": 0x117,

    "BTN_JOYSTICK": 0x120,
    "BTN_TRIGGER": 0x120,
    "BTN_THUMB": 0x121,
    "BTN_THUMB2": 0x122,
    "BTN_TOP": 0x123,
    "BTN_TOP2": 0x124,
    "BTN_PINKIE": 0x125,
    "BTN_BASE": 0x126,
    "BTN_BASE2": 0x127,
    "BTN_BASE3": 0x128,
    "BTN_BASE4": 0x129,
    "BTN_BASE5": 0x12a,
    "BTN_BASE6": 0x12b,
    "BTN_DEAD": 0x12f,

    "BTN_GAMEPAD": 0x130,
    "BTN_A": 0x130,
    "BTN_B": 0x131,
    "BTN_C": 0x132,
    "BTN_X": 0x133,
    "BTN_Y": 0x134,
    "BTN_Z": 0x135,
    "BTN_TL": 0x136,
    "BTN_TR": 0x137,
    "BTN_TL2": 0x138,
    "BTN_TR2": 0x139,
    "BTN_SELECT": 0x13a,
    "BTN_START": 0x13b,
    "BTN_MODE": 0x13c,
    "BTN_THUMBL": 0x13d,
    "BTN_THUMBR": 0x13e,

    "BTN_DIGI": 0x140,
    "BTN_TOOL_PEN": 0x140,
    "BTN_TOOL_RUBBER": 0x141,
    "BTN_TOOL_BRUSH": 0x142,
    "BTN_TOOL_PENCIL": 0x143,
    "BTN_TOOL_AIRBRUSH": 0x144,
    "BTN_TOOL_FINGER": 0x145,
    "BTN_TOOL_MOUSE": 0x146,
    "BTN_TOOL_LENS": 0x147,
    "BTN_TOUCH": 0x14a,
    "BTN_STYLUS": 0x14b,
    "BTN_STYLUS2": 0x14c,
    "BTN_TOOL_DOUBLETAP": 0x14d,
    "BTN_TOOL_TRIPLETAP": 0x14e,
    "BTN_TOOL_QUADTAP": 0x14f, # Four fingers on trackpad

    "BTN_WHEEL": 0x150,
    "BTN_GEAR_DOWN": 0x150,
    "BTN_GEAR_UP": 0x151,

    "BTN_TRIGGER_HAPPY": 0x2c0,
    "BTN_TRIGGER_HAPPY1": 0x2c0,
    "BTN_TRIGGER_HAPPY2": 0x2c1,
    "BTN_TRIGGER_HAPPY3": 0x2c2,
    "BTN_TRIGGER_HAPPY4": 0x2c3,
    "BTN_TRIGGER_HAPPY5": 0x2c4,
    "BTN_TRIGGER_HAPPY6": 0x2c5,
    "BTN_TRIGGER_HAPPY7": 0x2c6,
    "BTN_TRIGGER_HAPPY8": 0x2c7,
    "BTN_TRIGGER_HAPPY9": 0x2c8,
    "BTN_TRIGGER_HAPPY10": 0x2c9,
    "BTN_TRIGGER_HAPPY11": 0x2ca,
    "BTN_TRIGGER_HAPPY12": 0x2cb,
    "BTN_TRIGGER_HAPPY13": 0x2cc,
    "BTN_TRIGGER_HAPPY14": 0x2cd,
    "BTN_TRIGGER_HAPPY15": 0x2ce,
    "BTN_TRIGGER_HAPPY16": 0x2cf,
    "BTN_TRIGGER_HAPPY17": 0x2d0,
    "BTN_TRIGGER_HAPPY18": 0x2d1,
    "BTN_TRIGGER_HAPPY19": 0x2d2,
    "BTN_TRIGGER_HAPPY20": 0x2d3,
    "BTN_TRIGGER_HAPPY21": 0x2d4,
    "BTN_TRIGGER_HAPPY22": 0x2d5,
    "BTN_TRIGGER_HAPPY23": 0x2d6,
    "BTN_TRIGGER_HAPPY24": 0x2d7,
    "BTN_TRIGGER_HAPPY25": 0x2d8,
    "BTN_TRIGGER_HAPPY26": 0x2d9,
    "BTN_TRIGGER_HAPPY27": 0x2da,
    "BTN_TRIGGER_HAPPY28": 0x2db,
    "BTN_TRIGGER_HAPPY29": 0x2dc,
    "BTN_TRIGGER_HAPPY30": 0x2dd,
    "BTN_TRIGGER_HAPPY31": 0x2de,
    "BTN_TRIGGER_HAPPY32": 0x2df,
    "BTN_TRIGGER_HAPPY33": 0x2e0,
    "BTN_TRIGGER_HAPPY34": 0x2e1,
    "BTN_TRIGGER_HAPPY35": 0x2e2,
    "BTN_TRIGGER_HAPPY36": 0x2e3,
    "BTN_TRIGGER_HAPPY37": 0x2e4,
    "BTN_TRIGGER_HAPPY38": 0x2e5,
    "BTN_TRIGGER_HAPPY39": 0x2e6,
    "BTN_TRIGGER_HAPPY40": 0x2e7,
    }

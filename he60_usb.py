"""ROZ HE USB HID communication module - libhmk protocol"""

import os, struct

VID = 0xAB50
PID = 0xAB60
EP_SIZE = 64

# Commands
CMD_FW_VERSION = 0
CMD_REBOOT = 1
CMD_BOOTLOADER = 2
CMD_RECALIBRATE = 4
CMD_GET_CALIBRATION = 6
CMD_SET_CALIBRATION = 7
CMD_GET_PROFILE = 8
CMD_GET_KEYMAP = 128
CMD_SET_KEYMAP = 129

# Keycode name <-> byte mapping
KEYCODE_MAP = {
    "KC_NO":0x00,"_______":0x01,
    "KC_A":0x02,"KC_B":0x03,"KC_C":0x04,"KC_D":0x05,"KC_E":0x06,"KC_F":0x07,
    "KC_G":0x08,"KC_H":0x09,"KC_I":0x0A,"KC_J":0x0B,"KC_K":0x0C,"KC_L":0x0D,
    "KC_M":0x0E,"KC_N":0x0F,"KC_O":0x10,"KC_P":0x11,"KC_Q":0x12,"KC_R":0x13,
    "KC_S":0x14,"KC_T":0x15,"KC_U":0x16,"KC_V":0x17,"KC_W":0x18,"KC_X":0x19,
    "KC_Y":0x1A,"KC_Z":0x1B,
    "KC_1":0x1C,"KC_2":0x1D,"KC_3":0x1E,"KC_4":0x1F,"KC_5":0x20,
    "KC_6":0x21,"KC_7":0x22,"KC_8":0x23,"KC_9":0x24,"KC_0":0x25,
    "KC_ENT":0x26,"KC_ESC":0x27,"KC_BSPC":0x28,"KC_TAB":0x29,"KC_SPC":0x2A,
    "KC_MINS":0x2B,"KC_EQL":0x2C,"KC_LBRC":0x2D,"KC_RBRC":0x2E,"KC_BSLS":0x2F,
    "KC_SCLN":0x31,"KC_QUOT":0x32,"KC_GRV":0x33,"KC_COMM":0x34,"KC_DOT":0x35,
    "KC_SLSH":0x36,"KC_CAPS":0x37,
    "KC_F1":0x38,"KC_F2":0x39,"KC_F3":0x3A,"KC_F4":0x3B,"KC_F5":0x3C,"KC_F6":0x3D,
    "KC_F7":0x3E,"KC_F8":0x3F,"KC_F9":0x40,"KC_F10":0x41,"KC_F11":0x42,"KC_F12":0x43,
    "KC_PSCR":0x44,"KC_SCRL":0x45,"KC_PAUS":0x46,
    "KC_INS":0x47,"KC_HOME":0x48,"KC_PGUP":0x49,"KC_DEL":0x4A,"KC_END":0x4B,"KC_PGDN":0x4C,
    "KC_RGHT":0x4D,"KC_LEFT":0x4E,"KC_DOWN":0x4F,"KC_UP":0x50,
    "KC_APP":0x63,
    "KC_LCTL":0x7B,"KC_LSFT":0x7C,"KC_LALT":0x7D,"KC_LGUI":0x7E,
    "KC_RCTL":0x7F,"KC_RSFT":0x80,"KC_RALT":0x81,"KC_RGUI":0x82,
    "KC_MUTE":0x86,"KC_VOLU":0x87,"KC_VOLD":0x88,
    "KC_MNXT":0x89,"KC_MPRV":0x8A,"KC_MSTP":0x8B,"KC_MPLY":0x8C,
    "MO(0)":0xC0,"MO(1)":0xC1,"MO(2)":0xC2,"MO(3)":0xC3,
    "MO(4)":0xC4,"MO(5)":0xC5,"MO(6)":0xC6,"MO(7)":0xC7,
    "PF(0)":0xC8,"PF(1)":0xC9,"PF(2)":0xCA,"PF(3)":0xCB,
    "PF_SWAP":0xD2,"PF_NEXT":0xD3,"SP_BOOT":0xD4,
}

# Reverse map: byte -> name
BYTE_TO_NAME = {v: k for k, v in KEYCODE_MAP.items()}


def name_to_byte(name):
    return KEYCODE_MAP.get(name, None)

def byte_to_name(b):
    return BYTE_TO_NAME.get(b, f"0x{b:02X}")


def find_hidraw():
    """Find the hidraw device for the HE60 config interface (34-byte descriptor)."""
    for h in sorted(os.listdir("/sys/class/hidraw/")):
        try:
            uevent = open(f"/sys/class/hidraw/{h}/device/uevent").read()
            if "ABS0 HE60" not in uevent:
                continue
            desc = open(f"/sys/class/hidraw/{h}/device/report_descriptor", "rb").read()
            if len(desc) == 34:  # vendor HID interface
                return f"/dev/{h}"
        except Exception:
            continue
    return None


class HE60Device:
    def __init__(self):
        self.fd = None
        self.path = None

    def connect(self):
        self.path = find_hidraw()
        if not self.path:
            raise RuntimeError("HE60 not found. Is it plugged in?")
        self.fd = os.open(self.path, os.O_RDWR)
        # Verify with firmware version command
        resp = self._cmd(CMD_FW_VERSION)
        if resp[0] != CMD_FW_VERSION:
            raise RuntimeError("Bad response from keyboard")
        ver = struct.unpack_from("<H", resp, 1)[0]
        return ver

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def _cmd(self, cmd_id, payload=b""):
        import select
        msg = bytes([cmd_id]) + payload
        msg = msg.ljust(EP_SIZE, b'\x00')
        os.write(self.fd, msg)
        r, _, _ = select.select([self.fd], [], [], 1.0)
        if not r:
            raise RuntimeError("No response from keyboard")
        return os.read(self.fd, EP_SIZE)

    def get_keymap(self, profile, layer, num_keys=69):
        """Read full keymap for a profile/layer."""
        keys = []
        offset = 0
        while offset < num_keys:
            resp = self._cmd(CMD_GET_KEYMAP, bytes([profile, layer, offset]))
            if resp[0] != CMD_GET_KEYMAP:
                raise RuntimeError("Failed to read keymap")
            chunk = resp[1:1 + min(63, num_keys - offset)]
            keys.extend(chunk)
            offset += 63
        return keys[:num_keys]

    def set_keymap(self, profile, layer, offset, keycodes):
        """Write keycodes to keyboard. keycodes = list of byte values."""
        # Max 59 keys per packet
        while keycodes:
            chunk = keycodes[:59]
            payload = bytes([profile, layer, offset, len(chunk)] + chunk)
            resp = self._cmd(CMD_SET_KEYMAP, payload)
            if resp[0] != CMD_SET_KEYMAP:
                raise RuntimeError("Failed to write keymap")
            offset += len(chunk)
            keycodes = keycodes[59:]

    def get_profile(self):
        resp = self._cmd(CMD_GET_PROFILE)
        return resp[1]

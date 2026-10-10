#!/usr/bin/env python3
"""ROZ HE Keyboard Configurator v1 - Republic of Zani"""

import json, os, sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

VERSION = "1.0"

# Config persistence
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "roz-hub")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

def load_hub_config():
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH) as f: return json.load(f)
    return {}

def save_hub_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f: json.dump(cfg, f, indent=2)

# USB HID constants
USB_VID = 0xAB50
USB_PID = 0xAB60
EP_SIZE = 64
CMD_FW_VERSION = 0
CMD_GET_PROFILE = 8
CMD_GET_KEYMAP = 128
CMD_SET_KEYMAP = 129

# Keycode name <-> byte
KC_MAP = {
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
    "PF(0)":0xC8,"PF(1)":0xC9,"PF(2)":0xCA,"PF(3)":0xCB,
    "PF_SWAP":0xD2,"PF_NEXT":0xD3,"SP_BOOT":0xD4,
}
KC_REV = {v: k for k, v in KC_MAP.items()}

def kc_to_byte(name):
    return KC_MAP.get(name)
def byte_to_kc(b):
    return KC_REV.get(b, f"0x{b:02X}")

def find_hidraw():
    for h in sorted(os.listdir("/sys/class/hidraw/")):
        try:
            uevent = open(f"/sys/class/hidraw/{h}/device/uevent").read()
            if "ABS0 HE60" not in uevent: continue
            desc = open(f"/sys/class/hidraw/{h}/device/report_descriptor","rb").read()
            if len(desc) == 34: return f"/dev/{h}"
        except Exception: continue
    return None

def usb_cmd(fd, cmd_id, payload=b""):
    import select
    msg = bytes([cmd_id]) + payload
    msg = msg.ljust(EP_SIZE, b'\x00')
    os.write(fd, msg)
    r,_,_ = select.select([fd],[],[],1.0)
    if not r: raise RuntimeError("No response")
    return os.read(fd, EP_SIZE)

def usb_get_keymap(fd, profile, layer, num_keys=69):
    keys = []
    offset = 0
    while offset < num_keys:
        resp = usb_cmd(fd, CMD_GET_KEYMAP, bytes([profile, layer, offset]))
        if resp[0] != CMD_GET_KEYMAP: raise RuntimeError("Read failed")
        keys.extend(resp[1:1+min(63, num_keys-offset)])
        offset += 63
    return keys[:num_keys]

def usb_set_keymap(fd, profile, layer, offset, keycodes):
    while keycodes:
        chunk = keycodes[:59]
        payload = bytes([profile, layer, offset, len(chunk)] + list(chunk))
        resp = usb_cmd(fd, CMD_SET_KEYMAP, payload)
        if resp[0] != CMD_SET_KEYMAP: raise RuntimeError("Write failed")
        offset += len(chunk)
        keycodes = keycodes[59:]

def resource_path(rel):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)

KEYCODES = [
    "▽ (transparent)","✕ (none)",
    "A","B","C","D","E","F","G","H","I","J","K","L","M",
    "N","O","P","Q","R","S","T","U","V","W","X","Y","Z",
    "1","2","3","4","5","6","7","8","9","0",
    "Ctrl","Shift","Alt","Win","RCtrl","RShift","RAlt","RWin",
    "Enter","Esc","Bksp","Tab","Space","Caps",
    "↑ Up","↓ Down","← Left","→ Right","Home","End","PgUp","PgDn",
    "Ins","Del","PrtSc","ScrLk","Pause",
    "- minus","= equal","[ lbracket","] rbracket","\\ backslash",
    "; semicolon","' quote","` grave",", comma",". dot","/ slash","Menu",
    "F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12",
    "Mute","Vol+","Vol-","Prev","Next","Play",
    "Fn","Fn2","Fn3","TG1","TG2","TG3",
    "P0","P1","P2","P3","PSwap","Boot",
]

# Map friendly display name -> real keycode
DISPLAY_TO_KC = {
    "▽ (transparent)":"_______","✕ (none)":"KC_NO",
    "A":"KC_A","B":"KC_B","C":"KC_C","D":"KC_D","E":"KC_E","F":"KC_F",
    "G":"KC_G","H":"KC_H","I":"KC_I","J":"KC_J","K":"KC_K","L":"KC_L",
    "M":"KC_M","N":"KC_N","O":"KC_O","P":"KC_P","Q":"KC_Q","R":"KC_R",
    "S":"KC_S","T":"KC_T","U":"KC_U","V":"KC_V","W":"KC_W","X":"KC_X",
    "Y":"KC_Y","Z":"KC_Z",
    "1":"KC_1","2":"KC_2","3":"KC_3","4":"KC_4","5":"KC_5",
    "6":"KC_6","7":"KC_7","8":"KC_8","9":"KC_9","0":"KC_0",
    "Ctrl":"KC_LCTL","Shift":"KC_LSFT","Alt":"KC_LALT","Win":"KC_LGUI",
    "RCtrl":"KC_RCTL","RShift":"KC_RSFT","RAlt":"KC_RALT","RWin":"KC_RGUI",
    "Enter":"KC_ENT","Esc":"KC_ESC","Bksp":"KC_BSPC","Tab":"KC_TAB",
    "Space":"KC_SPC","Caps":"KC_CAPS",
    "↑ Up":"KC_UP","↓ Down":"KC_DOWN","← Left":"KC_LEFT","→ Right":"KC_RGHT",
    "Home":"KC_HOME","End":"KC_END","PgUp":"KC_PGUP","PgDn":"KC_PGDN",
    "Ins":"KC_INS","Del":"KC_DEL","PrtSc":"KC_PSCR","ScrLk":"KC_SCRL","Pause":"KC_PAUS",
    "- minus":"KC_MINS","= equal":"KC_EQL","[ lbracket":"KC_LBRC","] rbracket":"KC_RBRC",
    "\\ backslash":"KC_BSLS","; semicolon":"KC_SCLN","' quote":"KC_QUOT",
    "` grave":"KC_GRV",", comma":"KC_COMM",". dot":"KC_DOT","/ slash":"KC_SLSH",
    "Menu":"KC_APP",
    "F1":"KC_F1","F2":"KC_F2","F3":"KC_F3","F4":"KC_F4","F5":"KC_F5","F6":"KC_F6",
    "F7":"KC_F7","F8":"KC_F8","F9":"KC_F9","F10":"KC_F10","F11":"KC_F11","F12":"KC_F12",
    "Mute":"KC_MUTE","Vol+":"KC_VOLU","Vol-":"KC_VOLD",
    "Prev":"KC_MPRV","Next":"KC_MNXT","Play":"KC_MPLY",
    "Fn":"MO(1)","Fn2":"MO(2)","Fn3":"MO(3)",
    "TG1":"TG(1)","TG2":"TG(2)","TG3":"TG(3)",
    "P0":"PF(0)","P1":"PF(1)","P2":"PF(2)","P3":"PF(3)",
    "PSwap":"PF_SWAP","Boot":"SP_BOOT",
}
KC_TO_DISPLAY = {v: k for k, v in DISPLAY_TO_KC.items()}

def _parse_layout_rows(layout_data, keymap_layer0):
    """Parse keyboard.json layout into rows with option variants.
    Returns: (base_rows, option_groups)
    base_rows[i] = list of (key_idx, label, width, option_or_None) preserving order
    option_groups = set of option IDs found (e.g. {0, 1})
    """
    SHORT_LABELS = {
        "KC_ESC":"Esc","KC_BSPC":"Bksp","KC_TAB":"Tab","KC_CAPS":"Caps",
        "KC_ENT":"Enter","KC_LSFT":"Shift","KC_RSFT":"RShift","KC_LCTL":"Ctrl",
        "KC_RCTL":"Ctrl","KC_LALT":"Alt","KC_RALT":"Alt","KC_LGUI":"Win",
        "KC_RGUI":"Win","KC_SPC":"Space","KC_MINS":"-","KC_EQL":"=",
        "KC_LBRC":"[","KC_RBRC":"]","KC_BSLS":"\\","KC_SCLN":";",
        "KC_QUOT":"'","KC_GRV":"`","KC_COMM":",","KC_DOT":".","KC_SLSH":"/",
        "KC_APP":"Menu","MO(1)":"Fn","MO(2)":"Fn2","MO(3)":"Fn3",
        "_______":"▽","KC_NO":"✕",
    }
    def label_for(key_idx):
        if keymap_layer0 and key_idx < len(keymap_layer0):
            kc = keymap_layer0[key_idx]
            if kc in SHORT_LABELS: return SHORT_LABELS[kc]
            if kc.startswith("KC_"): return kc[3:]
            return kc
        return str(key_idx)

    all_rows = []  # each row = list of (key_idx, label, width, option_tuple_or_None)
    option_ids = set()

    for json_row in layout_data:
        row = []
        for entry in json_row:
            key_idx = entry["key"]
            w = entry.get("w", 1)
            lbl = label_for(key_idx)
            opt = tuple(entry["option"]) if "option" in entry else None
            if opt is not None:
                option_ids.add(opt[0])
            row.append((key_idx, lbl, w, opt))
        all_rows.append(row)

    return all_rows, option_ids

BG="#1a1a1a"; BG_SIDE="#111111"; BG_PANEL="#222222"
BG_KEY="#2a2a2a"; BG_KEY_HOVER="#3a3a3a"
ACCENT="#cc2222"; BG_KEY_SEL=ACCENT
TEXT="#ffffff"; TEXT_DIM="#888888"
KEY_U=48; KEY_GAP=4; KEY_H=46; RAD=8


def lerp_color(c1, c2, t):
    """Interpolate between two hex colors."""
    r1,g1,b1 = int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
    r,g,b = int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t)
    return f"#{r:02x}{g:02x}{b:02x}"


def round_rect(canvas, x1, y1, x2, y2, r=8, **kw):
    """Draw a rounded rectangle on canvas."""
    pts = [
        x1+r,y1, x2-r,y1,
        x2-r,y1, x2,y1, x2,y1+r,
        x2,y1+r, x2,y2-r,
        x2,y2-r, x2,y2, x2-r,y2,
        x2-r,y2, x1+r,y2,
        x1+r,y2, x1,y2, x1,y2-r,
        x1,y2-r, x1,y1+r,
        x1,y1+r, x1,y1, x1+r,y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


class App(tk.Tk):
    def __init__(self):
        # WM_CLASS must match StartupWMClass in roz-hub.desktop so the taskbar groups the window with its launcher
        super().__init__(className="rozhub")
        self.title("ROZ Hub")
        self.geometry("1150x750")
        self.configure(bg=BG)
        self.minsize(1050,680)
        # Window icon for taskbar and title bar
        try:
            for p in [resource_path("logo/roz-256.png"),
                      resource_path("../logo/roz-256.png")]:
                if os.path.isfile(p):
                    self._icon_img = tk.PhotoImage(file=p)
                    self.iconphoto(True, self._icon_img)
                    break
        except Exception: pass
        self.data=None; self.filepath=None; self.selected_key_idx=None
        self.layout_opts=[0,0,0]
        self.num_keys = 67
        self._layout_rows = []
        self._layout_option_ids = set()
        self._hover_anims = {}
        self._key_items = {}
        self.usb_fd = None
        self.usb_profile = 0
        self.live_keymap = {}  # (layer, key_idx) -> byte value
        self._build_ui()
        self._try_usb_connect()
        self._set_layer(0)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        if self.ls_running:
            self._stop_leftstick()
        self.destroy()

    def _build_ui(self):
        side = tk.Frame(self, bg=BG_SIDE, width=180)
        side.pack(side="left", fill="y"); side.pack_propagate(False)

        try:
            for p in [resource_path("logo/roz-sidebar.png"),
                      resource_path("../logo/roz-sidebar.png")]:
                if os.path.isfile(p):
                    self._logo_img = tk.PhotoImage(file=p)
                    tk.Label(side, image=self._logo_img, bg=BG_SIDE).pack(pady=(15,5))
                    break
        except Exception: pass

        tk.Label(side, text="by Zani Coolen", font=("Arial",8), fg=TEXT_DIM, bg=BG_SIDE).pack()
        tk.Label(side, text=f"v{VERSION} · No RGB", font=("Arial",8), fg="#555", bg=BG_SIDE).pack(pady=(2,15))

        self.pages={}; self.nav_btns={}; self.current_page="keymap"
        for name, icon in [("keymap","⌨  Key Assignment"),("actuation","🎯  Actuation"),
                           ("analog","📊  Analog Viewer"),("gamepad","🎮  Gamepad"),
                           ("leftstick","🕹  Left Stick"),
                           ("layout","🔧  Layout"),("calibration","⚙  Calibration"),
                           ("info","ℹ  Device Info")]:
            btn = tk.Label(side, text=icon, font=("Arial",10), fg=TEXT, bg=BG_SIDE,
                           anchor="w", padx=15, pady=10, cursor="hand2")
            btn.pack(fill="x")
            btn.bind("<Button-1>", lambda e, n=name: self._show_page(n))
            btn.bind("<Enter>", lambda e, b=btn, n=name:
                     b.config(bg="#2a2a2a") if n != self.current_page else None)
            btn.bind("<Leave>", lambda e, b=btn, n=name:
                     b.config(bg=ACCENT if n == self.current_page else BG_SIDE))
            self.nav_btns[name] = btn

        tk.Frame(side, bg=BG_SIDE).pack(fill="both", expand=True)
        for label, cmd in [("📂  Open",self._open)]:
            b = tk.Label(side, text=label, font=("Arial",9), fg=TEXT_DIM, bg=BG_SIDE,
                         anchor="w", padx=15, pady=6, cursor="hand2")
            b.pack(fill="x")
            b.bind("<Button-1>", lambda e, c=cmd: c())
            b.bind("<Enter>", lambda e, w=b: w.config(fg=TEXT))
            b.bind("<Leave>", lambda e, w=b: w.config(fg=TEXT_DIM))

        self.content = tk.Frame(self, bg=BG)
        self.content.pack(side="right", fill="both", expand=True)
        self.status = tk.Label(self, text="Open a keyboard.json to start", font=("Arial",9),
                               fg=TEXT_DIM, bg="#111", anchor="w", padx=10)
        self.status.pack(side="bottom", fill="x")

        self._build_keymap_page()
        self._build_actuation_page()
        self._build_analog_page()
        self._build_gamepad_page()
        self._build_leftstick_page()
        self._build_layout_page()
        self._build_calibration_page()
        self._build_info_page()
        self._show_page("keymap")
        # Auto-load keyboard.json
        auto = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keyboard.json")
        if os.path.isfile(auto):
            self._load_file(auto)
        # Restore left stick config (auto-start if was enabled)
        self._load_ls_config()

    def _show_page(self, name):
        self.current_page = name
        for n, btn in self.nav_btns.items():
            btn.config(bg=ACCENT if n==name else BG_SIDE, fg="#fff" if n==name else TEXT)
        for p in self.pages.values(): p.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        if name == "actuation":
            self._start_act_depth()
        else:
            self.act_depth_running = False

    # ── KEYMAP PAGE ──
    def _build_keymap_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages["keymap"] = page
        tk.Label(page, text="Key Assignment", font=("Arial",15,"bold"),
                 fg=TEXT, bg=BG).pack(anchor="w", padx=20, pady=(12,5))

        lf = tk.Frame(page, bg=BG); lf.pack(fill="x", padx=20, pady=3)
        tk.Label(lf, text="Layer:", font=("Arial",10), fg=TEXT_DIM, bg=BG).pack(side="left")
        self.layer_var = tk.IntVar(value=0); self.layer_btns = []
        layer_names = ["  Base  ","  Fn  ","  Layer 2  ","  Layer 3  "]
        for i in range(4):
            b = tk.Label(lf, text=layer_names[i], font=("Arial",10,"bold"), fg=TEXT,
                         bg="#333", padx=8, pady=3, cursor="hand2")
            b.pack(side="left", padx=3)
            b.bind("<Button-1>", lambda e, idx=i: self._set_layer(idx))
            self.layer_btns.append(b)

        canvas_h = 5*(KEY_H+KEY_GAP)+30
        cf = tk.Frame(page, bg=BG_PANEL, highlightbackground="#333", highlightthickness=1)
        cf.pack(fill="x", padx=20, pady=8)
        self.kb_canvas = tk.Canvas(cf, height=canvas_h, bg=BG_PANEL, highlightthickness=0)
        self.kb_canvas.pack(fill="x", padx=10, pady=10)

        # Editor panel with integrated search
        ef = tk.Frame(page, bg=BG_PANEL, highlightbackground="#333", highlightthickness=1)
        ef.pack(fill="x", padx=20)

        # Row 1: selected key + search
        r1 = tk.Frame(ef, bg=BG_PANEL); r1.pack(fill="x", padx=15, pady=(10,5))
        self.sel_label = tk.Label(r1, text="Click a key to edit", font=("Arial",11),
                                  fg=TEXT_DIM, bg=BG_PANEL)
        self.sel_label.pack(side="left", padx=(0,15))
        tk.Label(r1, text="🔍", font=("Arial",11), fg=TEXT_DIM, bg=BG_PANEL).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        se = tk.Entry(r1, textvariable=self.search_var, font=("Arial",10),
                      bg="#333", fg=TEXT, insertbackground=TEXT, width=20,
                      relief="flat", highlightthickness=1, highlightbackground="#444",
                      highlightcolor=ACCENT)
        se.pack(side="left", padx=5)
        self.search_results = tk.Label(r1, text="", font=("Arial",9),
                                       fg=TEXT_DIM, bg=BG_PANEL)
        self.search_results.pack(side="left", padx=5)

        # Row 2: keycode dropdown + apply
        r2 = tk.Frame(ef, bg=BG_PANEL); r2.pack(fill="x", padx=15, pady=(0,10))
        tk.Label(r2, text="Keycode:", font=("Arial",10), fg=TEXT_DIM, bg=BG_PANEL).pack(side="left")
        self.kc_var = tk.StringVar()
        self.kc_combo = ttk.Combobox(r2, textvariable=self.kc_var, values=KEYCODES,
                                     width=18, font=("Arial",10))
        self.kc_combo.pack(side="left", padx=8)
        self.kc_combo.bind("<<ComboboxSelected>>", self._apply_key)
        self.kc_combo.bind("<Return>", self._apply_key)
        ab = tk.Label(r2, text="  Apply  ", font=("Arial",10,"bold"), fg="#fff",
                      bg=ACCENT, cursor="hand2", padx=8, pady=2)
        ab.pack(side="left", padx=5)
        ab.bind("<Button-1>", self._apply_key)

    def _set_layer(self, idx):
        self.layer_var.set(idx)
        for i, b in enumerate(self.layer_btns):
            b.config(bg=ACCENT if i==idx else "#333", fg="#fff" if i==idx else TEXT)
        self._draw_keyboard()

    def _get_rows(self):
        """Build display rows from parsed layout, filtering by selected options."""
        if not hasattr(self, '_layout_rows') or not self._layout_rows:
            return []
        # layout_opts[0] = backspace choice (option 0), layout_opts[1] = unused, layout_opts[2] = spacebar (option 1)
        chosen = {0: self.layout_opts[0], 1: self.layout_opts[2]}
        rows = []
        for layout_row in self._layout_rows:
            row = []
            for key_idx, lbl, w, opt in layout_row:
                if opt is None:
                    row.append((key_idx, lbl, w))
                elif opt[0] in chosen and opt[1] == chosen[opt[0]]:
                    row.append((key_idx, lbl, w))
            if row:
                rows.append(row)
        return rows

    def _draw_keyboard(self):
        self.kb_canvas.delete("all")
        self._key_items = {}
        for aid in self._hover_anims.values():
            if aid[2]: self.after_cancel(aid[2])
        self._hover_anims = {}

        SHORT = {
            "KC_LCTL":"Ctrl","KC_RCTL":"Ctrl","KC_LSFT":"Shift","KC_RSFT":"Shift",
            "KC_LALT":"Alt","KC_RALT":"Alt","KC_LGUI":"Win","KC_RGUI":"Win",
            "KC_ENT":"Enter","KC_ESC":"Esc","KC_BSPC":"Bksp","KC_TAB":"Tab",
            "KC_SPC":"Space","KC_CAPS":"Caps","KC_DEL":"Del","KC_INS":"Ins",
            "KC_HOME":"Home","KC_END":"End","KC_PGUP":"PgUp","KC_PGDN":"PgDn",
            "KC_UP":"↑ Up","KC_DOWN":"↓ Down","KC_LEFT":"← Left","KC_RGHT":"→ Right",
            "KC_PSCR":"PrtSc","KC_SCRL":"ScrLk","KC_PAUS":"Pause",
            "KC_MINS":"-","KC_EQL":"=","KC_LBRC":"[","KC_RBRC":"]",
            "KC_BSLS":"\\","KC_SCLN":";","KC_QUOT":"'","KC_GRV":"`",
            "KC_COMM":",","KC_DOT":".","KC_SLSH":"/","KC_APP":"Menu",
            "KC_MUTE":"Mute","KC_VOLU":"Vol+","KC_VOLD":"Vol-",
            "KC_MPLY":"Play","KC_MNXT":"Next","KC_MPRV":"Prev",
            "MO(1)":"Fn","MO(2)":"Fn2","MO(3)":"Fn3",
            "MO(0)":"Fn0","TG(1)":"TG1","TG(2)":"TG2","TG(3)":"TG3",
            "PF(0)":"P0","PF(1)":"P1","PF(2)":"P2","PF(3)":"P3",
            "PF_SWAP":"PSwap","PF_NEXT":"PNext","SP_BOOT":"Boot",
            "_______":"▽","KC_NO":"✕",
        }

        layer = self.layer_var.get()
        has_data = self.data and layer < len(self.data.get("keymap",[]))
        keys = self.data["keymap"][layer] if has_data else None
        has_live = bool(self.live_keymap)
        rows = self._get_rows()
        y = 10
        for row in rows:
            x = 10
            for key_idx, label, width in row:
                w = int(width*KEY_U)
                live_kc = self._get_live_kc(layer, key_idx) if has_live else None
                if live_kc:
                    kc = live_kc
                elif keys and key_idx < len(keys):
                    kc = keys[key_idx]
                else:
                    kc = None

                if kc and kc in SHORT:
                    disp = SHORT[kc]
                elif kc and kc.startswith("KC_"):
                    disp = kc[3:]  # strip KC_ prefix, show e.g. "A","F1"
                elif kc:
                    disp = kc
                else:
                    disp = label

                is_sel = key_idx == self.selected_key_idx
                fill = BG_KEY_SEL if is_sel else BG_KEY
                outline = ACCENT if is_sel else "#444"
                tc = "#fff"

                r = round_rect(self.kb_canvas, x, y, x+w-KEY_GAP, y+KEY_H, r=RAD,
                               fill=fill, outline=outline, width=2 if is_sel else 1)
                t = self.kb_canvas.create_text(x+(w-KEY_GAP)//2, y+KEY_H//2,
                    text=disp, fill=tc, font=("Arial",9), width=w-12)

                self._key_items[key_idx] = (r, t)
                for item in (r, t):
                    self.kb_canvas.tag_bind(item, "<Button-1>",
                        lambda e, ki=key_idx, lb=label: self._click_key(ki, lb))
                    self.kb_canvas.tag_bind(item, "<Enter>",
                        lambda e, ki=key_idx: self._anim_hover(ki, True))
                    self.kb_canvas.tag_bind(item, "<Leave>",
                        lambda e, ki=key_idx: self._anim_hover(ki, False))
                x += w
            y += KEY_H + KEY_GAP

    def _anim_hover(self, key_idx, entering):
        """Animate key color on hover."""
        if key_idx not in self._key_items:
            return
        is_sel = key_idx == self.selected_key_idx
        if is_sel:
            return  # don't animate selected key
        # Cancel existing animation
        if key_idx in self._hover_anims and self._hover_anims[key_idx][2]:
            self.after_cancel(self._hover_anims[key_idx][2])
        target = BG_KEY_HOVER if entering else BG_KEY
        # Get current color or start from current state
        if key_idx in self._hover_anims:
            current_t = self._hover_anims[key_idx][1]
        else:
            current_t = 0.0
        start_t = current_t if entering else current_t
        self._hover_anims[key_idx] = [target, start_t, None]
        self._step_hover(key_idx, entering)

    def _step_hover(self, key_idx, entering):
        if key_idx not in self._hover_anims or key_idx not in self._key_items:
            return
        anim = self._hover_anims[key_idx]
        step = 0.15
        if entering:
            anim[1] = min(1.0, anim[1] + step)
        else:
            anim[1] = max(0.0, anim[1] - step)
        color = lerp_color(BG_KEY, BG_KEY_HOVER, anim[1])
        r, t = self._key_items[key_idx]
        self.kb_canvas.itemconfig(r, fill=color)
        done = (entering and anim[1] >= 1.0) or (not entering and anim[1] <= 0.0)
        if not done:
            anim[2] = self.after(16, lambda: self._step_hover(key_idx, entering))
        else:
            anim[2] = None

    def _click_key(self, idx, label):
        prev = self.selected_key_idx
        self.selected_key_idx = idx
        layer = self.layer_var.get()
        live_kc = self._get_live_kc(layer, idx)
        if live_kc:
            kc = live_kc
        elif self.data and layer < len(self.data.get("keymap",[])):
            kc = self.data["keymap"][layer][idx]
        else:
            kc = label
        # Show friendly name in dropdown
        disp = KC_TO_DISPLAY.get(kc, kc)
        self.sel_label.config(text=f"Key {idx} ({label})", fg=TEXT)
        self.kc_var.set(disp)
        self._draw_keyboard()
        if idx in self._key_items:
            self._flash_key(idx, 0)

    def _nb_draw_mini_kb(self):
        """Draw a small clickable keyboard on the Null Bind tab."""
        c = self.nb_canvas
        c.delete("all")
        U = 36; G = 2; H = 34
        rows = self._get_rows()
        y = 5
        for row in rows:
            x = 5
            for key_idx, label, width in row:
                w = int(width * U)
                is_k1 = self.nb_key1 and self.nb_key1[0] == key_idx
                is_k2 = self.nb_key2 and self.nb_key2[0] == key_idx
                fill = "#44aa44" if is_k1 else ("#4444cc" if is_k2 else BG_KEY)
                outline = "#6f6" if is_k1 else ("#66f" if is_k2 else "#444")
                r = round_rect(c, x, y, x+w-G, y+H, r=5, fill=fill, outline=outline)
                t = c.create_text(x+(w-G)//2, y+H//2, text=label, fill="#fff", font=("Arial",7), width=w-6)
                for item in (r, t):
                    c.tag_bind(item, "<Button-1>", lambda e, ki=key_idx, lb=label: self._nb_click_mini(ki, lb))
                x += w
            y += H + G

    def _nb_click_mini(self, idx, label):
        """Handle click on mini keyboard — first click = key1, second = key2."""
        if self.nb_key1 is None:
            self.nb_key1 = (idx, label)
            self.nb_key1_label.config(text=f"{label} (key {idx})", fg="#44aa44")
            self.nb_key2_label.config(text="(click second key...)", fg=ACCENT)
            self.status.config(text=f"Key 1 = {label} — now click the second key")
        elif self.nb_key2 is None:
            if idx == self.nb_key1[0]:
                return  # same key, ignore
            self.nb_key2 = (idx, label)
            self.nb_key2_label.config(text=f"{label} (key {idx})", fg="#4444cc")
            self.status.config(text=f"Null bind: {self.nb_key1[1]} ↔ {label} — choose mode and Apply")
        else:
            # Reset and start over
            self.nb_key1 = (idx, label)
            self.nb_key2 = None
            self.nb_key1_label.config(text=f"{label} (key {idx})", fg="#44aa44")
            self.nb_key2_label.config(text="(click second key...)", fg=ACCENT)
            self.status.config(text=f"Key 1 = {label} — now click the second key")
        self._nb_draw_mini_kb()

    def _flash_key(self, key_idx, step):
        """Quick flash animation on key select."""
        if key_idx not in self._key_items:
            return
        r, t = self._key_items[key_idx]
        if step < 3:
            color = lerp_color(ACCENT, "#ff4444", step/2.0)
            self.kb_canvas.itemconfig(r, fill=color)
            self.after(30, lambda: self._flash_key(key_idx, step+1))
        else:
            self.kb_canvas.itemconfig(r, fill=ACCENT)

    # Common name aliases -> real keycodes
    FRIENDLY_NAMES = {
        "FN":"MO(1)","FN1":"MO(1)","FN2":"MO(2)","FN3":"MO(3)",
        "MENU":"KC_APP","ENTER":"KC_ENT","RETURN":"KC_ENT",
        "BACKSPACE":"KC_BSPC","DELETE":"KC_DEL","SPACE":"KC_SPC",
        "ESCAPE":"KC_ESC","CAPSLOCK":"KC_CAPS","TAB":"KC_TAB",
        "UP":"KC_UP","DOWN":"KC_DOWN","LEFT":"KC_LEFT","RIGHT":"KC_RGHT",
        "SHIFT":"KC_LSFT","CTRL":"KC_LCTL","ALT":"KC_LALT","WIN":"KC_LGUI",
        "RSHIFT":"KC_RSFT","RCTRL":"KC_RCTL","RALT":"KC_RALT","RWIN":"KC_RGUI",
        "MUTE":"KC_MUTE","VOLUP":"KC_VOLU","VOLDOWN":"KC_VOLD",
        "PLAY":"KC_MPLY","NEXT":"KC_MNXT","PREV":"KC_MPRV",
        "PRINTSCREEN":"KC_PSCR","INSERT":"KC_INS","HOME":"KC_HOME","END":"KC_END",
        "PAGEUP":"KC_PGUP","PAGEDOWN":"KC_PGDN","BOOT":"SP_BOOT",
    }

    def _apply_key(self, event=None):
        if self.selected_key_idx is None:
            return
        layer = self.layer_var.get()
        disp = self.kc_var.get().strip()
        if not disp: return
        # Convert display name to real keycode
        kc = DISPLAY_TO_KC.get(disp, disp)
        # Also check FRIENDLY_NAMES
        up = kc.upper().replace(" ","")
        if up in self.FRIENDLY_NAMES:
            kc = self.FRIENDLY_NAMES[up]
        # Update JSON data if loaded
        if self.data and layer < len(self.data.get("keymap",[])):
            self.data["keymap"][layer][self.selected_key_idx] = kc
        # Send to keyboard via USB
        if self._usb_send_key(layer, self.selected_key_idx, kc):
            self._draw_keyboard()
            self.status.config(text=f"✓ Key {self.selected_key_idx} → {disp} (Layer {layer}) — sent to keyboard")
        else:
            self._draw_keyboard()
            self.status.config(text=f"Key {self.selected_key_idx} → {disp} (Layer {layer}) — saved locally only")

    def _on_search(self, *args):
        q = self.search_var.get().strip().lower()
        if not q:
            self.kc_combo.config(values=KEYCODES)
            self.search_results.config(text="")
            return
        matches = [k for k in KEYCODES if q in k.lower()]
        self.kc_combo.config(values=matches)
        self.search_results.config(text=f"{len(matches)} match{'es' if len(matches)!=1 else ''}")
        if len(matches) == 1:
            self.kc_var.set(matches[0])

    # ── LEFT STICK PAGE ──
    def _build_leftstick_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages["leftstick"] = page
        tk.Label(page, text="Left Stick (Analog WASD → Joystick)", font=("Arial",15,"bold"),
                 fg=TEXT, bg=BG).pack(anchor="w", padx=20, pady=(12,5))
        tk.Label(page, text="Converts WASD key depth into a virtual gamepad left stick. More pressure = more tilt.",
                 font=("Arial",9), fg=TEXT_DIM, bg=BG).pack(anchor="w", padx=20)

        panel = tk.Frame(page, bg=BG_PANEL, highlightbackground="#333", highlightthickness=1)
        panel.pack(fill="x", padx=20, pady=10)
        inner = tk.Frame(panel, bg=BG_PANEL); inner.pack(padx=20, pady=15)

        # Key index config
        tk.Label(inner, text="Key Indices (from keyboard.json):", font=("Arial",10,"bold"),
                 fg=ACCENT, bg=BG_PANEL).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0,8))
        self.ls_w_var = tk.IntVar(value=18)  # W
        self.ls_a_var = tk.IntVar(value=31)  # A
        self.ls_s_var = tk.IntVar(value=32)  # S
        self.ls_d_var = tk.IntVar(value=33)  # D
        for col, (lbl, var) in enumerate([("W (up)",self.ls_w_var),("A (left)",self.ls_a_var),
                                           ("S (down)",self.ls_s_var),("D (right)",self.ls_d_var)]):
            tk.Label(inner, text=lbl, font=("Arial",10), fg=TEXT, bg=BG_PANEL).grid(row=1, column=col, padx=8)
            tk.Spinbox(inner, from_=0, to=66, textvariable=var, width=4, font=("Arial",10),
                       bg="#333", fg=TEXT, buttonbackground="#444", insertbackground=TEXT
                       ).grid(row=2, column=col, padx=8, pady=(0,10))

        # Deadzone
        tk.Label(inner, text="Deadzone:", font=("Arial",10), fg=TEXT, bg=BG_PANEL).grid(row=3, column=0, sticky="w")
        self.ls_deadzone_var = tk.IntVar(value=10)
        tk.Scale(inner, from_=0, to=50, orient="horizontal", variable=self.ls_deadzone_var,
                 length=180, bg=BG_PANEL, fg=TEXT, highlightthickness=0, troughcolor="#333",
                 activebackground=ACCENT).grid(row=3, column=1, columnspan=2, sticky="w")

        # A/D Spam (counter-strafe jitter)
        self.ls_adspam_var = tk.BooleanVar(value=False)
        tk.Checkbutton(inner, text="A/D Spam", variable=self.ls_adspam_var,
                       font=("Arial",10,"bold"), fg=TEXT, bg=BG_PANEL, selectcolor="#444",
                       activebackground=BG_PANEL, activeforeground=TEXT
                       ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(10,0))
        tk.Label(inner, text="Speed (ms):", font=("Arial",9), fg=TEXT_DIM, bg=BG_PANEL).grid(row=5, column=0, sticky="w")
        self.ls_adspam_speed_var = tk.IntVar(value=40)
        tk.Scale(inner, from_=10, to=200, orient="horizontal", variable=self.ls_adspam_speed_var,
                 length=180, bg=BG_PANEL, fg=TEXT, highlightthickness=0, troughcolor="#333",
                 activebackground=ACCENT).grid(row=5, column=1, columnspan=2, sticky="w")

        # Visualization
        vis_f = tk.Frame(page, bg=BG_PANEL, highlightbackground="#333", highlightthickness=1)
        vis_f.pack(fill="x", padx=20, pady=5)
        self.ls_canvas = tk.Canvas(vis_f, width=200, height=200, bg="#222", highlightthickness=0)
        self.ls_canvas.pack(side="left", padx=20, pady=15)
        # WASD depth bars next to visualizer
        bars_f = tk.Frame(vis_f, bg=BG_PANEL); bars_f.pack(side="left", padx=10, pady=15)
        self.ls_depth_labels = {}
        for key in ["W","A","S","D"]:
            row = tk.Frame(bars_f, bg=BG_PANEL); row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{key}:", font=("Arial",11,"bold"), fg=ACCENT, bg=BG_PANEL, width=3).pack(side="left")
            c = tk.Canvas(row, width=120, height=16, bg="#333", highlightthickness=0)
            c.pack(side="left", padx=5)
            lbl = tk.Label(row, text="0%", font=("Arial",9), fg=TEXT_DIM, bg=BG_PANEL, width=5)
            lbl.pack(side="left")
            self.ls_depth_labels[key] = (c, lbl)

        # Start/Stop
        btn_f = tk.Frame(page, bg=BG); btn_f.pack(pady=8)
        self.ls_running = False
        self.ls_uinput_fd = None
        self.ls_btn = tk.Label(btn_f, text="  ▶ Start Left Stick  ", font=("Arial",11,"bold"),
                               fg="#fff", bg=ACCENT, cursor="hand2", padx=12, pady=5)
        self.ls_btn.pack(side="left", padx=5)
        self.ls_btn.bind("<Button-1>", lambda e: self._toggle_leftstick())
        self.ls_status = tk.Label(page, text="", font=("Arial",9), fg=TEXT_DIM, bg=BG)
        self.ls_status.pack(anchor="w", padx=20)

    def _toggle_leftstick(self):
        if self.ls_running:
            self._stop_leftstick()
        else:
            self._start_leftstick()

    def _start_leftstick(self):
        if self.usb_fd is None and not self._try_usb_connect():
            self.ls_status.config(text="⚠ Keyboard not connected"); return
        # Create uinput virtual gamepad
        try:
            self.ls_uinput_fd = self._create_uinput_stick()
        except Exception as e:
            self.ls_status.config(text=f"⚠ uinput failed: {e} (try: sudo modprobe uinput)")
            return
        self.ls_running = True
        self.ls_btn.config(text="  ⏹ Stop Left Stick  ", bg="#666")
        self.ls_status.config(text="✓ Active — WASD still types, stick reads analog depth")
        self._save_ls_config(True)
        self._poll_leftstick()

    def _stop_leftstick(self):
        self.ls_running = False
        self.ls_btn.config(text="  ▶ Start Left Stick  ", bg=ACCENT)
        if self.ls_uinput_fd is not None:
            try:
                import fcntl
                UI_DEV_DESTROY = 0x5502
                fcntl.ioctl(self.ls_uinput_fd, UI_DEV_DESTROY)
                os.close(self.ls_uinput_fd)
            except Exception: pass
            self.ls_uinput_fd = None
        self.ls_status.config(text="Stopped")
        self._save_ls_config(False)

    def _save_ls_config(self, enabled):
        cfg = load_hub_config()
        cfg["leftstick"] = {
            "enabled": enabled,
            "w": self.ls_w_var.get(), "a": self.ls_a_var.get(),
            "s": self.ls_s_var.get(), "d": self.ls_d_var.get(),
            "deadzone": self.ls_deadzone_var.get(),
            "adspam": self.ls_adspam_var.get(),
            "adspam_speed": self.ls_adspam_speed_var.get(),
        }
        save_hub_config(cfg)

    def _load_ls_config(self):
        cfg = load_hub_config().get("leftstick", {})
        if cfg.get("w"): self.ls_w_var.set(cfg["w"])
        if cfg.get("a"): self.ls_a_var.set(cfg["a"])
        if cfg.get("s"): self.ls_s_var.set(cfg["s"])
        if cfg.get("d"): self.ls_d_var.set(cfg["d"])
        if "deadzone" in cfg: self.ls_deadzone_var.set(cfg["deadzone"])
        if "adspam" in cfg: self.ls_adspam_var.set(cfg["adspam"])
        if "adspam_speed" in cfg: self.ls_adspam_speed_var.set(cfg["adspam_speed"])
        if cfg.get("enabled"):
            self.after(500, self._start_leftstick)

    def _create_uinput_stick(self):
        """Create a uinput device with ABS_X and ABS_Y (left stick)."""
        import struct, fcntl

        UI_SET_EVBIT = 0x40045564
        UI_SET_ABSBIT = 0x40045567
        UI_DEV_CREATE = 0x5501
        EV_ABS = 0x03
        EV_SYN = 0x00
        ABS_X = 0x00
        ABS_Y = 0x01

        fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        # Enable EV_ABS
        fcntl.ioctl(fd, UI_SET_EVBIT, EV_ABS)
        fcntl.ioctl(fd, UI_SET_ABSBIT, ABS_X)
        fcntl.ioctl(fd, UI_SET_ABSBIT, ABS_Y)

        # uinput_user_dev struct: name[80] + id(bustype,vendor,product,version) + ff_effects_max + absmax[64] + absmin[64] + absfuzz[64] + absflat[64]
        name = b"ROZ Left Stick" + b'\x00' * (80 - 14)
        # id: bus=0x03(USB), vendor=0xAB50, product=0xAB61, version=1
        dev_id = struct.pack("<HHHH", 0x03, 0xAB50, 0xAB61, 1)
        ff = struct.pack("<i", 0)
        # absmax[64]: set [0]=32767, [1]=32767
        absmax = [0]*64; absmax[0] = 32767; absmax[1] = 32767
        absmin = [0]*64; absmin[0] = -32767; absmin[1] = -32767
        absfuzz = [0]*64; absfuzz[0] = 16; absfuzz[1] = 16
        absflat = [0]*64; absflat[0] = 128; absflat[1] = 128

        user_dev = name + dev_id + ff
        user_dev += struct.pack("<64i", *absmax)
        user_dev += struct.pack("<64i", *absmin)
        user_dev += struct.pack("<64i", *absfuzz)
        user_dev += struct.pack("<64i", *absflat)

        os.write(fd, user_dev)
        fcntl.ioctl(fd, UI_DEV_CREATE)
        import time; time.sleep(0.1)
        return fd

    def _emit_stick(self, x, y):
        """Write ABS_X, ABS_Y, SYN to uinput."""
        import struct
        EV_ABS = 0x03; EV_SYN = 0x00; SYN_REPORT = 0x00
        ABS_X = 0x00; ABS_Y = 0x01
        # input_event: struct timeval(16 bytes on 64-bit) + type(H) + code(H) + value(i)
        now = struct.pack("<QQ", 0, 0)  # kernel fills timestamp
        os.write(self.ls_uinput_fd, now + struct.pack("<HHi", EV_ABS, ABS_X, x))
        os.write(self.ls_uinput_fd, now + struct.pack("<HHi", EV_ABS, ABS_Y, y))
        os.write(self.ls_uinput_fd, now + struct.pack("<HHi", EV_SYN, SYN_REPORT, 0))

    def _poll_leftstick(self):
        if not self.ls_running:
            return
        try:
            w_idx = self.ls_w_var.get()
            a_idx = self.ls_a_var.get()
            s_idx = self.ls_s_var.get()
            d_idx = self.ls_d_var.get()
            deadzone = self.ls_deadzone_var.get()

            # Read depths for all 4 keys
            depths = {}
            for idx, key in [(w_idx,"W"),(a_idx,"A"),(s_idx,"S"),(d_idx,"D")]:
                chunk_offset = (idx // 21) * 21
                resp = usb_cmd(self.usb_fd, 5, bytes([chunk_offset]))
                if resp[0] == 5:
                    i = idx - chunk_offset
                    depths[key] = resp[3 + i * 3]  # distance byte 0-255
                else:
                    depths[key] = 0

            # Apply deadzone
            for k in depths:
                if depths[k] < deadzone:
                    depths[k] = 0

            # Calculate axis: X = D - A, Y = S - W (down positive in gamepad convention)
            raw_x = depths["D"] - depths["A"]  # -255 to +255
            raw_y = depths["S"] - depths["W"]  # -255 to +255

            # Normalize to circle (clamp magnitude to 255)
            import math
            mag = math.sqrt(raw_x*raw_x + raw_y*raw_y)
            if mag > 255:
                raw_x = int(raw_x * 255 / mag)
                raw_y = int(raw_y * 255 / mag)

            # Scale to joystick range (-32767 to 32767)
            axis_x = int(raw_x * 32767 / 255)
            axis_y = int(raw_y * 32767 / 255)
            axis_x = max(-32767, min(32767, axis_x))
            axis_y = max(-32767, min(32767, axis_y))

            # A/D spam: rapidly alternate X axis direction
            if self.ls_adspam_var.get():
                import time
                now = int(time.time() * 1000)
                period = self.ls_adspam_speed_var.get()
                if (now // period) % 2 == 0:
                    axis_x = 32767
                else:
                    axis_x = -32767

            # Emit to uinput
            self._emit_stick(axis_x, axis_y)

            # Update visualization
            self._draw_leftstick_vis(raw_x/255.0, raw_y/255.0, depths)

        except Exception as e:
            self.ls_status.config(text=f"⚠ {e}")
            self._stop_leftstick()
            return

        self.after(4, self._poll_leftstick)  # ~250Hz

    def _draw_leftstick_vis(self, nx, ny, depths):
        """Draw stick position on canvas and depth bars."""
        c = self.ls_canvas
        c.delete("all")
        cx, cy = 100, 100; r = 90
        # Outer circle
        c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#444", width=2)
        # Crosshair
        c.create_line(cx-r, cy, cx+r, cy, fill="#333")
        c.create_line(cx, cy-r, cx, cy+r, fill="#333")
        # Deadzone circle
        dz = self.ls_deadzone_var.get() / 255.0 * r
        c.create_oval(cx-dz, cy-dz, cx+dz, cy+dz, outline="#555", dash=(2,2))
        # Stick position
        sx = cx + nx * r
        sy = cy + ny * r
        c.create_oval(sx-8, sy-8, sx+8, sy+8, fill=ACCENT, outline="#ff4444")
        # Line from center
        c.create_line(cx, cy, sx, sy, fill=ACCENT, width=2)

        # Depth bars
        for key in ["W","A","S","D"]:
            bar_c, lbl = self.ls_depth_labels[key]
            bar_c.delete("all")
            val = depths.get(key, 0)
            pct = val / 255.0
            bar_w = int(pct * 118)
            bar_c.create_rectangle(1, 1, 1+bar_w, 15, fill=ACCENT, outline="")
            lbl.config(text=f"{int(pct*100)}%")

    # ── LAYOUT PAGE ──
    def _build_layout_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages["layout"] = page
        tk.Label(page, text="Layout Options", font=("Arial",15,"bold"),
                 fg=TEXT, bg=BG).pack(anchor="w", padx=20, pady=(12,10))
        panel = tk.Frame(page, bg=BG_PANEL, highlightbackground="#333", highlightthickness=1)
        panel.pack(fill="x", padx=20, pady=5)
        inner = tk.Frame(panel, bg=BG_PANEL); inner.pack(padx=20, pady=20, anchor="w")
        opts = [("Backspace",["2U Backspace","Split Backspace"]),
                ("Right Shift",["Standard"]),
                ("Bottom Row",["7U Spacebar","Split Spacebar"])]
        self.layout_vars = []
        for label, choices in opts:
            tk.Label(inner, text=label+":", font=("Arial",11,"bold"), fg=ACCENT,
                     bg=BG_PANEL).pack(anchor="w", pady=(10,3))
            var = tk.IntVar(value=0); self.layout_vars.append(var)
            for ci, ch in enumerate(choices):
                tk.Radiobutton(inner, text=ch, variable=var, value=ci, font=("Arial",10),
                               fg=TEXT, bg=BG_PANEL, selectcolor="#444",
                               activebackground=BG_PANEL, activeforeground=TEXT,
                               command=self._on_layout_change).pack(anchor="w", padx=20)

    def _on_layout_change(self):
        self.layout_opts = [v.get() for v in self.layout_vars]
        self._draw_keyboard()

    # ── ACTUATION PAGE ──
    def _build_actuation_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages["actuation"] = page
        tk.Label(page, text="Actuation & Advanced Keys", font=("Arial",15,"bold"),
                 fg=TEXT, bg=BG).pack(anchor="w", padx=20, pady=(12,5))
        tk.Label(page, text="Select a key on Key Assignment first, then configure here.",
                 font=("Arial",9), fg=TEXT_DIM, bg=BG).pack(anchor="w", padx=20)

        # Sub-tabs
        nb = ttk.Notebook(page)
        nb.pack(fill="both", expand=True, padx=20, pady=8)

        # ── Rapid Trigger tab ──
        rt_f = tk.Frame(nb, bg=BG_PANEL); nb.add(rt_f, text="  Rapid Trigger  ")
        rt = tk.Frame(rt_f, bg=BG_PANEL); rt.pack(padx=20, pady=15)

        self.act_key_label = tk.Label(rt, text="No key selected", font=("Arial",12,"bold"),
                                      fg=ACCENT, bg=BG_PANEL)
        self.act_key_label.grid(row=0, column=0, columnspan=3, pady=(0,10), sticky="w")

        tk.Label(rt, text="Actuation Point:", font=("Arial",11), fg=TEXT, bg=BG_PANEL).grid(row=1, column=0, sticky="w", pady=4)
        self.act_point_var = tk.IntVar(value=50)
        tk.Scale(rt, from_=1, to=255, orient="horizontal", variable=self.act_point_var,
                 length=280, bg=BG_PANEL, fg=TEXT, highlightthickness=0, troughcolor="#333",
                 activebackground=ACCENT).grid(row=1, column=1, padx=10)
        self.act_point_mm = tk.Label(rt, text="", font=("Arial",10), fg=TEXT_DIM, bg=BG_PANEL)
        self.act_point_mm.grid(row=1, column=2)
        self.act_point_var.trace_add("write", lambda *a: self.act_point_mm.config(
            text=f"~{self.act_point_var.get()*4.0/255:.1f}mm"))

        tk.Label(rt, text="RT Press:", font=("Arial",11), fg=TEXT, bg=BG_PANEL).grid(row=2, column=0, sticky="w", pady=4)
        self.rt_down_var = tk.IntVar(value=30)
        tk.Scale(rt, from_=0, to=255, orient="horizontal", variable=self.rt_down_var,
                 length=280, bg=BG_PANEL, fg=TEXT, highlightthickness=0, troughcolor="#333",
                 activebackground=ACCENT).grid(row=2, column=1, padx=10)

        tk.Label(rt, text="RT Release:", font=("Arial",11), fg=TEXT, bg=BG_PANEL).grid(row=3, column=0, sticky="w", pady=4)
        self.rt_up_var = tk.IntVar(value=30)
        tk.Scale(rt, from_=0, to=255, orient="horizontal", variable=self.rt_up_var,
                 length=280, bg=BG_PANEL, fg=TEXT, highlightthickness=0, troughcolor="#333",
                 activebackground=ACCENT).grid(row=3, column=1, padx=10)

        self.crt_var = tk.BooleanVar(value=False)
        tk.Checkbutton(rt, text="Continuous Rapid Trigger", variable=self.crt_var,
                       font=("Arial",11), fg=TEXT, bg=BG_PANEL, selectcolor="#444",
                       activebackground=BG_PANEL, activeforeground=TEXT
                       ).grid(row=4, column=0, columnspan=2, sticky="w", pady=8)

        # Live key depth indicator
        depth_f = tk.Frame(rt, bg=BG_PANEL)
        depth_f.grid(row=5, column=0, columnspan=3, pady=(10,4), sticky="ew")
        tk.Label(depth_f, text="Live Depth:", font=("Arial",10), fg=TEXT_DIM, bg=BG_PANEL).pack(side="left")
        self.act_depth_canvas = tk.Canvas(depth_f, width=280, height=24, bg="#222", highlightthickness=0)
        self.act_depth_canvas.pack(side="left", padx=8)
        self.act_depth_label = tk.Label(depth_f, text="0.0mm", font=("Arial",10,"bold"), fg=ACCENT, bg=BG_PANEL)
        self.act_depth_label.pack(side="left")
        self.act_depth_running = False

        btn_f = tk.Frame(rt, bg=BG_PANEL); btn_f.grid(row=6, column=0, columnspan=3, pady=8)
        ab = tk.Label(btn_f, text="  Apply to Key  ", font=("Arial",10,"bold"), fg="#fff",
                      bg=ACCENT, cursor="hand2", padx=10, pady=3)
        ab.pack(side="left", padx=5); ab.bind("<Button-1>", lambda e: self._apply_actuation())
        ab2 = tk.Label(btn_f, text="  Apply to All  ", font=("Arial",10,"bold"), fg="#fff",
                       bg="#666", cursor="hand2", padx=10, pady=3)
        ab2.pack(side="left", padx=5); ab2.bind("<Button-1>", lambda e: self._apply_actuation_all())

        # ── Null Bind (SNAPPY/SOCD) tab ──
        nb_f = tk.Frame(nb, bg=BG_PANEL); nb.add(nb_f, text="  Null Bind (SOCD)  ")

        # Top: settings row
        nbi = tk.Frame(nb_f, bg=BG_PANEL); nbi.pack(fill="x", padx=15, pady=(10,0))

        self.nb_picking = False
        self.nb_key1 = None
        self.nb_key2 = None

        tk.Label(nbi, text="Key 1:", font=("Arial",10), fg=TEXT_DIM, bg=BG_PANEL).grid(row=0, column=0, sticky="w")
        self.nb_key1_label = tk.Label(nbi, text="(click below)", font=("Arial",10,"bold"), fg=ACCENT, bg=BG_PANEL)
        self.nb_key1_label.grid(row=0, column=1, padx=(5,20))

        tk.Label(nbi, text="Key 2:", font=("Arial",10), fg=TEXT_DIM, bg=BG_PANEL).grid(row=0, column=2, sticky="w")
        self.nb_key2_label = tk.Label(nbi, text="(click below)", font=("Arial",10,"bold"), fg=TEXT_DIM, bg=BG_PANEL)
        self.nb_key2_label.grid(row=0, column=3, padx=(5,20))

        tk.Label(nbi, text="Mode:", font=("Arial",10), fg=TEXT_DIM, bg=BG_PANEL).grid(row=0, column=4, sticky="w")
        self.nb_behavior_var = tk.StringVar(value="Last Pressed")
        ttk.Combobox(nbi, textvariable=self.nb_behavior_var, state="readonly",
                     values=["Last Pressed","Primary Wins","Secondary Wins","Neutral","Distance"],
                     width=14, font=("Arial",9)).grid(row=0, column=5, padx=5)

        ab3 = tk.Label(nbi, text="  Apply  ", font=("Arial",10,"bold"), fg="#fff",
                       bg=ACCENT, cursor="hand2", padx=8, pady=2)
        ab3.grid(row=0, column=6, padx=(15,0))
        ab3.bind("<Button-1>", lambda e: self._apply_advanced("null_bind"))

        # Mini keyboard canvas for picking keys
        self.nb_canvas = tk.Canvas(nb_f, height=5*(34+3)+10, bg=BG_PANEL, highlightthickness=0)
        self.nb_canvas.pack(fill="x", padx=15, pady=(8,10))
        self._nb_draw_mini_kb()

        # ── Dynamic Keystroke (DKS) tab ──
        dks_f = tk.Frame(nb, bg=BG_PANEL); nb.add(dks_f, text="  Dynamic Keystroke  ")
        dksi = tk.Frame(dks_f, bg=BG_PANEL); dksi.pack(padx=20, pady=15)

        tk.Label(dksi, text="Bind up to 4 keycodes to different phases of a keypress.",
                 font=("Arial",10), fg=TEXT_DIM, bg=BG_PANEL).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0,10))

        phases = ["Press","Bottom-Out","Release BO","Release"]
        self.dks_kc_vars = []
        self.dks_action_vars = []
        tk.Label(dksi, text="Keycode", font=("Arial",10,"bold"), fg=ACCENT, bg=BG_PANEL).grid(row=1, column=0, padx=5)
        for j, ph in enumerate(phases):
            tk.Label(dksi, text=ph, font=("Arial",9,"bold"), fg=ACCENT, bg=BG_PANEL).grid(row=1, column=j+1, padx=3)

        for i in range(4):
            kv = tk.StringVar()
            self.dks_kc_vars.append(kv)
            ttk.Combobox(dksi, textvariable=kv, values=KEYCODES, width=12,
                         font=("Arial",9)).grid(row=i+2, column=0, padx=5, pady=2)
            row_actions = []
            for j in range(4):
                av = tk.StringVar(value="Hold")
                row_actions.append(av)
                ttk.Combobox(dksi, textvariable=av, state="readonly",
                             values=["Hold","Press","Release","Tap"], width=7,
                             font=("Arial",9)).grid(row=i+2, column=j+1, padx=3, pady=2)
            self.dks_action_vars.append(row_actions)

        tk.Label(dksi, text="Bottom-Out Point:", font=("Arial",10), fg=TEXT, bg=BG_PANEL).grid(row=7, column=0, sticky="w", pady=8)
        self.dks_bottom_var = tk.IntVar(value=128)
        tk.Scale(dksi, from_=0, to=255, orient="horizontal", variable=self.dks_bottom_var,
                 length=200, bg=BG_PANEL, fg=TEXT, highlightthickness=0, troughcolor="#333",
                 activebackground=ACCENT).grid(row=7, column=1, columnspan=2, padx=10)

        ab4 = tk.Label(dksi, text="  Apply DKS  ", font=("Arial",10,"bold"), fg="#fff",
                       bg=ACCENT, cursor="hand2", padx=10, pady=3)
        ab4.grid(row=8, column=0, columnspan=5, pady=10)
        ab4.bind("<Button-1>", lambda e: self._apply_advanced("dks"))

        # ── Tap-Hold tab ──
        th_f = tk.Frame(nb, bg=BG_PANEL); nb.add(th_f, text="  Tap-Hold  ")
        thi = tk.Frame(th_f, bg=BG_PANEL); thi.pack(padx=20, pady=15)

        tk.Label(thi, text="Tap for one key, hold for another.",
                 font=("Arial",10), fg=TEXT_DIM, bg=BG_PANEL).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,10))

        tk.Label(thi, text="Tap Key:", font=("Arial",11), fg=TEXT, bg=BG_PANEL).grid(row=1, column=0, sticky="w", pady=5)
        self.th_tap_var = tk.StringVar()
        ttk.Combobox(thi, textvariable=self.th_tap_var, values=KEYCODES, width=18,
                     font=("Arial",10)).grid(row=1, column=1, padx=10)

        tk.Label(thi, text="Hold Key:", font=("Arial",11), fg=TEXT, bg=BG_PANEL).grid(row=2, column=0, sticky="w", pady=5)
        self.th_hold_var = tk.StringVar()
        ttk.Combobox(thi, textvariable=self.th_hold_var, values=KEYCODES, width=18,
                     font=("Arial",10)).grid(row=2, column=1, padx=10)

        tk.Label(thi, text="Tapping Term (ms):", font=("Arial",11), fg=TEXT, bg=BG_PANEL).grid(row=3, column=0, sticky="w", pady=5)
        self.th_term_var = tk.IntVar(value=200)
        tk.Spinbox(thi, from_=50, to=1000, increment=10, textvariable=self.th_term_var,
                   width=8, font=("Arial",11), bg="#333", fg=TEXT, buttonbackground="#444",
                   insertbackground=TEXT).grid(row=3, column=1, padx=10, sticky="w")

        self.th_hold_other_var = tk.BooleanVar(value=False)
        tk.Checkbutton(thi, text="Hold on other key press", variable=self.th_hold_other_var,
                       font=("Arial",10), fg=TEXT, bg=BG_PANEL, selectcolor="#444",
                       activebackground=BG_PANEL, activeforeground=TEXT
                       ).grid(row=4, column=0, columnspan=2, sticky="w", pady=8)

        ab5 = tk.Label(thi, text="  Apply Tap-Hold  ", font=("Arial",10,"bold"), fg="#fff",
                       bg=ACCENT, cursor="hand2", padx=10, pady=3)
        ab5.grid(row=5, column=0, columnspan=2, pady=10)
        ab5.bind("<Button-1>", lambda e: self._apply_advanced("tap_hold"))

        # ── Toggle tab ──
        tg_f = tk.Frame(nb, bg=BG_PANEL); nb.add(tg_f, text="  Toggle  ")
        tgi = tk.Frame(tg_f, bg=BG_PANEL); tgi.pack(padx=20, pady=15)

        tk.Label(tgi, text="Tap to toggle a key on/off.",
                 font=("Arial",10), fg=TEXT_DIM, bg=BG_PANEL).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,10))

        tk.Label(tgi, text="Toggle Key:", font=("Arial",11), fg=TEXT, bg=BG_PANEL).grid(row=1, column=0, sticky="w", pady=5)
        self.tg_key_var = tk.StringVar()
        ttk.Combobox(tgi, textvariable=self.tg_key_var, values=KEYCODES, width=18,
                     font=("Arial",10)).grid(row=1, column=1, padx=10)

        tk.Label(tgi, text="Tapping Term (ms):", font=("Arial",11), fg=TEXT, bg=BG_PANEL).grid(row=2, column=0, sticky="w", pady=5)
        self.tg_term_var = tk.IntVar(value=200)
        tk.Spinbox(tgi, from_=50, to=1000, increment=10, textvariable=self.tg_term_var,
                   width=8, font=("Arial",11), bg="#333", fg=TEXT, buttonbackground="#444",
                   insertbackground=TEXT).grid(row=2, column=1, padx=10, sticky="w")

        ab6 = tk.Label(tgi, text="  Apply Toggle  ", font=("Arial",10,"bold"), fg="#fff",
                       bg=ACCENT, cursor="hand2", padx=10, pady=3)
        ab6.grid(row=3, column=0, columnspan=2, pady=15)
        ab6.bind("<Button-1>", lambda e: self._apply_advanced("toggle"))

    def _apply_advanced(self, mode):
        """Send advanced key config to keyboard."""
        if mode == "null_bind":
            if self.nb_key1 is None or self.nb_key2 is None:
                messagebox.showinfo("Info", "Click 'Pick Keys' and select two keys on the keyboard first")
                return
        elif self.selected_key_idx is None:
            messagebox.showinfo("Info", "Select a key first")
            return
        if self.usb_fd is None and not self._try_usb_connect():
            self.status.config(text="⚠ Keyboard not connected"); return
        try:
            import struct
            layer = self.layer_var.get()
            key = self.selected_key_idx
            # CMD_SET_ADVANCED_KEYS = 133
            if mode == "null_bind":
                key = self.nb_key1[0]
                key2 = self.nb_key2[0]
                beh = ["Last Pressed","Primary Wins","Secondary Wins","Neutral","Distance"].index(self.nb_behavior_var.get())
                ak_data = struct.pack("BBBBBBB", layer, key, 1, key2, beh, self.nb_bottom_var.get(), 0)
            elif mode == "dks":
                kcs = []
                for v in self.dks_kc_vars:
                    name = v.get().strip()
                    b = kc_to_byte(DISPLAY_TO_KC.get(name, name)) if name else 0
                    kcs.append(b or 0)
                bitmaps = []
                act_map = {"Hold":0,"Press":1,"Release":2,"Tap":3}
                for row in self.dks_action_vars:
                    bm = 0
                    for j, av in enumerate(row):
                        bm |= act_map[av.get()] << (j*2)
                    bitmaps.append(bm)
                ak_data = struct.pack("BBB4B4BB", layer, key, 2, *kcs, *bitmaps, self.dks_bottom_var.get())
            elif mode == "tap_hold":
                tap = kc_to_byte(DISPLAY_TO_KC.get(self.th_tap_var.get(), self.th_tap_var.get()))
                hold = kc_to_byte(DISPLAY_TO_KC.get(self.th_hold_var.get(), self.th_hold_var.get()))
                if tap is None or hold is None: self.status.config(text="⚠ Invalid keycode"); return
                ak_data = struct.pack("<BBBBBHB", layer, key, 3, tap, hold,
                                      self.th_term_var.get(), 1 if self.th_hold_other_var.get() else 0)
            elif mode == "toggle":
                kc = kc_to_byte(DISPLAY_TO_KC.get(self.tg_key_var.get(), self.tg_key_var.get()))
                if kc is None: self.status.config(text="⚠ Invalid keycode"); return
                ak_data = struct.pack("<BBBH", kc, 0, 0, self.tg_term_var.get())
                ak_data = struct.pack("BBB", layer, key, 4) + ak_data
            else:
                return

            # Find a free slot or overwrite existing for this layer+key
            # For now send to slot 0 offset — firmware handles dedup
            payload = bytes([self.usb_profile, 0, 1]) + ak_data.ljust(12, b'\x00')
            resp = usb_cmd(self.usb_fd, 133, payload)
            if resp[0] == 133:
                if mode == "null_bind":
                    self.status.config(text=f"✓ Null bind: {self.nb_key1[1]} ↔ {self.nb_key2[1]} ({self.nb_behavior_var.get()})")
                else:
                    self.status.config(text=f"✓ {mode.replace('_',' ').title()} set for key {key}")
            else:
                self.status.config(text=f"⚠ Failed to set {mode}")
        except Exception as e:
            self.status.config(text=f"⚠ {e}")

    def _apply_actuation(self):
        if self.selected_key_idx is None:
            messagebox.showinfo("Info", "Select a key first on the Key Assignment page")
            return
        if self.usb_fd is None and not self._try_usb_connect():
            self.status.config(text="⚠ Keyboard not connected"); return
        try:
            import struct
            data = struct.pack("BBBB", self.act_point_var.get(), self.rt_down_var.get(),
                               self.rt_up_var.get(), 1 if self.crt_var.get() else 0)
            payload = bytes([self.usb_profile, self.selected_key_idx, 1]) + data
            resp = usb_cmd(self.usb_fd, 131, payload)
            if resp[0] == 131:
                self.status.config(text=f"✓ Actuation set for key {self.selected_key_idx}")
            else:
                self.status.config(text="⚠ Failed to set actuation")
        except Exception as e:
            self.status.config(text=f"⚠ {e}")

    def _apply_actuation_all(self):
        if self.usb_fd is None and not self._try_usb_connect():
            self.status.config(text="⚠ Keyboard not connected"); return
        try:
            import struct
            one_key = struct.pack("BBBB", self.act_point_var.get(), self.rt_down_var.get(),
                                  self.rt_up_var.get(), 1 if self.crt_var.get() else 0)
            for offset in range(0, self.num_keys, 15):
                count = min(15, self.num_keys - offset)
                payload = bytes([self.usb_profile, offset, count]) + one_key * count
                resp = usb_cmd(self.usb_fd, 131, payload)
                if resp[0] != 131:
                    self.status.config(text=f"⚠ Failed at offset {offset}"); return
            self.status.config(text=f"✓ Actuation set for all {self.num_keys} keys")
        except Exception as e:
            self.status.config(text=f"⚠ {e}")

    def _poll_act_depth(self):
        """Poll the selected key's live distance and draw on the actuation depth bar."""
        if not self.act_depth_running or self.current_page != "actuation":
            self.act_depth_running = False
            return
        key_idx = self.selected_key_idx
        if key_idx is None or self.usb_fd is None:
            self.act_depth_canvas.delete("all")
            self.act_depth_label.config(text="—")
            self.after(100, self._poll_act_depth)
            return
        try:
            chunk_offset = (key_idx // 21) * 21
            resp = usb_cmd(self.usb_fd, 5, bytes([chunk_offset]))
            if resp[0] == 5:
                i = key_idx - chunk_offset
                dist = resp[3 + i * 3]  # distance byte
                mm = dist * 4.0 / 255
                # Draw bar
                self.act_depth_canvas.delete("all")
                bar_w = int(dist * 276 / 255)
                color = ACCENT if dist > 50 else "#555"
                self.act_depth_canvas.create_rectangle(2, 2, 2 + bar_w, 22, fill=color, outline="")
                # Draw actuation point marker
                act_pt = self.act_point_var.get()
                marker_x = 2 + int(act_pt * 276 / 255)
                self.act_depth_canvas.create_line(marker_x, 0, marker_x, 24, fill="#ffcc00", width=2)
                self.act_depth_label.config(text=f"{mm:.1f}mm")
        except Exception:
            pass
        self.after(30, self._poll_act_depth)

    def _start_act_depth(self):
        if not self.act_depth_running:
            self.act_depth_running = True
            self._poll_act_depth()

    # ── ANALOG VIEWER PAGE ──
    def _build_analog_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages["analog"] = page
        tk.Label(page, text="Analog Key Viewer", font=("Arial",15,"bold"),
                 fg=TEXT, bg=BG).pack(anchor="w", padx=20, pady=(12,5))
        tk.Label(page, text="Live visualization of key press depth (requires USB connection).",
                 font=("Arial",9), fg=TEXT_DIM, bg=BG).pack(anchor="w", padx=20)

        self.analog_canvas = tk.Canvas(page, height=300, bg=BG_PANEL, highlightthickness=0)
        self.analog_canvas.pack(fill="x", padx=20, pady=10)

        bf = tk.Frame(page, bg=BG)
        bf.pack(pady=5)
        self.analog_running = False
        self.analog_btn = tk.Label(bf, text="  ▶ Start  ", font=("Arial",10,"bold"), fg="#fff",
                                   bg=ACCENT, cursor="hand2", padx=10, pady=3)
        self.analog_btn.pack(side="left", padx=5)
        self.analog_btn.bind("<Button-1>", lambda e: self._toggle_analog())

    def _toggle_analog(self):
        self.analog_running = not self.analog_running
        self.analog_btn.config(text="  ⏹ Stop  " if self.analog_running else "  ▶ Start  ")
        if self.analog_running:
            self._poll_analog()

    def _poll_analog(self):
        if not self.analog_running:
            return
        if self.usb_fd is None and not self._try_usb_connect():
            self.analog_running = False
            self.analog_btn.config(text="  ▶ Start  ")
            return
        try:
            self.analog_canvas.delete("all")
            bar_w = 12
            pad = 5
            # Read analog values in chunks (CMD_ANALOG_INFO = 5)
            all_vals = []
            for offset in range(0, self.num_keys, 21):
                resp = usb_cmd(self.usb_fd, 5, bytes([offset]))
                if resp[0] != 5: break
                for i in range(min(21, self.num_keys - offset)):
                    adc = resp[1 + i*3] | (resp[2 + i*3] << 8)
                    dist = resp[3 + i*3]
                    all_vals.append((adc, dist))

            for i, (adc, dist) in enumerate(all_vals):
                x = pad + i * (bar_w + 2)
                h = dist * 280 // 255
                color = ACCENT if dist > 50 else "#444"
                self.analog_canvas.create_rectangle(x, 290-h, x+bar_w, 290,
                    fill=color, outline="")
                if dist > 10:
                    self.analog_canvas.create_text(x+bar_w//2, 285-h, text=str(dist),
                        fill=TEXT, font=("Arial",6), anchor="s")
            self.after(50, self._poll_analog)
        except Exception:
            self.analog_running = False
            self.analog_btn.config(text="  ▶ Start  ")

    # ── GAMEPAD PAGE ──
    def _build_gamepad_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages["gamepad"] = page
        tk.Label(page, text="Gamepad / XInput", font=("Arial",15,"bold"),
                 fg=TEXT, bg=BG).pack(anchor="w", padx=20, pady=(12,5))

        # Options panel
        opt_panel = tk.Frame(page, bg=BG_PANEL, highlightbackground="#333", highlightthickness=1)
        opt_panel.pack(fill="x", padx=20, pady=8)
        opt_inner = tk.Frame(opt_panel, bg=BG_PANEL); opt_inner.pack(padx=20, pady=15)

        self.xinput_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt_inner, text="Enable XInput (Gamepad Mode)", variable=self.xinput_var,
                       font=("Arial",11), fg=TEXT, bg=BG_PANEL, selectcolor="#444",
                       activebackground=BG_PANEL, activeforeground=TEXT
                       ).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)

        self.poll_8k_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opt_inner, text="8kHz Polling Rate (USB HS)", variable=self.poll_8k_var,
                       font=("Arial",11), fg=TEXT, bg=BG_PANEL, selectcolor="#444",
                       activebackground=BG_PANEL, activeforeground=TEXT
                       ).grid(row=1, column=0, columnspan=2, sticky="w", pady=5)

        tk.Label(opt_inner, text="Tick Rate:", font=("Arial",11), fg=TEXT,
                 bg=BG_PANEL).grid(row=2, column=0, sticky="w", pady=5)
        self.tick_rate_var = tk.IntVar(value=1)
        tk.Spinbox(opt_inner, from_=1, to=255, textvariable=self.tick_rate_var, width=6,
                   font=("Arial",11), bg="#333", fg=TEXT, buttonbackground="#444",
                   insertbackground=TEXT).grid(row=2, column=1, sticky="w", padx=10)

        btn_f = tk.Frame(opt_inner, bg=BG_PANEL)
        btn_f.grid(row=3, column=0, columnspan=2, pady=10)
        ab = tk.Label(btn_f, text="  Apply Options  ", font=("Arial",10,"bold"), fg="#fff",
                      bg=ACCENT, cursor="hand2", padx=10, pady=3)
        ab.pack(side="left", padx=5)
        ab.bind("<Button-1>", lambda e: self._apply_options())

        # Gamepad buttons info
        gp_panel = tk.Frame(page, bg=BG_PANEL, highlightbackground="#333", highlightthickness=1)
        gp_panel.pack(fill="x", padx=20, pady=5)
        tk.Label(gp_panel, text="Gamepad Button Mapping", font=("Arial",12,"bold"),
                 fg=ACCENT, bg=BG_PANEL).pack(anchor="w", padx=20, pady=(15,5))
        tk.Label(gp_panel, text="Select a key on Key Assignment, then assign a gamepad button here.",
                 font=("Arial",9), fg=TEXT_DIM, bg=BG_PANEL).pack(anchor="w", padx=20)

        gpi = tk.Frame(gp_panel, bg=BG_PANEL); gpi.pack(padx=20, pady=10)
        tk.Label(gpi, text="Button:", font=("Arial",11), fg=TEXT, bg=BG_PANEL).pack(side="left")
        self.gp_btn_var = tk.StringVar(value="None")
        ttk.Combobox(gpi, textvariable=self.gp_btn_var, state="readonly", width=15,
                     values=["None","A","B","X","Y","LB","RB","LT","RT",
                             "Start","Back","L-Stick","R-Stick",
                             "D-Up","D-Down","D-Left","D-Right"],
                     font=("Arial",10)).pack(side="left", padx=10)
        ab2 = tk.Label(gpi, text="  Apply  ", font=("Arial",10,"bold"), fg="#fff",
                       bg=ACCENT, cursor="hand2", padx=8, pady=2)
        ab2.pack(side="left", padx=5)
        ab2.bind("<Button-1>", lambda e: self._apply_gamepad_btn())

        # Profile management
        prof_panel = tk.Frame(page, bg=BG_PANEL, highlightbackground="#333", highlightthickness=1)
        prof_panel.pack(fill="x", padx=20, pady=8)
        tk.Label(prof_panel, text="Profile & Maintenance", font=("Arial",12,"bold"),
                 fg=ACCENT, bg=BG_PANEL).pack(anchor="w", padx=20, pady=(15,5))
        pf = tk.Frame(prof_panel, bg=BG_PANEL); pf.pack(padx=20, pady=10)

        for txt, cmd_id, color in [
            ("Recalibrate", 4, "#555"),
            ("Reset Profile", 11, "#555"),
            ("Factory Reset", 3, "#882222"),
        ]:
            b = tk.Label(pf, text=f"  {txt}  ", font=("Arial",10,"bold"), fg="#fff",
                         bg=color, cursor="hand2", padx=10, pady=3)
            b.pack(side="left", padx=5)
            b.bind("<Button-1>", lambda e, c=cmd_id, t=txt: self._device_cmd(c, t))

    def _apply_options(self):
        if self.usb_fd is None and not self._try_usb_connect():
            self.status.config(text="⚠ Keyboard not connected"); return
        try:
            import struct
            raw = (1 if self.xinput_var.get() else 0) | ((1 if self.poll_8k_var.get() else 0) << 2)
            payload = struct.pack("<H", raw)
            resp = usb_cmd(self.usb_fd, 10, payload)  # CMD_SET_OPTIONS = 10
            if resp[0] == 10:
                # Also set tick rate
                resp2 = usb_cmd(self.usb_fd, 135, bytes([self.usb_profile, self.tick_rate_var.get()]))
                self.status.config(text="✓ Options applied")
            else:
                self.status.config(text="⚠ Failed")
        except Exception as e:
            self.status.config(text=f"⚠ {e}")

    def _apply_gamepad_btn(self):
        if self.selected_key_idx is None:
            messagebox.showinfo("Info", "Select a key first"); return
        if self.usb_fd is None and not self._try_usb_connect():
            self.status.config(text="⚠ Keyboard not connected"); return
        try:
            btns = ["None","A","B","X","Y","LB","RB","LT","RT",
                    "Start","Back","L-Stick","R-Stick","D-Up","D-Down","D-Left","D-Right"]
            val = btns.index(self.gp_btn_var.get())
            # CMD_SET_GAMEPAD_BUTTONS = 137
            payload = bytes([self.usb_profile, self.selected_key_idx, 1, val])
            resp = usb_cmd(self.usb_fd, 137, payload)
            if resp[0] == 137:
                self.status.config(text=f"✓ Gamepad button set for key {self.selected_key_idx}")
            else:
                self.status.config(text="⚠ Failed")
        except Exception as e:
            self.status.config(text=f"⚠ {e}")

    def _device_cmd(self, cmd_id, name):
        if cmd_id == 3:  # Factory reset
            if not messagebox.askyesno("Confirm", "Factory reset? This erases ALL settings."):
                return
        if cmd_id == 11:  # Reset profile
            if not messagebox.askyesno("Confirm", f"Reset profile {self.usb_profile}?"):
                return
        if self.usb_fd is None and not self._try_usb_connect():
            self.status.config(text="⚠ Keyboard not connected"); return
        try:
            if cmd_id == 11:
                resp = usb_cmd(self.usb_fd, cmd_id, bytes([self.usb_profile]))
            else:
                resp = usb_cmd(self.usb_fd, cmd_id)
            if resp[0] == cmd_id:
                self.status.config(text=f"✓ {name} done")
            else:
                self.status.config(text=f"⚠ {name} failed")
        except Exception as e:
            self.status.config(text=f"⚠ {e}")

    # ── CALIBRATION PAGE ──
    def _build_calibration_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages["calibration"] = page
        tk.Label(page, text="Calibration", font=("Arial",15,"bold"),
                 fg=TEXT, bg=BG).pack(anchor="w", padx=20, pady=(12,10))
        panel = tk.Frame(page, bg=BG_PANEL, highlightbackground="#333", highlightthickness=1)
        panel.pack(fill="x", padx=20, pady=5)
        inner = tk.Frame(panel, bg=BG_PANEL); inner.pack(padx=20, pady=20)
        tk.Label(inner, text="Initial Rest Value:", font=("Arial",11), fg=TEXT,
                 bg=BG_PANEL).grid(row=0, column=0, sticky="w", pady=8)
        self.rest_var = tk.IntVar(value=2400)
        tk.Spinbox(inner, from_=0, to=4095, textvariable=self.rest_var, width=10,
                   font=("Arial",11), bg="#333", fg=TEXT, buttonbackground="#444",
                   insertbackground=TEXT).grid(row=0, column=1, padx=15)
        tk.Label(inner, text="Bottom-Out Threshold:", font=("Arial",11), fg=TEXT,
                 bg=BG_PANEL).grid(row=1, column=0, sticky="w", pady=8)
        self.bottom_var = tk.IntVar(value=650)
        tk.Spinbox(inner, from_=0, to=4095, textvariable=self.bottom_var, width=10,
                   font=("Arial",11), bg="#333", fg=TEXT, buttonbackground="#444",
                   insertbackground=TEXT).grid(row=1, column=1, padx=15)
        ab = tk.Label(inner, text="  Apply  ", font=("Arial",10,"bold"), fg="#fff",
                      bg=ACCENT, cursor="hand2", padx=12, pady=4)
        ab.grid(row=2, column=0, columnspan=2, pady=(15,0))
        ab.bind("<Button-1>", lambda e: self._apply_cal())

    def _apply_cal(self):
        if not self.data:
            messagebox.showwarning("Warning","No file loaded"); return
        self.data.setdefault("calibration",{})
        self.data["calibration"]["initial_rest_value"] = self.rest_var.get()
        self.data["calibration"]["initial_bottom_out_threshold"] = self.bottom_var.get()
        self.status.config(text="Calibration updated")

    # ── INFO PAGE ──
    def _build_info_page(self):
        page = tk.Frame(self.content, bg=BG); self.pages["info"] = page
        tk.Label(page, text="Device Info", font=("Arial",15,"bold"),
                 fg=TEXT, bg=BG).pack(anchor="w", padx=20, pady=(12,10))
        self.info_panel = tk.Frame(page, bg=BG_PANEL, highlightbackground="#333", highlightthickness=1)
        self.info_panel.pack(fill="x", padx=20, pady=5)

    def _draw_info(self):
        for w in self.info_panel.winfo_children(): w.destroy()
        if not self.data: return
        inner = tk.Frame(self.info_panel, bg=BG_PANEL)
        inner.pack(padx=20, pady=20, anchor="w")
        for i,(k,v) in enumerate([
            ("Name",self.data.get("name","")),("Manufacturer",self.data.get("manufacturer","")),
            ("Maintainer",self.data.get("maintainer","")),
            ("USB VID",self.data.get("usb",{}).get("vid","")),
            ("USB PID",self.data.get("usb",{}).get("pid","")),
            ("Keys",self.data.get("keyboard",{}).get("num_keys","")),
            ("Profiles",self.data.get("keyboard",{}).get("num_profiles","")),
            ("Layers",self.data.get("keyboard",{}).get("num_layers","")),
            ("Driver",self.data.get("hardware",{}).get("driver","")),
            ("Configurator",f"v{VERSION}"),
        ]):
            tk.Label(inner, text=k+":", font=("Arial",11,"bold"), fg=ACCENT,
                     bg=BG_PANEL).grid(row=i, column=0, sticky="w", pady=3, padx=(0,15))
            tk.Label(inner, text=str(v), font=("Arial",11), fg=TEXT,
                     bg=BG_PANEL).grid(row=i, column=1, sticky="w", pady=3)

    # ── USB OPS ──
    def _try_usb_connect(self):
        try:
            path = find_hidraw()
            if not path:
                self.status.config(text="⚠ Keyboard not found — plug it in and reopen")
                return False
            self.usb_fd = os.open(path, os.O_RDWR)
            resp = usb_cmd(self.usb_fd, CMD_FW_VERSION)
            if resp[0] != CMD_FW_VERSION:
                self.status.config(text="⚠ Bad response from keyboard")
                return False
            import struct
            ver = struct.unpack_from("<H", resp, 1)[0]
            self.usb_profile = usb_cmd(self.usb_fd, CMD_GET_PROFILE)[1]
            # Read all 4 layers from keyboard
            self.live_keymap = {}
            for layer in range(4):
                keys = usb_get_keymap(self.usb_fd, self.usb_profile, layer, self.num_keys)
                for i, b in enumerate(keys):
                    self.live_keymap[(layer, i)] = b
            self.status.config(text=f"✓ Connected — FW v{ver}, Profile {self.usb_profile}")
            return True
        except Exception as e:
            self.status.config(text=f"⚠ USB: {e}")
            self.usb_fd = None
            return False

    def _usb_send_key(self, layer, key_idx, kc_name):
        """Send a single key change to the keyboard live."""
        b = kc_to_byte(kc_name)
        if b is None:
            self.status.config(text=f"⚠ Unknown keycode: {kc_name}")
            return False
        if self.usb_fd is None:
            if not self._try_usb_connect():
                return False
        try:
            usb_set_keymap(self.usb_fd, self.usb_profile, layer, key_idx, [b])
            self.live_keymap[(layer, key_idx)] = b
            return True
        except Exception as e:
            self.status.config(text=f"⚠ USB write failed: {e}")
            self.usb_fd = None
            return False

    def _get_live_kc(self, layer, key_idx):
        """Get keycode name from live keymap."""
        b = self.live_keymap.get((layer, key_idx))
        if b is not None:
            return byte_to_kc(b)
        return None

    # ── FILE OPS ──
    def _load_file(self, path):
        try:
            with open(path,"r") as f: self.data = json.load(f)
            self.filepath = path
            cal = self.data.get("calibration",{})
            self.rest_var.set(cal.get("initial_rest_value",2400))
            self.bottom_var.set(cal.get("initial_bottom_out_threshold",650))
            # Parse layout from JSON
            layout = self.data.get("layout",{}).get("keymap",[])
            km0 = self.data.get("keymap",[[]])[0] if self.data.get("keymap") else []
            if layout:
                self._layout_rows, self._layout_option_ids = _parse_layout_rows(layout, km0)
            self.num_keys = self.data.get("keyboard",{}).get("num_keys", 67)
            self._set_layer(0); self._draw_info()
            self.status.config(text=f"Loaded: {path}")
        except Exception as e: messagebox.showerror("Error",str(e))

    def _open(self):
        path = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if path: self._load_file(path)

    def _save(self):
        if not self.filepath or not self.data: return self._save_as()
        try:
            with open(self.filepath,"w") as f: json.dump(self.data,f,indent=2); f.write("\n")
            self.status.config(text=f"Saved: {self.filepath}")
        except Exception as e: messagebox.showerror("Error",str(e))

    def _save_as(self):
        if not self.data: return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if path: self.filepath = path; self._save()


if __name__ == "__main__":
    App().mainloop()
# build 1775076785

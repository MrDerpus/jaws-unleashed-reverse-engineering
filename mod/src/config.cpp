/*
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Jaws Unleashed reverse engineering tools
 * Copyright (C) 2026 MrDerpus and contributors
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include "config.h"
#include "modpath.h"
#include "farview.h"
#include "ecco.h"

#include <windows.h>
#include <stdio.h>
#include <string.h>

/* Both live next to Jaws.exe. */
static char CONFIG_FILE[MAX_PATH]  = "";
static char CURRENT_FILE[MAX_PATH] = "";

static const DWORD SAVE_SIZE      = 0x1DB4;
static const DWORD PROFILE        = 0x8D0110;
static const DWORD PROF_BINDINGS  = 0x5C;        /* 3 x 19 dwords */
static const int   N_ACTIONS      = 19;
static const DWORD ARR_KEYBOARD   = 0x8A0094;
static const DWORD ARR_SECOND     = 0x8A0208;
static const DWORD ARR_PAD        = 0x8A0300;
static const DWORD ARR_LEN        = 31;
static const DWORD KEYBOARD_DEV   = 0x8D6818;    /* set by input init 0x483CE0 */
static const DWORD INPUT_OBJ      = 0x8D67F8;
static const DWORD FN_REBIND      = 0x483F30;

typedef void (__attribute__((thiscall)) *RebindFn)(void* self);

static void log_line(const char* fmt, const char* a = "", const char* b = "")
{
    if (FILE* f = fopen(MOD_PATH("jaws_mod.log"), "a")) {
        fprintf(f, "[jaws_mod] config: ");
        fprintf(f, fmt, a, b);
        fprintf(f, "\n");
        fclose(f);
    }
}

static bool rd(DWORD addr, void* out, SIZE_T n)
{
    return ReadProcessMemory(GetCurrentProcess(), (LPCVOID)addr, out, n, nullptr) != 0;
}

/* ── names ───────────────────────────────────────────────────────────── */
/* The 19 rebindable actions, in the profile's order (table 0x7E07E0); names
 * from the game's controls menu (0x54E6E0). */
static const struct { DWORD id; const char* name; } ACTIONS[N_ACTIONS] = {
    {0x02, "swim"},           {0x05, "turn_up"},        {0x06, "turn_down"},
    {0x07, "turn_left"},      {0x08, "turn_right"},     {0x0A, "charge_attack"},
    {0x0C, "bite"},           {0x00, "shark_vision"},   {0x0B, "stealth_attack"},
    {0x09, "tail_whip"},      {0x03, "target_lock"},    {0x18, "next_target"},
    {0x19, "previous_target"},{0x16, "next_body_part"}, {0x17, "previous_body_part"},
    {0x04, "map"},            {0x1B, "pause"},          {0x01, "dodge"},
    {0x0D, "camera_mode"},
};

struct CodeName { DWORD code; const char* name; };

/* DirectInput scan codes (keyboard slot, stored & 0xFF, 0xFF = none). */
static const CodeName KEYS[] = {
    {0x01,"escape"},{0x02,"1"},{0x03,"2"},{0x04,"3"},{0x05,"4"},{0x06,"5"},{0x07,"6"},
    {0x08,"7"},{0x09,"8"},{0x0A,"9"},{0x0B,"0"},{0x0C,"minus"},{0x0D,"equals"},
    {0x0E,"backspace"},{0x0F,"tab"},{0x10,"q"},{0x11,"w"},{0x12,"e"},{0x13,"r"},
    {0x14,"t"},{0x15,"y"},{0x16,"u"},{0x17,"i"},{0x18,"o"},{0x19,"p"},
    {0x1A,"lbracket"},{0x1B,"rbracket"},{0x1C,"enter"},{0x1D,"lctrl"},{0x1E,"a"},
    {0x1F,"s"},{0x20,"d"},{0x21,"f"},{0x22,"g"},{0x23,"h"},{0x24,"j"},{0x25,"k"},
    {0x26,"l"},{0x27,"semicolon"},{0x28,"apostrophe"},{0x29,"grave"},{0x2A,"lshift"},
    {0x2B,"backslash"},{0x2C,"z"},{0x2D,"x"},{0x2E,"c"},{0x2F,"v"},{0x30,"b"},
    {0x31,"n"},{0x32,"m"},{0x33,"comma"},{0x34,"period"},{0x35,"slash"},
    {0x36,"rshift"},{0x37,"numpad_star"},{0x38,"lalt"},{0x39,"space"},
    {0x3A,"capslock"},{0x3B,"f1"},{0x3C,"f2"},{0x3D,"f3"},{0x3E,"f4"},{0x3F,"f5"},
    {0x40,"f6"},{0x41,"f7"},{0x42,"f8"},{0x43,"f9"},{0x44,"f10"},{0x45,"numlock"},
    {0x46,"scrolllock"},{0x47,"numpad7"},{0x48,"numpad8"},{0x49,"numpad9"},
    {0x4A,"numpad_minus"},{0x4B,"numpad4"},{0x4C,"numpad5"},{0x4D,"numpad6"},
    {0x4E,"numpad_plus"},{0x4F,"numpad1"},{0x50,"numpad2"},{0x51,"numpad3"},
    {0x52,"numpad0"},{0x53,"numpad_period"},{0x57,"f11"},{0x58,"f12"},
    {0x9C,"numpad_enter"},{0x9D,"rctrl"},{0xB5,"numpad_slash"},{0xB8,"ralt"},
    {0xC5,"pause"},{0xC7,"home"},{0xC8,"up"},{0xC9,"pageup"},{0xCB,"left"},
    {0xCD,"right"},{0xCF,"end"},{0xD0,"down"},{0xD1,"pagedown"},{0xD2,"insert"},
    {0xD3,"delete"},{0xFF,"none"},
};
/* Second slot (stored & 0x1FF, 0x1FF = none); meanings from the controls
 * menu text (0x539120). Wheel direction of 0x10B/0x10C not verified. */
static const CodeName MOUSE[] = {
    {0x103,"left"},{0x104,"right"},{0x105,"middle"},{0x106,"button4"},
    {0x107,"button5"},{0x108,"button6"},{0x109,"button7"},{0x10A,"button8"},
    {0x10B,"wheel_up"},{0x10C,"wheel_down"},{0x1FF,"none"},
};
/* Gamepad (0xFF = none): 5 + N = "BUTTON N" in the menu, 0x17..0x1A = d-pad. */
static const CodeName PAD[] = {
    {0x05,"button0"},{0x06,"button1"},{0x07,"button2"},{0x08,"button3"},
    {0x09,"button4"},{0x0A,"button5"},{0x0B,"button6"},{0x0C,"button7"},
    {0x0D,"button8"},{0x0E,"button9"},{0x0F,"button10"},{0x10,"button11"},
    {0x11,"button12"},{0x12,"button13"},{0x13,"button14"},{0x14,"button15"},
    {0x15,"button16"},{0x16,"button17"},{0x17,"dpad_up"},{0x18,"dpad_right"},
    {0x19,"dpad_down"},{0x1A,"dpad_left"},{0xFF,"none"},{0xFFFF,"none"},
};
#define COUNT(a) (int)(sizeof(a) / sizeof((a)[0]))
static const struct { const char* word; const CodeName* names; int n; DWORD mask; } SLOTS[3] = {
    {"key",   KEYS,  COUNT(KEYS),  0xFF},
    {"mouse", MOUSE, COUNT(MOUSE), 0x1FF},
    {"pad",   PAD,   COUNT(PAD),   0xFFFF},
};

static int find_action(const char* name)
{
    char n[64]; int j = 0;
    for (const char* c = name; *c && j < 63; ++c) n[j++] = (*c == '-' || *c == ' ') ? '_' : *c;
    n[j] = 0;
    for (int i = 0; i < N_ACTIONS; ++i)
        if (!_stricmp(n, ACTIONS[i].name)) return i;
    return -1;
}

static bool parse_code(int slot, const char* v, DWORD* out)
{
    for (int i = 0; i < SLOTS[slot].n; ++i)
        if (!_stricmp(v, SLOTS[slot].names[i].name)) { *out = SLOTS[slot].names[i].code; return true; }
    if (v[0] == '0' && (v[1] == 'x' || v[1] == 'X')) {
        char* end; unsigned long c = strtoul(v, &end, 16);
        if (!*end && c <= SLOTS[slot].mask) { *out = c; return true; }
    }
    return false;
}

static const char* code_name(int slot, DWORD code, char* buf)
{
    for (int i = 0; i < SLOTS[slot].n; ++i)
        if (SLOTS[slot].names[i].code == code) return SLOTS[slot].names[i].name;
    sprintf(buf, "0x%X", (unsigned)code);
    return buf;
}

/* ── start states of the hotkey features ──────────────────────────────── */
extern bool g_fog_off, g_hide_foliage, g_invincible, g_noclip;   /* device_proxy.cpp */

static void set_bool(bool* b, bool on) { *b = on; }
static void set_farview(bool on) { SetFarView(on); }
static void set_ecco(bool on)
{
    if (on != EccoEnabled() && (!on || InstallEccoHook()))
        ToggleEcco();
}

static struct StartOpt {
    const char* key;
    bool*       flag;              /* plain flag, or ... */
    void      (*set)(bool);        /* ... a setter */
    int         cfg;               /* last value read: -1 = not in the file */
} START_OPTS[] = {
    {"farview",      nullptr,         set_farview, -1},   /* Shift+F4 */
    {"fog_off",      &g_fog_off,      nullptr,     -1},   /* F4 */
    {"foliage_hide", &g_hide_foliage, nullptr,     -1},   /* F6 */
    {"noclip",       &g_noclip,       nullptr,     -1},   /* F7 */
    {"invincible",   &g_invincible,   nullptr,     -1},   /* F11 */
    {"ecco_mode",    nullptr,         set_ecco,    -1},   /* Shift+F2 */
};

/* ── settings ─────────────────────────────────────────────────────────── */
struct Bind { int slot, action; DWORD code; };

static char     g_controls_from[MAX_PATH] = "";
static bool     g_apply_all = false;
static FILETIME g_cfg_time  = {0, 0};
static bool     g_cfg_seen  = false;
static Bind     g_binds[3 * N_ACTIONS];
static int      g_nbinds    = 0;

static bool     g_have_save = false;
static DWORD    g_save_layout[3 * N_ACTIONS];   /* from controls_from */
static bool     g_have_defaults = false;
static DWORD    g_defaults[3 * N_ACTIONS];      /* live arrays at startup */
static bool     g_want = false;                 /* a layout is configured */
static DWORD    g_layout[3 * N_ACTIONS];        /* wanted, profile format */
static bool     g_applied = false;
static DWORD    g_applied_layout[3 * N_ACTIONS];
static DWORD    g_last_profile[3 * N_ACTIONS];

static bool on_off(const char* v)
{
    return !_stricmp(v, "on") || !_stricmp(v, "1") || !_stricmp(v, "yes") || !_stricmp(v, "true");
}

static void resolve_path(const char* name, char* out, size_t n)
{
    if (strchr(name, ':') || name[0] == '\\' || name[0] == '/') {
        snprintf(out, n, "%s", name);
        return;
    }
    char exe[MAX_PATH] = "";
    GetModuleFileNameA(nullptr, exe, sizeof(exe));
    char* slash = strrchr(exe, '\\');
    if (slash) slash[1] = 0; else exe[0] = 0;
    snprintf(out, n, "%s%s", exe, name);
}

/* Reads the 57 binding entries out of a .sav file. */
static bool load_save_layout(const char* name)
{
    char path[MAX_PATH];
    resolve_path(name, path, sizeof(path));
    FILE* f = fopen(path, "rb");
    if (!f) { log_line("cannot open controls_from %s", path); return false; }
    static unsigned char buf[SAVE_SIZE + 1];
    size_t got = fread(buf, 1, sizeof(buf), f);
    fclose(f);
    if (got != SAVE_SIZE) { log_line("%s is not a 7604-byte save", path); return false; }
    memcpy(g_save_layout, buf + PROF_BINDINGS, sizeof(g_save_layout));
    for (DWORD e : g_save_layout)
        if ((e >> 16) >= ARR_LEN) { log_line("%s: bad binding table", path); return false; }
    log_line("control layout loaded from %s", path);
    return true;
}

static void pick_paths()
{
    if (CONFIG_FILE[0]) return;
    resolve_path("jaws_config.txt", CONFIG_FILE, sizeof(CONFIG_FILE));
    resolve_path("jaws_controls_current.txt", CURRENT_FILE, sizeof(CURRENT_FILE));
}

static void read_config()
{
    pick_paths();
    WIN32_FILE_ATTRIBUTE_DATA fa;
    if (!GetFileAttributesExA(CONFIG_FILE, GetFileExInfoStandard, &fa)) {
        if (!g_cfg_seen) { g_cfg_seen = true; log_line("no %s, using defaults", CONFIG_FILE); }
        return;
    }
    if (g_cfg_seen && CompareFileTime(&fa.ftLastWriteTime, &g_cfg_time) == 0)
        return;
    g_cfg_seen = true;
    g_cfg_time = fa.ftLastWriteTime;

    char from[MAX_PATH] = "";
    bool all = false;
    int opt[COUNT(START_OPTS)];
    for (int& o : opt) o = -1;
    g_nbinds = 0;
    if (FILE* f = fopen(CONFIG_FILE, "r")) {
        char line[512];
        while (fgets(line, sizeof(line), f)) {
            if (char* hash = strchr(line, '#')) *hash = 0;
            char key[64], val[MAX_PATH];
            if (sscanf(line, "%63s %259[^\r\n]", key, val) != 2) continue;
            for (char* e = val + strlen(val); e > val && (e[-1] == ' ' || e[-1] == '\t'); ) *--e = 0;
            if      (!_stricmp(key, "controls_from"))  snprintf(from, sizeof(from), "%s", val);
            else if (!_stricmp(key, "controls_apply")) all = !_stricmp(val, "all");
            else {
                int k = -1;
                for (int i = 0; i < COUNT(START_OPTS); ++i)
                    if (!_stricmp(key, START_OPTS[i].key)) k = i;
                if (k >= 0) { opt[k] = on_off(val); continue; }
                int slot = -1;
                for (int i = 0; i < 3; ++i) if (!_stricmp(key, SLOTS[i].word)) slot = i;
                if (slot < 0) { log_line("unknown setting '%s'", key); continue; }
                char act[64], code[64];
                DWORD c = 0;
                int a = -1;
                if (sscanf(val, "%63s %63s", act, code) != 2 || (a = find_action(act)) < 0 ||
                    !parse_code(slot, code, &c)) {
                    log_line("bad line '%s %s'", key, val);
                    continue;
                }
                g_binds[g_nbinds++ % (3 * N_ACTIONS)] = {slot, a, c};
            }
        }
        fclose(f);
    }
    if (g_nbinds > 3 * N_ACTIONS) g_nbinds = 3 * N_ACTIONS;
    log_line("read %s", CONFIG_FILE);

    g_apply_all = all;
    if (strcmp(from, g_controls_from) != 0 || !g_have_save) {
        snprintf(g_controls_from, sizeof(g_controls_from), "%s", from);
        g_have_save = from[0] && _stricmp(from, "none") && load_save_layout(from);
    }
    /* A start state is set when the game starts and whenever its line
     * changes; the hotkeys still toggle freely in between. */
    for (int i = 0; i < COUNT(START_OPTS); ++i) {
        StartOpt& o = START_OPTS[i];
        if (opt[i] == o.cfg) continue;
        o.cfg = opt[i];
        if (o.cfg < 0) continue;
        if (o.flag) set_bool(o.flag, o.cfg == 1); else o.set(o.cfg == 1);
        log_line("%s %s", o.key, o.cfg ? "on" : "off");
    }
}

/* ── controls ─────────────────────────────────────────────────────────── */
/* Live arrays -> profile format, as a new game does (0x537090). */
static void read_live(DWORD* out)
{
    const DWORD* arr[3] = {(DWORD*)ARR_KEYBOARD, (DWORD*)ARR_SECOND, (DWORD*)ARR_PAD};
    for (int s = 0; s < 3; ++s)
        for (int i = 0; i < N_ACTIONS; ++i) {
            DWORD id = ACTIONS[i].id;
            out[s * N_ACTIONS + i] = (id << 16) | (arr[s][id] & SLOTS[s].mask);
        }
}

/* controls_from (or the startup defaults) with the key/mouse/pad lines on top. */
static void build_layout()
{
    g_want = g_have_save || g_nbinds > 0;
    if (!g_want) return;
    memcpy(g_layout, g_have_save ? g_save_layout : g_defaults, sizeof(g_layout));
    for (int b = 0; b < g_nbinds; ++b) {
        const Bind& x = g_binds[b];
        g_layout[x.slot * N_ACTIONS + x.action] = (ACTIONS[x.action].id << 16) | x.code;
    }
}

/* Same as the game's save loading (0x539B30), then the game's own rebuild. */
static void apply_layout(bool to_profile)
{
    DWORD* arr[3] = {(DWORD*)ARR_KEYBOARD, (DWORD*)ARR_SECOND, (DWORD*)ARR_PAD};
    for (int s = 0; s < 3; ++s)
        for (int i = 0; i < N_ACTIONS; ++i) {
            DWORD e = g_layout[s * N_ACTIONS + i];
            arr[s][e >> 16] = e & 0xFFFF;
        }
    if (to_profile)
        memcpy((void*)(PROFILE + PROF_BINDINGS), g_layout, sizeof(g_layout));
    ((RebindFn)FN_REBIND)((void*)INPUT_OBJ);
    memcpy(g_applied_layout, g_layout, sizeof(g_layout));
    g_applied = true;
}

/* Keeps jaws_controls_current.txt in step with the live layout. */
static void write_current()
{
    static DWORD last[3 * N_ACTIONS];
    static bool written = false;
    DWORD live[3 * N_ACTIONS];
    read_live(live);
    if (written && !memcmp(live, last, sizeof(live)))
        return;
    FILE* f = fopen(CURRENT_FILE, "w");
    if (!f) return;
    fprintf(f, "# Live control layout, written by the mod whenever it changes.\n"
               "# Copy lines into jaws_config.txt (next to Jaws.exe) to set them there.\n");
    char buf[16];
    for (int s = 0; s < 3; ++s) {
        fprintf(f, "\n");
        for (int i = 0; i < N_ACTIONS; ++i)
            fprintf(f, "%-6s%-20s%s\n", SLOTS[s].word, ACTIONS[i].name,
                    code_name(s, live[s * N_ACTIONS + i] & 0xFFFF, buf));
    }
    fclose(f);
    memcpy(last, live, sizeof(live));
    written = true;
}

static void update_controls(bool cfg_changed)
{
    DWORD dev = 0;
    if (!rd(KEYBOARD_DEV, &dev, 4) || !dev)       /* input not set up yet */
        return;
    if (!g_have_defaults) {
        read_live(g_defaults);
        g_have_defaults = true;
        cfg_changed = true;
    }
    if (cfg_changed)
        build_layout();

    DWORD prof[3 * N_ACTIONS];
    if (!rd(PROFILE + PROF_BINDINGS, prof, sizeof(prof)))
        return;
    bool profile_loaded = prof[0] != 0;           /* empty profile = all zero */

    if (g_want && (!g_applied || memcmp(g_layout, g_applied_layout, sizeof(g_layout)))) {
        /* startup, or the config changed: set it live (and in the profile
         * when one is loaded, so saving keeps it) */
        apply_layout(profile_loaded);
        log_line("control layout applied");
        rd(PROFILE + PROF_BINDINGS, prof, sizeof(prof));
    } else if (memcmp(prof, g_last_profile, sizeof(prof)) != 0) {
        /* the profile's table changed: a save was loaded or a new game made */
        if (g_want && g_apply_all && profile_loaded && memcmp(prof, g_layout, sizeof(prof))) {
            apply_layout(true);
            log_line("loaded save's controls replaced by the layout");
            rd(PROFILE + PROF_BINDINGS, prof, sizeof(prof));
        }
    }
    memcpy(g_last_profile, prof, sizeof(prof));
    write_current();
}

void UpdateModConfig()
{
    static DWORD last_check = 0;
    static FILETIME seen = {0, 0};
    DWORD now = GetTickCount();
    if (g_cfg_seen && now - last_check < 1000)
        return;
    last_check = now;
    read_config();
    bool changed = CompareFileTime(&seen, &g_cfg_time) != 0;
    seen = g_cfg_time;
    update_controls(changed);
}

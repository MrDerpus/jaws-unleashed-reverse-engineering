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

#include "iddump.h"

#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <vector>

static const DWORD ENGINE_GLOBAL  = 0x920E24;
static const DWORD ENGINE_ID_MAP  = 0x50;
static const DWORD ENGINE_COUNTER = 0x14;     /* runtime ID counter */
static const char* IDS_FILE  = "C:\\jaws_ids.txt";
static const char* DUMP_FILE = "C:\\jaws_iddump.txt";

/* Trigger test (TEST.GDW, 2026-10-03) plus vanilla FISH references. */
static const DWORD DEFAULT_IDS[] = {
    0xF000, 0xF001, 0xF002, 0xF008, 0xF009, 0xF00A, 0xFF00,
    130, 131, 26414, 26417,
};

static bool rd(DWORD addr, void* out, SIZE_T n)
{
    return addr && ReadProcessMemory(GetCurrentProcess(), (LPCVOID)addr, out, n, nullptr) != 0;
}

static std::vector<DWORD> load_ids()
{
    std::vector<DWORD> ids;
    if (FILE* f = fopen(IDS_FILE, "r")) {
        char line[64];
        while (fgets(line, sizeof(line), f)) {
            char* end = nullptr;
            unsigned long v = strtoul(line, &end, 0);
            if (end != line && v)
                ids.push_back((DWORD)v);
        }
        fclose(f);
    }
    if (ids.empty())
        ids.assign(DEFAULT_IDS, DEFAULT_IDS + sizeof(DEFAULT_IDS) / sizeof(DEFAULT_IDS[0]));
    return ids;
}

static void dump_object(FILE* out, DWORD obj)
{
    DWORD w[64] = {};
    if (!rd(obj, w, sizeof(w))) {
        fprintf(out, "    object %08lX unreadable\n", (unsigned long)obj);
        return;
    }
    for (int i = 0; i < 64; i += 8) {
        fprintf(out, "    +%03X:", i * 4);
        for (int k = 0; k < 8; ++k)
            fprintf(out, " %08lX", (unsigned long)w[i + k]);
        fprintf(out, "\n");
    }
}


/* ANPosition (boat marker) -> its spawned copy -> live brick -> ANShip AI, the
 * chain StagePursuitQuest2 follows (docs/exe_analysis.md "Running it in-game"):
 * marker vtable 0x7D0AEC, copy ID at +0xF4, live brick at registered +0x24, AI at
 * brick +0x20. ANShip fields from its activation FUN_00410DA0: +0xC24 state-stack
 * depth, +0xC28 + 8k (state, sub), +0xE20 path ID, +0x2A4 path object, +0xA78 "no
 * path" byte, +0xD8C flag (state 2/7 path), +0xA84 "skip" byte, +0x318 waypoint
 * group mask. */
static const DWORD VT_ANPOSITION = 0x7D0AEC;

/* What a vtable slot's function returns, if it is one of the tiny shared stubs:
 * 1 for "mov eax,1; ret" (0x401630), 0 for "xor eax,eax; ret", -1 otherwise. */
static int stub_value(DWORD fn)
{
    BYTE b[6] = {};
    if (!rd(fn, b, sizeof(b))) return -1;
    if (b[0] == 0xB8 && b[1] == 1 && !b[2] && !b[3] && !b[4] && b[5] == 0xC3) return 1;
    if (b[0] == 0x33 && b[1] == 0xC0 && b[2] == 0xC3) return 0;
    return -1;
}

/* Emulates 0x6C2FD0 on a registered object: if vtable+4 says "definition", the
 * live object is vtable+0x20's result (0x401640 = [obj+0x24]); otherwise the
 * registered object is the live one. */
static DWORD live_of(FILE* out, DWORD obj)
{
    DWORD vt = 0, f4 = 0, f20 = 0, live = 0;
    rd(obj, &vt, 4); rd(vt + 4, &f4, 4); rd(vt + 0x20, &f20, 4);
    int is_def = stub_value(f4);
    if (is_def == 0) return obj;
    if (is_def == 1 && f20 == 0x401640) { rd(obj + 0x24, &live, 4); return live; }
    fprintf(out, "   (vtable %08lX: +4 = %08lX, +0x20 = %08lX not understood)\n",
            (unsigned long)vt, (unsigned long)f4, (unsigned long)f20);
    return 0;
}

static void dump_boat(FILE* out, DWORD copy_obj)
{
    DWORD brick = 0, ai = 0, aivt = 0, cvt = 0;
    float pos[3] = {};
    rd(copy_obj, &cvt, 4);
    fprintf(out, "   copy object %08lX vtable %08lX:\n", (unsigned long)copy_obj, (unsigned long)cvt);
    dump_object(out, copy_obj);
    brick = live_of(out, copy_obj);
    if (brick) rd(brick + 0xA8, pos, sizeof(pos));
    if (brick) rd(brick + 0x20, &ai, 4);
    fprintf(out, "   boat: copy object %08lX brick %08lX pos (%.1f, %.1f, %.1f) ai %08lX",
            (unsigned long)copy_obj, (unsigned long)brick, pos[0], pos[1], pos[2], (unsigned long)ai);
    if (!ai || !rd(ai, &aivt, 4)) { fprintf(out, "\n"); return; }
    DWORD depth = 0, path_id = 0, path = 0, flag_d8c = 0, mask = 0, aiflags = 0;
    BYTE nopath = 0, skip = 0;
    rd(ai + 0x0C, &aiflags, 4); rd(ai + 0xC24, &depth, 4); rd(ai + 0xE20, &path_id, 4);
    rd(ai + 0x2A4, &path, 4); rd(ai + 0xA78, &nopath, 1); rd(ai + 0xD8C, &flag_d8c, 4);
    rd(ai + 0xA84, &skip, 1); rd(ai + 0x318, &mask, 4);
    fprintf(out, " vtable %08lX flags %08lX\n    path id %lu path obj %08lX no-path %u +D8C %08lX skip %u group mask %08lX\n    states:",
            (unsigned long)aivt, (unsigned long)aiflags, (unsigned long)path_id, (unsigned long)path,
            nopath, (unsigned long)flag_d8c, skip, (unsigned long)mask);
    for (DWORD k = 0; k <= depth && k < 32; ++k) {
        DWORD st[2] = {};
        rd(ai + 0xC28 + 8 * k, st, sizeof(st));
        fprintf(out, " [%lu/%lu]", (unsigned long)st[0], (unsigned long)st[1]);
    }
    fprintf(out, "  (depth %lu)\n", (unsigned long)depth);
}

bool DumpIdRegistry(char* msg, size_t msg_sz)
{
    DWORD engine = 0, nbuckets = 0, buckets = 0, counter = 0;
    if (!rd(ENGINE_GLOBAL, &engine, 4) || !engine) {
        snprintf(msg, msg_sz, "ID dump: no engine yet");
        return false;
    }
    DWORD map = engine + ENGINE_ID_MAP;
    if (!rd(map + 4, &nbuckets, 4) || !rd(map + 8, &buckets, 4) || !nbuckets || nbuckets > 0x400000) {
        snprintf(msg, msg_sz, "ID dump: registry unreadable");
        return false;
    }
    rd(engine + ENGINE_COUNTER, &counter, 4);
    std::vector<DWORD> table(nbuckets);
    if (!rd(buckets, table.data(), nbuckets * 4)) {
        snprintf(msg, msg_sz, "ID dump: bucket array unreadable");
        return false;
    }

    /* every entry: (key, entry address, object) */
    struct Entry { DWORD key, addr, obj; };
    std::vector<Entry> all;
    for (DWORD b = 0; b < nbuckets; ++b)
        for (DWORD e = table[b], guard = 0; e && guard < 100000; ++guard) {
            DWORD ent[4];
            if (!rd(e, ent, sizeof(ent)))
                break;
            all.push_back({ent[0], e, ent[2]});
            e = ent[3];
        }

    FILE* out = fopen(DUMP_FILE, "a");
    if (!out) {
        snprintf(msg, msg_sz, "ID dump: cannot write %s", DUMP_FILE);
        return false;
    }
    SYSTEMTIME st;
    GetLocalTime(&st);
    fprintf(out, "==== ID registry dump %02d:%02d:%02d  engine %08lX  buckets %lu  entries %u  runtime counter %lu (0x%lX)\n",
            st.wHour, st.wMinute, st.wSecond, (unsigned long)engine, (unsigned long)nbuckets,
            (unsigned)all.size(), (unsigned long)counter, (unsigned long)counter);

    std::vector<DWORD> ids = load_ids();
    int found = 0;
    for (DWORD id : ids) {
        bool any = false;
        for (const Entry& en : all) {
            DWORD own_id = 0, vt = 0;
            rd(en.obj + 4, &own_id, 4);
            if (en.key != id && own_id != id)
                continue;
            rd(en.obj, &vt, 4);
            fprintf(out, "  id %lu (0x%lX): entry %08lX key 0x%lX object %08lX vtable %08lX own-id 0x%lX%s\n",
                    (unsigned long)id, (unsigned long)id, (unsigned long)en.addr, (unsigned long)en.key,
                    (unsigned long)en.obj, (unsigned long)vt, (unsigned long)own_id,
                    en.key == id ? "" : "  (registered under another key)");
            dump_object(out, en.obj);
            /* +0x20 / +0x24 hold the live runtime instance of an action
             * (seen: GDControl +0x20, MBRombolhato +0x24); dump those too. */
            for (DWORD off : {0x20u, 0x24u}) {
                DWORD p = 0, pvt = 0;
                if (rd(en.obj + off, &p, 4) && p > 0x10000 && rd(p, &pvt, 4) && pvt >= 0x7CE000 && pvt < 0x845000) {
                    fprintf(out, "   -> +%02lX points at %08lX (vtable %08lX):\n", (unsigned long)off, (unsigned long)p, (unsigned long)pvt);
                    dump_object(out, p);
                }
            }
            if (vt == VT_ANPOSITION) {
                DWORD copy_id = 0;
                rd(en.obj + 0xF4, &copy_id, 4);
                bool hit = false;
                for (const Entry& c : all)
                    if (c.key == copy_id) { dump_boat(out, c.obj); hit = true; break; }
                if (!hit)
                    fprintf(out, "   boat: copy id 0x%lX not in registry\n", (unsigned long)copy_id);
            }
            any = true;
        }
        if (any)
            ++found;
        else
            fprintf(out, "  id %lu (0x%lX): NOT in registry\n", (unsigned long)id, (unsigned long)id);
    }
    fprintf(out, "\n");
    fclose(out);
    snprintf(msg, msg_sz, "ID dump: %d/%u IDs found, written to %s", found, (unsigned)ids.size(), DUMP_FILE);
    return true;
}

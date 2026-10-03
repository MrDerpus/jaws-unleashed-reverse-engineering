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

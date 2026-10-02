#include "bookmarks.h"
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

static const char* BOOKMARK_FILE = "C:\\jaws_bookmarks.txt";

struct Slot { bool used; float x, y, z; char label[BOOKMARK_LABEL_MAX]; };

static Slot     g_slots[BOOKMARK_SLOTS + 1];   /* index 0 unused */
static FILETIME g_loaded_mtime = {};
static bool     g_loaded = false;

static bool FileMTime(FILETIME& out)
{
    WIN32_FILE_ATTRIBUTE_DATA a;
    if (!GetFileAttributesExA(BOOKMARK_FILE, GetFileExInfoStandard, &a)) return false;
    out = a.ftLastWriteTime;
    return true;
}

/* Line format: "<slot> <x> <y> <z> [label...]"; '#' starts a comment line,
 * blank and malformed lines are skipped. */
static void Load()
{
    memset(g_slots, 0, sizeof(g_slots));
    FILE* f = fopen(BOOKMARK_FILE, "r");
    if (!f) return;
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        char* p = line;
        while (*p == ' ' || *p == '\t') ++p;
        if (*p == '#' || *p == '\n' || *p == '\r' || !*p) continue;
        int s, used = 0;
        float x, y, z;
        if (sscanf(p, "%d %f %f %f%n", &s, &x, &y, &z, &used) != 4) continue;
        if (s < 1 || s > BOOKMARK_SLOTS) continue;
        Slot& slot = g_slots[s];
        slot.used = true; slot.x = x; slot.y = y; slot.z = z;
        const char* lab = p + used;
        while (*lab == ' ' || *lab == '\t') ++lab;
        snprintf(slot.label, sizeof(slot.label), "%s", lab);
        slot.label[strcspn(slot.label, "\r\n")] = 0;
    }
    fclose(f);
}

static void Save()
{
    FILE* f = fopen(BOOKMARK_FILE, "w");
    if (!f) return;
    fprintf(f, "# Jaws Unleashed mod teleport bookmarks.\n"
               "# Format: <slot 1-9> <X> <Y> <Z> [optional name]\n"
               "# Edit freely, even while the game is running -- reloaded each time F8 opens.\n"
               "# Coordinates are per level: the same slot means a different place in each GDW.\n");
    for (int i = 1; i <= BOOKMARK_SLOTS; ++i) {
        const Slot& s = g_slots[i];
        if (!s.used) continue;
        fprintf(f, "%d %.2f %.2f %.2f%s%s\n", i, s.x, s.y, s.z, s.label[0] ? " " : "", s.label);
    }
    fclose(f);
    FileMTime(g_loaded_mtime);   /* our own write shouldn't trigger a reload */
}

void BookmarkReloadIfChanged()
{
    FILETIME mt = {};
    bool exists = FileMTime(mt);
    if (g_loaded && exists && CompareFileTime(&mt, &g_loaded_mtime) == 0) return;
    if (g_loaded && !exists) return;   /* file deleted: keep what's in memory */
    Load();
    g_loaded_mtime = mt;
    g_loaded = true;
}

bool BookmarkGet(int slot, float& x, float& y, float& z, const char** label)
{
    BookmarkReloadIfChanged();
    if (slot < 1 || slot > BOOKMARK_SLOTS) return false;
    const Slot& s = g_slots[slot];
    if (!s.used) return false;
    x = s.x; y = s.y; z = s.z;
    if (label) *label = s.label;
    return true;
}

void BookmarkSet(int slot, float x, float y, float z)
{
    BookmarkReloadIfChanged();   /* don't clobber edits made since last load */
    if (slot < 1 || slot > BOOKMARK_SLOTS) return;
    Slot& s = g_slots[slot];
    s.used = true; s.x = x; s.y = y; s.z = z;
    s.label[0] = 0;              /* new position, old name no longer applies */
    Save();
}

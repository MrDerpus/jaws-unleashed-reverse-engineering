#pragma once
/*
 * Teleport bookmarks: 9 slots of world coordinates, persisted to
 * C:\jaws_bookmarks.txt, one "<slot> <x> <y> <z> [name]" line per saved
 * slot; '#' lines are comments. The file is meant to be hand-edited and is
 * re-read whenever its modification time changes.
 *
 * Storage is process-wide, not per-DeviceProxy: the game recreates its D3D
 * device hundreds of times per session (see README "Screenshots"), and any
 * per-instance state resets each time.
 *
 * Bookmarks are plain world coordinates with no level attached -- the same
 * slot means a different place in a different GDW.
 */
static const int BOOKMARK_SLOTS     = 9;
static const int BOOKMARK_LABEL_MAX = 48;

/* Re-reads the file if it changed on disk (cheap: one stat call). */
void BookmarkReloadIfChanged();

/* slot is 1-based (1..9). `label` (optional) receives the slot's name, or "". */
bool BookmarkGet(int slot, float& x, float& y, float& z, const char** label = nullptr);
/* Saves the file. Clears the slot's name, since it's a new position. */
void BookmarkSet(int slot, float x, float y, float z);

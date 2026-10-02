#pragma once
/*
 * Lets the mod swallow keyboard input from the game while the teleport text
 * box is open, so typed digits/spaces don't trigger shark actions.
 *
 * The game reads the keyboard through DirectInput 8. All devices of a class
 * share one COM vtable, so we create a throwaway keyboard device of our own,
 * patch GetDeviceState / GetDeviceData in its vtable, and release it -- the
 * patch then applies to the game's devices too, regardless of whether they
 * were created before or after us.
 */

/* Idempotent; call once dinput8.dll is loaded (any time after startup --
 * it's a static import of Jaws.exe). */
void InstallInputBlock();

/* While true, the game sees no keys pressed and no buffered input events. */
extern bool g_block_game_input;

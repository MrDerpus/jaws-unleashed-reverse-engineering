# SPDX-License-Identifier: GPL-3.0-or-later
#
# Jaws Unleashed reverse engineering tools
# Copyright (C) 2026 MrDerpus and contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

CXX      := i686-w64-mingw32-g++
CXXFLAGS := -std=c++17 -O2 -Wall -Wno-unused-parameter \
            -DWINVER=0x0500 -D_WIN32_WINNT=0x0500
LDFLAGS  := -shared -static-libgcc -static-libstdc++ \
            -Wl,--enable-stdcall-fixup \
            -lgdi32 -luser32 -lkernel32

SRCS := src/d3d8_proxy.cpp \
        src/device_proxy.cpp \
        src/overlay.cpp \
        src/shark.cpp \
        src/input_block.cpp \
        src/bookmarks.cpp \
        src/stage.cpp \
        src/iddump.cpp \
        src/messages.cpp

TARGET := d3d8.dll

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CXX) $(CXXFLAGS) -o $@ $^ src/d3d8.def $(LDFLAGS)

clean:
	rm -f $(TARGET)

.PHONY: all clean

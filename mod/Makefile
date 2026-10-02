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
        src/stage.cpp

TARGET := d3d8.dll

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CXX) $(CXXFLAGS) -o $@ $^ src/d3d8.def $(LDFLAGS)

clean:
	rm -f $(TARGET)

.PHONY: all clean

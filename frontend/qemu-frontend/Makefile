include ../../common/Makefile.common

SIM_ROOT ?= $(shell readlink -f "$(CURDIR)/../../")

QEMU_HOME ?= $(SIM_ROOT)/qemu-9.2.4
QEMU_FRONTEND_CFLAGS=-fPIC -fvisibility=hidden $(shell pkg-config --cflags glib-2.0) -std=c++17 -g -O0
CFLAGS+=$(QEMU_FRONTEND_CFLAGS)
CPPFLAGS+=-I.. -I../../decoder_lib -I$(QEMU_HOME)/include
CXXFLAGS+=$(QEMU_FRONTEND_CFLAGS)
LD_FLAGS+=-shared

default: libqemu-frontend.so

# Override LD_LIBS to exclude torch and other unnecessary libraries
# Note: -lxed is needed because libdecoder.a contains x86 decoder code that references xed symbols
QEMU_FRONTEND_LD_LIBS = -ldecoder -lsift -lxed -lrt -lz

libqemu-frontend.so: bbv_count.o plugin.o qemu_frontend.o
	$(_MSG) '[LD    ]' $(subst $(shell readlink -f $(SIM_ROOT))/,,$(shell readlink -f $@))
	$(_CMD) $(CXX) $(LD_FLAGS) -o $@ $^ -L$(SIM_ROOT)/lib -L$(SIM_ROOT)/decoder_lib -L$(SIM_ROOT)/sift -L$(XED_HOME)/lib $(QEMU_FRONTEND_LD_LIBS) $(OPT_CFLAGS)

bbv_count.o: ../bbv_count.cc
	$(_MSG) '[CXX   ]' $(subst $(shell readlink -f $(SIM_ROOT))/,,$(shell readlink -f $@))
	$(_CMD) $(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

plugin.o: plugin.c qemu_frontend.h
	$(_MSG) '[CC    ]' $(subst $(shell readlink -f $(SIM_ROOT))/,,$(shell readlink -f $@))
	$(_CMD) $(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

qemu_frontend.o: qemu_frontend.cc qemu_frontend.h memory.h
	$(_MSG) '[CXX   ]' $(subst $(shell readlink -f $(SIM_ROOT))/,,$(shell readlink -f $@))
	$(_CMD) $(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

clean:
	-$(RM) libqemu-frontend.so bbv_count.o plugin.o qemu_frontend.o *.d

ifneq ($(CLEAN),clean)
-include bbv_count.d plugin.d qemu_frontend.d
endif


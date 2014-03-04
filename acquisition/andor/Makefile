# Generic GNUMakefile

# Just a snippet to stop executing under other make(1) commands
# that won't understand these lines
ifneq (,)
This makefile requires GNU Make.
endif

PROGRAM = _andor.so
CPP_FILES := $(wildcard *.cpp)
OBJS := $(patsubst %.cpp, %.o, $(CPP_FILES))
CC = g++
CPPFLAGS = -fPIC -std=c++11 -I/usr/include/python3.3 -I/usr/local/include -I/usr/local/include/boost -I/usr/local/pygccxml-svn/pyplusplus_dev/indexing_suite_v2 -Wall -O2 -march=native
LDFLAGS = -fPIC -shared -L/usr/local/lib -lboost_python-3.3-mt -latcore -lpython3.3 -lboost_numpy -lpthread -O2 -march=native

all: _common.h.gch $(PROGRAM)

_common.h.gch : _common.h
	$(CC) $(CPPFLAGS) -c $< -o $@

$(PROGRAM): .depend $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) -Wl,-soname,$(PROGRAM) -o $(PROGRAM)

depend: .depend

.depend: cmd = $(CC) $(CPPFLAGS) -MM -MF depend $(var); cat depend >> .depend;
.depend:
	@echo "Generating dependencies..."
	@$(foreach var, $(CPP_FILES), $(cmd))
	@rm -f depend

-include .depend

# These are the pattern matching rules. In addition to the automatic
# variables used here, the variable $* that matches whatever % stands for
# can be useful in special cases.
%.o: %.cpp
	$(CC) $(CPPFLAGS) -c $< -o $@

#%: %.cpp
#	$(CC) $(CPPFLAGS) -o $@ $<

clean:
	rm -f .depend $(OBJS) $(PROGRAM) _common.h.gch

.PHONY: clean depend

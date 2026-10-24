# OncoPattern — convenience entry points
#
# The real drivers are tools/ocbuild and tools/runtests; this file exists so
# that the commands everyone types first work from a fresh clone.
#
#   $ make test
#
# TECH_ROOT may be set to point at a TECH checkout; tools/ocbuild also looks
# at ../../TECH, ../TECH and ./TECH on its own.

TECH_ROOT ?= ../../TECH
export TECH_ROOT

PYTHON ?= python3
ENTRY  ?= config/boot.tech
NAME   ?= oncopattern

.PHONY: help check test run vm package datasets clean

help:
	@echo "make check     repository hygiene checks (no toolchain needed)"
	@echo "make test      hygiene checks, then every certificate"
	@echo "make run       build and run the whole pipeline"
	@echo "make vm        the same, on the self-hosted vm.tech"
	@echo "make package   dist/oncopattern.bin, self-contained"
	@echo "make datasets  regenerate the synthetic fixtures"
	@echo "make clean     remove results/ and dist/"
	@echo ""
	@echo "TECH_ROOT=$(TECH_ROOT)  (override: make test TECH_ROOT=/path/to/TECH)"

check:
	$(PYTHON) tools/check_repo.py

test: check
	tools/runtests

run:
	tools/ocbuild run $(ENTRY) $(NAME)

vm:
	tools/ocbuild vm $(ENTRY) $(NAME)

package:
	tools/ocbuild package $(ENTRY) $(NAME)

datasets:
	$(PYTHON) tools/gen_datasets.py

clean:
	rm -rf results dist

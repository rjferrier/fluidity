# Python scripts will use Fluidity binaries associated with the present
# directory unless specified otherwise.  When running tests which are
# remote from the branch, the user will need to point FLUIDITYPATH back
# to this branch.
export FLUIDITYPATH ?= $(CURDIR)/../../

# TODO options_iteration is currently assumed to exist in the home
# directory; instead it should be installable and the dependence on
# HOME should be removed.
export PYTHONPATH := $(PYTHONPATH):$(FLUIDITYPATH)/python:$(FLUIDITYPATH)/tools:$(FLUIDITYPATH)/tests/darcy_impes_common:$(HOME)

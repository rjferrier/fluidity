# Python scripts will use Fluidity binaries associated with the present
# directory unless specified otherwise.  When running tests which are
# remote from the branch, the user will need to point FLUIDITYPATH back
# to this branch.
export FLUIDITYPATH ?= $(CURDIR)/../../

export DARCYCOMMONPATH := $(FLUIDITYPATH)/tests/darcy_impes_common

# TODO options_iteration is currently assumed to exist in the home
# directory; instead it should be installable and the dependence on
# HOME should be removed.
export PYTHONPATH := $(PYTHONPATH):$(DARCYCOMMONPATH):$(FLUIDITYPATH)/python:$(FLUIDITYPATH)/tools:$(HOME)


export TEMPLATES = *.xml.template *.geo.template
export MESHPATH = meshes
export SIMPATH = simulations


input: clean

clean:
	rm -f *.txt
	rm -f $(SIMPATH)/*.vtu
	rm -f $(SIMPATH)/*.stat
	rm -f $(SIMPATH)/*.err
	rm -f $(SIMPATH)/matrixdump*
	rm -f $(MESHPATH)/*.msh
	rm -f $(TEMPLATES)
	rm -f *.pyc
	rm -f *~

%.xml.template:
	cp $(FLUIDITYPATH)/tools/data/$@ .

%.geo.template:
	cp $(DARCYCOMMONPATH)/mesh_data/$@ .

# regenerate everything needed by the Fluidity testing framework
regen: pre xml clean

# run the test suite in parallel
all: pre run post

# delegate to the python script 
%: $(TEMPLATES)
	@python script.py $@

# Python scripts will use Fluidity binaries associated with the present
# directory unless specified otherwise
export FLUIDITYPATH ?= $(CURDIR)/../../

export DARCYCOMMONPATH := $(FLUIDITYPATH)/tests/darcy_impes_common
# export PYTHONPATH := $(PYTHONPATH):$(DARCYCOMMONPATH):$(FLUIDITYPATH)/python:$(FLUIDITYPATH)/tools
export PYTHONPATH := $(HOME)/opiter:$(PYTHONPATH):$(DARCYCOMMONPATH):$(FLUIDITYPATH)/python:$(FLUIDITYPATH)/tools

export TEMPLATES = darcy_impes_base.diml.template *.geo.template *.xml.template
export MESHPATH = meshes
export SIMPATH = simulations

.phony: pre run post xml clean

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

%.diml.template:
	cp $(DARCYCOMMONPATH)/$@ .

%.geo.template:
	cp $(DARCYCOMMONPATH)/mesh_data/$@ .

%.xml.template:
	cp $(FLUIDITYPATH)/tools/data/$@ .

# regenerate everything needed by the Fluidity testing framework
regen: pre xml clean

# run the test suite in parallel
all: pre run post

# delegate to the python script 
pre run post xml: $(TEMPLATES)
	python $(PROBLEM).py $@

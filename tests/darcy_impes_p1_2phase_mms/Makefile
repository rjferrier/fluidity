include ../darcy_impes_common/Depend.mk

export TEMPLATES = *.xml.template *.geo.template

input: clean

clean:
	rm -f *.txt
	rm -f simulations/*.vtu
	rm -f simulations/*.stat
	rm -f simulations/*.err
	rm -f simulations/matrixdump*
	rm -f meshes/*.msh
	rm -f $(TEMPLATES)
	rm -f *.pyc
	rm -f *~

%.geo.template:
	cp $(FLUIDITYPATH)/tests/darcy_impes_common/mesh_data/$@ .

%.xml.template:
	cp $(FLUIDITYPATH)/tools/data/$@ .

# regenerate everything needed by the Fluidity testing framework
regen: pre xml clean

# run the test suite in parallel
all: pre mesh run post

# delegate to the python script
%: $(TEMPLATES)
	@python script.py $@

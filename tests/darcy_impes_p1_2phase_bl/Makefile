include ../darcy_impes_common/Depend.mk

export TEMPLATES = xml.template \
	orthotope_1d.geo.template \
	orthotope_2d.geo.template \
	orthotope_3d.geo.template

input: clean

clean:
	rm -f *.txt
	rm -f simulations/*.vtu
	rm -f simulations/*.stat
	rm -f simulations/*.err
	rm -f meshes/*.msh
	rm -f $(TEMPLATES)
	rm -f *.pyc
	rm -f *~

%.geo.template:
	cp $(FLUIDITYPATH)/tests/darcy_impes_common/mesh_data/$@ .

%.template:
	cp $(FLUIDITYPATH)/tests/darcy_impes_common/$@ .

# regenerate everything needed by the Fluidity testing framework
regen: pre xml clean

# run the test suite in parallel
all: pre mesh run post

# delegate to the python script
%: $(TEMPLATES)
	@python script.py $@

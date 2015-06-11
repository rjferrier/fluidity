include ../darcy_impes_common/Depend.mk

.PHONY: scratch

input: 
	cp $(FLUIDITYPATH)/tests/darcy_impes_common/mesh_data/*.template .
	python script.py pre run post

post: 
	python script.py post

xml: 
	python script.py xml

scratch:
	python scratch.py

clean:
	rm -f first_timestep_adapted_mesh*
	rm -f *.geo.template
	rm -f matrixdump*
	rm -f *.err
	rm -f *.log
	python script.py clean

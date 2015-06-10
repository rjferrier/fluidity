include ../darcy_impes_common/Depend.mk

input: 
	cp $(FLUIDITYPATH)/tests/darcy_impes_common/mesh_data/template_*.geo .
	python script.py pre run post

post: 
	python script.py post

xml: 
	python script.py xml

clean:
	rm -f first_timestep_adapted_mesh*
	rm -f template_*.geo
	rm -f matrixdump*
	python script.py clean

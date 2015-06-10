include ../darcy_impes_common/Depend.mk

input: 
	cp $(FLUIDITYPATH)/tests/darcy_impes_common/mesh_data/template_*.geo .
	python script.py pre run post

post: 
	python script.py post

clean:
	# rm -f *.face
	# rm -f *.vtu 
	# rm -f *.pvtu 
	# rm -f *.s 
	# rm -f *.stat 
	# rm -f *.log-0 
	# rm -f *.err-0 
	# rm -f *.msh
	# rm -f *.halo
	# rm -f *.err*
	# rm -f *.log*
	# rm -f matrixdump*
	# rm -f first_timestep_adapted_mesh*
	# rm -f *.convergence 
	# rm -f *.pyc
	# rm -f *.txt
	# rm -f error_*.txt
	rm -f template_*.geo
	python script.py clean

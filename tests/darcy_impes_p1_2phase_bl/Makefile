include ../darcy_impes_common/Depend.mk

.PHONY: input pre run post xml clean

input: pre run post

pre: 
	cp $(FLUIDITYPATH)/tests/darcy_impes_common/mesh_data/*.geo.template .
	python script.py pre 

run: 
	python script.py run

post: 
	python script.py post

xml: 
	cp $(FLUIDITYPATH)/tests/darcy_impes_common/xml.template .
	python script.py xml

clean:
	rm -f *report.txt
	rm -rf results
	rm -rf meshes
	rm -f *geo.template
	rm -f xml.template
	rm -f *.pyc

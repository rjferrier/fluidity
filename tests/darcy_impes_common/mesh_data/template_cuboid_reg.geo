lx = $DOMAIN_LENGTH_X;
ly = $DOMAIN_LENGTH_Y;
lz = $DOMAIN_LENGTH_Z;
nx = $EL_NUM_X;
ny = $EL_NUM_Y;
nz = $EL_NUM_Z;
dx = $EL_SIZE_X;

Point(1) = {0, 0, 0, dx};
Extrude {lx, 0, 0} {
  Point{1}; Layers{nx}; 
}
Extrude {0, 0, lz} {
  Line{1}; Layers{nz}; 
}
Extrude {0, ly, 0} {
  Surface{5}; Layers{ny};
}

Physical Surface(1) = {26};	// xmin
Physical Surface(2) = {18};	// xmax
Physical Surface(3) = {5};	// ymin
Physical Surface(4) = {27};	// ymax
Physical Surface(5) = {22};	// zmax
Physical Surface(6) = {14};	// zmin
Physical Volume(7) = {1};


lx = $DOMAIN_LENGTH_X;
ly = $DOMAIN_LENGTH_Y;
nx = $EL_NUM_X;
ny = $EL_NUM_Y;
dx = $EL_SIZE_X;

Point(1) = {0, 0, 0, dx};
Extrude {lx, 0, 0} {
  Point{1}; Layers{nx}; 
}
Extrude {0, ly, 0} {
  Line{1}; Layers{ny}; 
}

Physical Line(1) = {3}; 	// xmin
Physical Line(2) = {4}; 	// xmax
Physical Line(3) = {1}; 	// ymin
Physical Line(4) = {2}; 	// ymax
Physical Surface(5) = {5};


lx = 1.0;
ly = 1.2;
lz = 0.8;
nx = 10;
ny = 2;			// 0 => use dx
nz = 2;			// 0 => use dx
reg = 1;		// 0 => False, 1 => True

Point(1) = {0, 0, 0, lx/nx};
If ( reg )
  Extrude {lx, 0, 0} { Point{1}; Layers{nx}; }
  
  If ( !nz )
    nz = Ceil(nx*lz/lx);
  EndIf
  Extrude {0, 0, lz} { Line{1}; Layers{nz}; }

  If ( !ny )
    ny = Ceil(nx*ly/lx);
  EndIf
  Extrude {0, ly, 0} { Surface{5}; Layers{ny}; }
EndIf
If ( !reg )
  Extrude {lx, 0, 0} { Point{1}; }
  Extrude {0, 0, lz} { Line{1}; }
  Extrude {0, ly, 0} { Surface{5}; }
EndIf


Physical Surface(1) = {26};	// xmin
Physical Surface(2) = {18};	// xmax
Physical Surface(3) = {5};	// ymin
Physical Surface(4) = {27};	// ymax
Physical Surface(5) = {22};	// zmax
Physical Surface(6) = {14};	// zmin
Physical Volume(7) = {1};


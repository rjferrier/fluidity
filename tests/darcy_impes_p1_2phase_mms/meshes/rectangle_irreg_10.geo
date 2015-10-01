lx = 1.0;
ly = 1.2;
nx = 10;
ny = 12;

Point(1) = {0, 0, 0, lx/nx};

Extrude {lx, 0, 0} { Point{1}; }
Extrude {0, ly, 0} { Line{1}; }

Physical Line(1) = {3}; 	// xmin
Physical Line(2) = {4}; 	// xmax
Physical Line(3) = {1}; 	// ymin
Physical Line(4) = {2}; 	// ymax
Physical Surface(5) = {5};

lx = 1.0;
ly = 1.2;
dx = 0.1;
sqrt2 = 1.4142135623730951;

Point(1) = {  0,  0,  0, dx};
Point(2) = { lx,  0,  0, dx};
Point(3) = { lx, ly,  0, dx};
Point(4) = {  0, ly,  0, dx};
Point(11) = {  lx/2,  -lx,  0, dx};
Point(12) = { lx+ly, ly/2,  0, dx};
Point(13) = {  lx/2,    0,  0, dx};
Point(14) = {    lx, ly/2,  0, dx};

Circle(1) = {1, 11, 2};
Circle(2) = {2, 12, 3};
Circle(3) = {3, 13, 4};
Circle(4) = {4, 14, 1};
Line Loop(9) = {1, 2, 3, 4};

Plane Surface(10) = {9};

Physical Line(1) = {4}; 	// xmin
Physical Line(2) = {2}; 	// xmax
Physical Line(3) = {1}; 	// ymin
Physical Line(4) = {3}; 	// ymax
Physical Surface(5) = {10};
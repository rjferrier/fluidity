lx = 1.0;
nx = 80;

// for some reason mesh adaptivity complains 
// if extrusion isn't done in reverse

Point(1) = {lx, 0, 0};
Extrude {-lx, 0, 0} {
  Point{1}; Layers{nx}; 
}

// end boundaries
Physical Point(1) = {2};
Physical Point(2) = {1};

Physical Line(3) = {1};


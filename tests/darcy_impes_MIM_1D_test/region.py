def val(x):
	tol=1.0e-05
	if (x-0.0<tol):
		region=1
	elif (x-0.3<tol):
		region=2
	else:
		region=3
	return region

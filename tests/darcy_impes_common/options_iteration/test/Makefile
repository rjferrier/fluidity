define run
@echo
@printf '%70s\n' | tr ' ' =
@echo ' Running $1*.py'
@printf '%70s\n' | tr ' ' =
@echo
$(PYTHON) -m unittest discover -p '$1*.py'
@printf '%70s\n' | tr ' ' =
@echo
endef

clean:
	rm *.pyc -f
	rm *~ -f

w%: clean
	$(call run,$@)

t%: clean
	$(call run,$@)

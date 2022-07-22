dist: setup.py botlib/*
	@echo Building...
	python3 setup.py sdist bdist_wheel
	rm -rf ./*.egg-info/ ./build/ MANIFEST

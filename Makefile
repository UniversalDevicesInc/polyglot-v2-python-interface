
# When running from command line don't set user so it will use your ~/.pypirc file
ifneq ($(PYPI_USER),)
  PYPI_ARGS = -u '${PYPI_USER}' -p '${PYPI_PASSWORD}'
endif

.PHONY: install_dependancies build publish_pypi_test publish_pypi

all: install_dependancies build publish_pypi_test publish_pypi

install_dependancies:
	python3 -m pip install --upgrade pip setuptools wheel twine

build:
	python3 setup.py sdist
	python3 setup.py bdist_wheel

# This uses skip existing so it doesn't fail in regression
publish_pypi_test:
	twine upload --repository-url https://test.pypi.org/legacy/ --skip-existing $(PYPI_ARGS) dist/*

publish_pypi:
	twine upload $(PYPI_ARGS) dist/*

# If you already have a ~/.polyglot then make sure Test=1 is in it!
test_setup:
	if [ ! -d ~/.polyglot ]; then mkdir ~/.polyglot ; echo "Test=1\nUSE_HTTPS=false" > ~/.polyglot/.env ; fi
	python setup.py install

test:
	./scripts/tests.sh


# When running from command line don't set user so it will use your ~/.pypirc file
PYPI_ARGS != if [ ${PYPI_USER} = "" ]; then echo "" ; else echo "-u ${PYPI_USER} -p ${PYPI_PASSWORD}" ; fi

all: install_dependancies build publish_pypi_test publish_pypi

install_dependancies:
	python3 -m pip install --upgrade pip setuptools wheel twine

build:
	python3 setup.py sdist
	python3 setup.py bdist_wheel

publish_pypi_test:
	twine upload --repository-url https://test.pypi.org/legacy/ --skip-existing ${PYPI_ARGS} dist/*

publish_pypi:
	twine upload -u ${PYPI_USER} -p ${PYPY_PASSWORD} dist/*

# If you already have a ~/.polyglot then make sure Test=1 is in it!
test_setup:
	if [ ! -d ~/.polyglot ]; then mkdir ~/.polyglot ; echo "Test=1\nUSE_HTTPS=false" > ~/.polyglot/.env ; fi

test:
	./scripts/tests.sh

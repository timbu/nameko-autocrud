test: flake8 pylint pytest

flake8:
	flake8 nameko_autocrud test

pylint:
	pylint nameko_autocrud -E

pytest:
	coverage run --concurrency=eventlet --source nameko_autocrud --branch -m pytest test
	coverage report --show-missing --fail-under=100

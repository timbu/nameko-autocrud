from setuptools import setup, find_packages

setup(
    name='nameko-autocrud',
    version='0.1.2',
    description='Autocrud utility for nameko services',
    author='Student.com',
    author_email='wearehiring@student.com',
    url='http://github.com/timbu/nameko-autocrud',
    packages=find_packages(exclude=['test', 'test.*']),
    install_requires=[
        "nameko>=2.6.0",
        "sqlalchemy>=1.0.16",
        "sqlalchemy_filters>=0.4.0",
        "python-dateutil>=2.6.1",
        "sqlalchemy-utils>=0.32.5",
    ],
    extras_require={
        'dev': [
            "coverage==4.0.3",
            "flake8==2.5.4",
            "pylint==1.5.5",
            "pytest==3.0.5",
            "nameko_sqlalchemy>=0.1.0",
        ]
    },
    zip_safe=True,
    license='Apache License, Version 2.0',
    classifiers=[
        "Programming Language :: Python",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
    ]
)

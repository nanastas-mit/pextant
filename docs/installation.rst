================================
Installation Instructions
================================
pextant is developed in Python 3.7 (32 bit and 64 bit should both work). Future releases might include packaging and automatic installation through a ``setup.py`` file. In the meantime, installation is facilitated through a combination of the conda enviroment manager and the pip tool. 
**Only tested on Windows machines**

Quick instructions:
================================
.. code-block:: python

	# 1. Import the environment
	conda env create -f environment.yml

	# 2. Next, activate the enviroment (Windows users)
	activate pextant
	
	# or Mac and Linux users:
	source activate pextant


Make sure to have the environment activated in your terminal befor running >>> python xxxx.py in the console/terminal. 
If you use pycharm make sure to changes your interpreter settings:

Good to know about Conda Enviroment Manager
================================

For convenience, the following snippet summarizes conda commands that can be used to manage multiple python enviroments:

.. code-block:: python

	# Import existing enviroment from a file
	conda env create -f environment.yml

	# Create a new enviroment
	conda create --name pextant python

	# Activate an enviroment (Windows users)
	activate pextant
	
	# Activate an enviroment (Mac and Linux users)
	source activate pextant

	# Deactivate an enviroment (Windows users)
	deactivate pextant
	
	# Deactivate an enviroment (Mac and Linux users)
	source deactivate pextant

	# List all enviroments
	conda env list

	# Find current enviroment (look for the one with (*))
	conda info --envs

	# Clone an enviorment (with its packages)
	conda create --name pextant2 --clone pextant

	# Remove an enviroment
	conda remove --name pextant --all

	# List all packages in an enviroment
	conda list --name pextant

	# Install a package in a given enviroment
	conda install --name pextant matplotlib
	# Or activate the environment and it will automtically save it

	# Install a given version of a package
	conda install --name pextant matplotlib=1.5.1

	# Export active enviroment
	conda env export > environment.yml

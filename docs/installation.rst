================================
Installation Instructions
================================
pextant is developed in Python 3.7 (32 bit and 64 bit should both work). Future releases might include packaging and automatic installation through a ``setup.py`` file. In the meantime, installation is facilitated through a combination of the conda enviroment manager and the pip tool. 
**Only tested on Windows machines**

Clone This Repository
--------------------------------

You can clone this repo using whatever method you prefer (command line, GitHub Desktop GUI, whatever), but know this: **Inside the pextant_cpp folder is the pybind11 Git submodule**

In order to sync submodules, you must:

- Clone the repo in whatever way you prefer
- Open a command prompt (you can probably do through this via a GUI as well)
- Navigate to the local directory that you cloned the repo to
- Type the following commands:

.. code-block:: python

	git submodule init
	git submodule update

Create the 'pextant' Environment
--------------------------------

First, you need to create an anaconda environment that contains all of the necessary packages. This is most easily done using the environment.yml file. Open an anaconda prompt and type the following:

.. code-block:: python

	# create the environment from .yml file
	conda env create -f environment.yml

Build and Install 'pextant_cpp' package
---------------------------------------

Next, you need to build and install the custom python_cpp package.

Using Visual Studio 2019 (or higher):

- Make sure C++ CMake Tools for Windows is installed
	- Open Visual Studio Installer
	- On the 'Installed' tab, click the 'Modify' button on the Visual Studio installation you'd like to use
	- On the 'Individual Components' tab, check 'C++ CMake Tools for Windows'
	- Click the 'Modify' button (should be in the lower right corner of the screen)
	
- Open the Project (using 'Open Folder')
	- In Visual Studio, use 'File->Open->Open Folder' on the pextant_cpp folder
	- for more info, see Microsoft 'CMake Projects in Visual Studio' documenation
		(https://docs.microsoft.com/en-us/cpp/build/cmake-projects-in-visual-studio?view=vs-2019)
		
- Make sure project points to correct version of python.exe, CMake generator
	- Open the project settings using 'Project->CMake Settings for pextant_cpp' (just a special viewer for CMakeSettings.json)
	- In 'CMake Variables and Cache', set PYTHON_EXECUTABLE to whatever python.exe you're using
		- You may have to check 'show advanced variables' to see PYTHON_EXECUTABLE
	- Under 'Show Advanced Settings', set 'CMake generator' to whatever version of visual studio you're using
		- e.g. Visual Studio 16 2019 Win64
		
- Build the project!
	- click 'Project->Generate Cache for pextant_cpp'
	- if something goes wrong, refer to 'CMakeLists.txt' for more info
	
- Install module using setup.py
	- open command prompt
	- navigate to folder containing the pextant_cpp folder/project
	- type 'pip install ./pextant_cpp'
		- for this to work, you will need to have the CMake python package installed in your Python environment
	- this is where the module's version number lives, so if you change something you should update this
	
- All done!
	- a pextant_cpp .pyd should now live in the site-packages folder of your python environment


Activate the 'pextant' Environment
==================================
.. code-block:: python

	# Finally, activate the environment (Windows users)
	activate pextant
	
	# or Mac and Linux users:
	source activate pextant


Conda Tips and Tricks
======================

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

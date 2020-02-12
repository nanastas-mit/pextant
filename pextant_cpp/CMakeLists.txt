#[[
TO USE (Visual Studio 2019):

	GENERAL BUILDING:
		-Goto 'Project->CMake Settings' and check the following:
			-Under 'CMake variables and Cache', set 'PYTHON_EXECUTABLE' to your environment's python.exe file (you may have to check 'show advanced variables')
			-Under 'Advanced' (click 'show advanced settings'), make sure CMake generator is set to some version of visual studio
		-Build! click 'Project->Generate Cache'
		-Install the module from command line (from pextant root folder) with 'pip install ./pextant_cpp' (you'll need CMake package installed)
		-If you'd like to change something, you should update the version number at the bottom of setup.py
		-If you add a file that you'd like to have included in the package, simply add it in the 'INSTALL BLOCK' region below
		-If you add a class or a function to an existing file that you'd like to expose in python, you'll need to add a binding in 'PextantBindings.cpp'

	DEBUGGING:
		-There's probably a better way to debug this module that what I've setup (at least I hope there is...), so be forwarned - the following is pretty jank
		-Comment out the 'INSTALLING BLOCK', comment in the 'EXECUTABLE_BLOCK'
		-Change 'VS_DEBUGGER_WORKING_DIRECTORY' to the directory where your environment's python.exe file lives
		-Move the *whole* 'cpp_test_helper' folder into your 'VS_DEBUGGER_WORKING_DIRECTORY' (this just gives you some ability to call python functions from while debugging from cpp)
		-Build ('Project->Generate Cache')
		-Open the just-created visual studio solution (in the 'out/build' folder)
		-Set startup project to 'pextant_cpp'
		-Run! (main() is in RunTests.cpp)

	OTHER DEBUGGING OPTIONS TO LOOK INTO:
		-set 'VS_DEBUGGER_WORKING_DIRECTORY' to your pextant root directory (this in theory would allow you to pull in actual pextant modules)
			-I never got this to work - always failed to link with python37.lib. Tried messing with linking folders and PATH, but no dice. Maybe you'll have better luck!

	RANDOM:
		-After installing pextant_cpp module, PyCharm would sometimes refuse to refresh the module's skeleton (meaning no autocomplete). You can force 
			regeneration by deleting the stub (in PyCharm Project Window) in 'External Libraries/<Python X.Y>/Binary Skeletons'
]]

# min version and project name
cmake_minimum_required(VERSION 3.14)
project(pextant_cpp)

# additional places to search for files
include_directories(scripts)
add_subdirectory(pybind11)

# INSTALLING_BLOCK: comment in for extension package install, comment out for executable creation / debugging
# create the module (for installing)
pybind11_add_module(pextant_cpp
	scripts/bindings/PextantBindings.cpp

	scripts/headers/PathFinder.h
	scripts/headers/Algorithms.h
	scripts/headers/GraphNode.h
	scripts/headers/Utils.h

	scripts/src/PathFinder.cpp
	scripts/src/Algorithms.cpp
	scripts/src/GraphNode.cpp
	scripts/src/Utils.cpp
)
# --INSTALLING_BLOCK

#[[
# EXECUTABLE_BLOCK: comment out for extension package install, comment in for executable creation / debugging
add_compile_definitions(PEXTANT_DEBUGGING_EXECUTABLE)
# create an executable (for debugging)
add_executable(pextant_cpp
	scripts/bindings/PextantBindings.cpp
	
	scripts/headers/PathFinder.h
	scripts/headers/Algorithms.h
	scripts/headers/GraphNode.h
	scripts/headers/Tests.h
	scripts/headers/Utils.h
	
	scripts/src/PathFinder.cpp
	scripts/src/Algorithms.cpp
	scripts/src/GraphNode.cpp
	scripts/src/Tests.cpp
	scripts/src/Utils.cpp

	scripts/src/RunTests.cpp
	scripts/src/Tests.cpp
)
set_target_properties(pextant_cpp PROPERTIES
	VS_DEBUGGER_WORKING_DIRECTORY C:/Users/nqa0604/AppData/Local/Continuum/anaconda2/envs/pextant_3  # ***CHANGE ME TO WHATEVER YOUR python.exe DIRECTORY IS***
)
target_link_libraries(pextant_cpp
	pybind11::embed
)
# --EXECUTABLE_BLOCK
]]

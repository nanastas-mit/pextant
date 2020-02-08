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

	scripts/headers/Algorithms.h
	scripts/headers/GraphNode.h
	scripts/headers/Tests.h
	scripts/headers/Utils.h

	scripts/src/Algorithms.cpp
	scripts/src/GraphNode.cpp
	scripts/src/Tests.cpp
	scripts/src/Utils.cpp
)
# --INSTALLING_BLOCK

#[[
# EXECUTABLE_BLOCK: comment out for extension package install, comment in for executable creation / debugging
add_compile_definitions(PEXTANT_DEBUGGING_EXECUTABLE)
# create an executable (for debugging)
add_executable(pextant_cpp
	scripts/bindings/PextantBindings.cpp

	scripts/headers/Algorithms.h
	scripts/headers/GraphNode.h
	scripts/headers/Tests.h
	scripts/headers/Utils.h

	scripts/src/Algorithms.cpp
	scripts/src/GraphNode.cpp
	scripts/src/Tests.cpp
	scripts/src/Utils.cpp

	scripts/src/RunTests.cpp
	scripts/src/Tests.cpp
)
set_target_properties(pextant_cpp PROPERTIES
	VS_DEBUGGER_WORKING_DIRECTORY C:/Users/nqa0604/AppData/Local/Continuum/anaconda2/envs/pextant_3
)
target_link_libraries(pextant_cpp
	pybind11::embed
)
# --EXECUTABLE_BLOCK
]]

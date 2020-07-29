Using Visual Studio 2019+
-Make sure C++ CMake Tools for Windows is installed
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

- Debugging
	- There's probably a better way to debug this module that what I've setup (at least I hope there is...), so be forwarned - the following is pretty jank
	- Comment out the 'INSTALLING BLOCK', comment in the 'EXECUTABLE_BLOCK'
	- Change 'VS_DEBUGGER_WORKING_DIRECTORY' to the directory where your environment's python.exe file lives
	- Move the *whole* 'cpp_test_helper' folder into your 'VS_DEBUGGER_WORKING_DIRECTORY' (this just gives you some ability to call python functions from while debugging from cpp)
	- Build ('Project->Generate Cache')
	- Open the just-created visual studio solution (in the 'out/build' folder)
	- Set startup project to 'pextant_cpp'
	- Run! (main() is in RunTests.cpp)

- What Debugging *should* be
	- set 'VS_DEBUGGER_WORKING_DIRECTORY' to your pextant root directory (this in theory would allow you to pull in actual pextant modules)
		- I never got this to work - always failed to link with python37.lib. Tried messing with linking folders and PATH, but no dice. Maybe you'll have better luck!

- Random:
	- After installing pextant_cpp module, PyCharm would sometimes refuse to refresh the module's skeleton (meaning no autocomplete). You can force 
		regeneration by deleting the stub (in PyCharm Project Window) in 'External Libraries/<Python X.Y>/Binary Skeletons'
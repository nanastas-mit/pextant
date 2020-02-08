import sys
sys.path.append('../../')
import argparse
from pextant.backend_app.app_state_manager import AppStateManager

if __name__ == '__main__':

    # SETUP COMMAND LINE OPTIONS
    parser = argparse.ArgumentParser()
    # create_gui
    parser.add_argument(
        "-ui", "--create_gui",
        help="run the server with a GUI",
        action="store_true"
    )

    # parse command line
    args = parser.parse_args()

    # create the app state manager
    app_man = AppStateManager(create_gui=args.create_gui)
    app_man.mainloop()

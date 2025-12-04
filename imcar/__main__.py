import multiprocessing
import sys

if __name__ == "__main__":
    # Required for Windows executables using multiprocessing
    multiprocessing.freeze_support()
    
    from imcar.app.start import main
    main(testing="--test" in sys.argv)

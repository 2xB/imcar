from imcar.app.start import main
import sys

if __name__ == "__main__":
    main(testing="--test" in sys.argv)

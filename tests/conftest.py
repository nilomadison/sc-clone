import os
import sys

# Run pygame headless for all tests
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

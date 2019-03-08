import sys

from . import reader

if sys.argv[1] == "reader":
    reader.run()
else:
    print("USAGE: COMMAND <reader>")

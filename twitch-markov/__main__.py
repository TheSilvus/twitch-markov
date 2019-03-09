import sys

from . import reader
from . import generator
from . import writer

if sys.argv[1] == "reader":
    reader.run()
elif sys.argv[1] == "generator":
    generator.run()
elif sys.argv[1] == "writer":
    writer.run()
else:
    print("USAGE: COMMAND <reader>")

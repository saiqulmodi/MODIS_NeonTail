# Empty on purpose. pytest always loads a root conftest.py before
# collecting tests, and adds this file's directory (the project root,
# where main.py lives) to sys.path in the process -- that's what lets
# "import main" work from inside tests/, since main.py isn't part of an
# installable package.

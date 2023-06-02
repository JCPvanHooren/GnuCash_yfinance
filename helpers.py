"""Helper Classes & Functions used across multiple modules

If run as main module (not imported): print Arguments

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

from typing import Optional

def print_headerline(char: str, leading_newline: Optional[bool] = False) -> None:
    """Print a headerline, optionally with a leading empty line

    Args:
        char: Character to be printed 64 times.
        leading_newline: Print an empty line before printing the headerline. Defaults to False.

    """

    if leading_newline:
        print()
    print(char * 64)

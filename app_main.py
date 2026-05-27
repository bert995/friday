"""Entry point for the packaged Friday.app.

PyInstaller analyses this file. It stays a thin wrapper so that `pet` keeps
being imported as a *package* (its modules use relative imports like
`from .bridge import Api`, which only work via the package — not when a module
inside it is run directly as the program's main script).
"""

from pet.shell import main

if __name__ == "__main__":
    main()

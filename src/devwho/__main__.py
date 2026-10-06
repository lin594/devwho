"""Allow both python -m devwho and the pinned shell-integration launcher."""

import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from devwho.cli import main

raise SystemExit(main())

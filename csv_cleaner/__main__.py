"""Allow ``python -m csv_cleaner``."""

import sys

from .cli import main

sys.exit(main())

"""Nepal Entity Service - A comprehensive service for managing Nepali public entities."""

__version__ = "0.1.0"

# Core exports
from .models import *

# Conditional imports based on available extras
try:
    from .api import *
except ImportError:
    pass

try:
    from .scraping import *
except ImportError:
    pass
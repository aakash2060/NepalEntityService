"""Model constraints and validation constants."""

# Length constraints
MAX_ID_LENGTH = 32
MAX_TYPE_LENGTH = 16
MAX_SUBTYPE_LENGTH = 16
MAX_SLUG_LENGTH = 64
MIN_SLUG_LENGTH = 3
MAX_SHORT_DESCRIPTION_LENGTH = 300
MAX_DESCRIPTION_LENGTH = 5000

# Regex patterns
ENTITY_TYPE_PATTERN = r"^[a-z_]+$"
ENTITY_SUBTYPE_PATTERN = r"^[a-z_]+$"
SLUG_PATTERN = r"^[a-z0-9-]+$"

# Usage Examples

## Installing Package with Extras

### Install Core Models Only
```bash
pip install nepal-entity-service
```

```python
from nes.models import Entity, Person, Relationship

person = Person(
    id="123",
    names={"en": "John Doe"},
    attributes={"role": "Politician"}
)
```

### Install and Extend the API
```bash
pip install nepal-entity-service[api]
```

```python
from fastapi import APIRouter
from nes.api import app

# Add your custom routes
custom_router = APIRouter()

@custom_router.get("/custom")
asyncnes.apistom_endpoint():
    return {"message": "Custom endpoint"}

app.include_router(custom_router)

# Run with: uvicorn your_api:app
```

### Use Scraping Tools
```bash
pip install nepal-entity-service[scraping]
```

```python
from nes.scraping.wikipedia_nepali_politicians import get_nepali_politician_page_links

links = get_nepali_politician_page_links()
print(f"Found {len(links)} politicians")
```

### Full Installation
```bash
pip install nepal-entity-service[all]
```

## Git Installation

```bash
pip install git+https://github.com/yourusername/NepalEntityService.git[api]
```

## Local Development

```bash
git clone <repository-url>
cd NepalEntityService
pip install -e .[all,dev]
```
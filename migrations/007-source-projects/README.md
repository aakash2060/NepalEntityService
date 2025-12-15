# Migration 007: Import Development Projects

## Purpose

Import development project data from multiple sources into the Nepal Entity Service. This migration supports a multi-source architecture for aggregating project data from:

- **MoF DFMIS** (Ministry of Finance - Development Finance Information Management System) ✅ Implemented
- **World Bank** (planned)
- **Asian Development Bank (ADB)** (planned)
- **JICA** (planned)
- **NPC Project Bank** (planned)

## Data Sources

### MoF DFMIS (Primary Source)
- **API**: https://dfims.mof.gov.np/api/v2/core/projects/
- **Authority**: Ministry of Finance, Nepal
- **Data Type**: All development projects registered in Nepal's DFMIS system
- **Coverage**: ~2,757 projects

### World Bank (Planned)
- **API**: World Bank Projects API
- **Data Type**: World Bank-funded projects in Nepal

### Asian Development Bank (Planned)
- **API**: ADB IATI Data
- **Data Type**: ADB-funded projects in Nepal

### JICA (Planned)
- **API**: JICA Project Database
- **Data Type**: Japanese ODA projects in Nepal

## Two-Step Process

This migration uses a two-step approach for each data source:

### Step 1: Scrape Data

Run the scraping script for the desired source:

**MoF DFMIS:**
```bash
cd migrations/007-source-projects/mof_dfmis
poetry run python scrape_mof_dfmis.py
```

This will:
1. Fetch all projects from the DFMIS API (with caching to `all_projects.json`)
2. Normalize data to the standard Project model
3. Save transformed data to `source/dfmis_projects.jsonl`

### Step 2: Run Migration

After scraping, run the migration to import the data:

```bash
poetry run nes migration run 007-source-projects
```

## What Gets Created

### Project Entities
- Bilingual names (English and Nepali where available)
- External identifiers (source project IDs)
- Project stage (pipeline, planning, approved, ongoing, completed, etc.)
- Financing components (loans, grants, mixed)
- Date events (approval, start, completion)
- Sector mappings
- Donor information

### Organization Entities (auto-created)
- Development agencies (donors)
- Implementing agencies
- Executing agencies
- Classified by subtype: `government_body`, `international_org`, `ngo`

### Relationships
- `FUNDED_BY`: Project → Donor organization
- `IMPLEMENTED_BY`: Project → Implementing agency
- `EXECUTED_BY`: Project → Executing agency
- `LOCATED_IN`: Project → Location (province/district/municipality)

## Data Normalization

The migration performs the following normalization:

1. **Project Stage**: Maps source-specific statuses to standard stages
2. **Organizations**: Auto-classifies by architecture (Government, Multilateral, Bilateral, NGO, INGO)
3. **Locations**: Links to existing location entities using fuzzy matching
4. **Financing**: Normalizes to grant/loan/mixed instrument types
5. **Dates**: Extracts approval, effectiveness, and completion dates

## Project Model

The `Project` entity extends the base `Entity` model with:

```python
class Project(Entity):
    type: Literal["project"]
    sub_type: EntitySubType = DEVELOPMENT_PROJECT
    stage: ProjectStage
    implementing_agency: Optional[str]
    executing_agency: Optional[str]
    financing: Optional[List[FinancingComponent]]
    dates: Optional[List[ProjectDateEvent]]
    locations: Optional[List[ProjectLocation]]
    sectors: Optional[List[SectorMapping]]
    tags: Optional[List[CrossCuttingTag]]
    donors: Optional[List[str]]
    donor_extensions: Optional[List[DonorExtension]]
    project_url: Optional[AnyUrl]
```

## File Structure

```
migrations/007-source-projects/
├── migrate.py              # Main migration script
├── README.md               # This file
├── mof_dfmis/
│   ├── scrape_mof_dfmis.py # DFMIS scraper
│   └── all_projects.json   # Raw API cache (auto-generated)
├── world_bank/             # (planned)
│   └── scrape_world_bank.py
├── adb/                    # (planned)
│   └── scrape_adb.py
└── source/
    ├── dfmis_projects.jsonl    # Transformed DFMIS data
    ├── world_bank_projects.jsonl  # (planned)
    └── adb_projects.jsonl         # (planned)
```

## Adding New Sources

To add a new data source:

1. Create a new folder: `migrations/007-source-projects/<source_name>/`
2. Create a scraper: `scrape_<source_name>.py`
3. Output to: `source/<source_name>_projects.jsonl`
4. Update `migrate.py` to load from the new source file
5. Add source-specific normalization logic

### Scraper Template

```python
async def scrape_and_save_projects(output_file: str = "<source>_projects.jsonl") -> int:
    """Scrape projects and save to JSONL file."""
    # 1. Fetch from API
    # 2. Normalize to Project model
    # 3. Add _migration_metadata for relationships
    # 4. Save to source/ directory
```

## Testing

After running the migration:

### Search for projects

```bash
nes search entities --type project --subtype development_project --limit 3
```

Example output:
```
Found 3 entities:

entity:project/development_project/dfmis-1317
  Name: Japanese FoodAid(KR)-2017
  Type: project/EntitySubType.DEVELOPMENT_PROJECT
  Version: 1

entity:project/development_project/dfmis-559
  Name: Rural Community Infrastructure Development Programme/Works
  Type: project/EntitySubType.DEVELOPMENT_PROJECT
  Version: 1

entity:project/development_project/dfmis-2184
  Name: Women and Girls' Leadership and Voice (LEAD)
  Type: project/EntitySubType.DEVELOPMENT_PROJECT
  Version: 1
```

### View a project

```bash
nes show entity:project/development_project/dfmis-1234
```

Example output:
```
Entity: entity:project/development_project/dfmis-1234
Type: project/EntitySubType.DEVELOPMENT_PROJECT
Slug: dfmis-1234

Names:
  PRIMARY:
    English: Pasang Lhamu-Nicole Niquille Hospital, Lukla

Identifiers:
  IdentifierScheme.OTHER: 1234

Version: 1
Created: 2025-12-15 12:08:37.515523+00:00
Author: nava-yuwa-central
```

### Check relationships for a project

```bash
nes search relationships --source entity:project/development_project/dfmis-1234
```

Example output:
```
Found 4 relationships:

relationship:...:FUNDED_BY
  Type: FUNDED_BY
  Source: entity:project/development_project/dfmis-1234
  Target: entity:organization/international_org/foundation-nicole-niquille-hospital-lukla

relationship:...:IMPLEMENTED_BY
  Type: IMPLEMENTED_BY
  Source: entity:project/development_project/dfmis-1234
  Target: entity:organization/ngo/pasang-lhamu-mountaineering-foundation

relationship:...:EXECUTED_BY
  Type: EXECUTED_BY
  Source: entity:project/development_project/dfmis-1234
  Target: entity:organization/international_org/foundation-nicole-niquille-hospital-lukla

relationship:...:LOCATED_IN
  Type: LOCATED_IN
  Source: entity:project/development_project/dfmis-1234
  Target: entity:location/district/solukhumbu
```

## Statistics (Current)

| Source | Projects | Organizations | Relationships |
|--------|----------|---------------|---------------|
| MoF DFMIS | 2,757 | ~500+ | ~17,500+ |
| World Bank | - | - | - |
| ADB | - | - | - |
| JICA | - | - | - |

## Rollback

To rollback this migration:

```bash
poetry run nes migration rollback 007-source-projects
```

This will remove all project entities, auto-created organizations, and relationships created by this migration.

## Notes

- The DFMIS API requires session cookies (handled automatically)
- Raw API responses are cached to `all_projects.json` for faster re-runs
- Location matching uses aliases for common misspellings
- Organizations are deduplicated by name before creation
- Projects without titles are skipped

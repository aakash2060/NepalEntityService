# Migration: 000-example-migration

## Purpose
Create the first entity in the Nepal Entity Service database - Bishweshwar Prasad Koirala (BP Koirala), the first democratically elected Prime Minister of Nepal.

## Data Sources
- Historical records of Nepal's political history
- BP Koirala's documented names in Nepali and English

## Changes
- **Entities created**: 1
  - `bishweshwar-prasad-koirala` (Person)
- **Relationships created**: 0

## Entity Details

### BP Koirala (bishweshwar-prasad-koirala)
- **Type**: Person
- **Primary Name (Nepali)**: विश्वेश्वर प्रसाद कोइराला
- **Primary Name (English)**: Bishweshwar Prasad Koirala
- **Common Name**: BP Koirala / बी पी कोइराला
- **Significance**: First democratically elected Prime Minister of Nepal

## Dependencies
None (this is the initial migration)

## Notes
This migration serves as:
- The first real entity in the database
- An example of proper entity structure with Nepali and English names
- A foundation for future political entity migrations
- A test case for the migration system

## Next Steps
After this migration is applied, subsequent migrations can add:
- `001-locations` - Import location data (provinces, districts, municipalities)
- `002-political-parties` - Import political party entities
- `003-government-positions` - Add relationships for government positions

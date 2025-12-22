"""
ADB (Asian Development Bank) Data Scraper for Nepal Development Projects.

This module provides functionality to extract project data from
the ADB IATI XML feed for projects related to Nepal. It follows the
existing architecture patterns in the nes project and transforms
ADB data to match the standardized project schema used by other sources.
"""

import asyncio
import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

from nes.services.scraping.web_scraper import RateLimiter, RetryHandler

# Configure logging
logger = logging.getLogger(__name__)


# --- Helpers -----------------------------------------------------------------
def first_text(elem) -> Optional[str]:
    if elem is None:
        return None
    # If element contains nested <narrative> elements, prefer the first text inside them
    narr = elem.find(".//narrative")
    if narr is not None and narr.text and narr.text.strip():
        return narr.text.strip()
    # fallback to text of elem
    return elem.text.strip() if elem.text and elem.text.strip() else None


def localname(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def parse_iati_xml(xml_text: str) -> List[Dict[str, Any]]:
    root = ET.fromstring(xml_text)
    activities = []
    # find all iati-activity elements regardless of namespace
    for act in root:
        if localname(act.tag) != "iati-activity":
            continue
        activity = {}
        # top-level attrs
        activity["default_currency"] = act.get("default-currency")
        activity["hierarchy"] = act.get("hierarchy")
        activity["last_updated"] = act.get("last-updated-datetime")

        # iati-identifier
        id_el = next((c for c in act if localname(c.tag) == "iati-identifier"), None)
        activity["iati_identifier"] = first_text(id_el) if id_el is not None else None

        # reporting-org
        rep = next((c for c in act if localname(c.tag) == "reporting-org"), None)
        if rep is not None:
            activity["reporting_org_ref"] = rep.get("ref")
            activity["reporting_org_type"] = rep.get("type")
            activity["reporting_org_narrative"] = first_text(rep)

        # title & description
        title = next((c for c in act if localname(c.tag) == "title"), None)
        activity["title"] = first_text(title)
        desc = next((c for c in act if localname(c.tag) == "description"), None)
        activity["description"] = first_text(desc)

        # participating-orgs
        parts = []
        for p in [c for c in act if localname(c.tag) == "participating-org"]:
            parts.append(
                {
                    "ref": p.get("ref"),
                    "role": p.get("role"),
                    "type": p.get("type"),
                    "name": first_text(p),
                }
            )
        activity["participating_orgs"] = parts

        # other-identifier(s)
        other_ids = []
        for o in [c for c in act if localname(c.tag) == "other-identifier"]:
            other_ids.append(
                {
                    "ref": o.get("ref"),
                    "type": o.get("type"),
                    "owner_org": first_text(o.find(".//owner-org")),
                }
            )
        activity["other_identifiers"] = other_ids

        # activity-status
        status = next((c for c in act if localname(c.tag) == "activity-status"), None)
        activity["activity_status"] = status.get("code") if status is not None else None

        # activity-date (may be many types)
        dates = []
        for d in [c for c in act if localname(c.tag) == "activity-date"]:
            dates.append({"iso_date": d.get("iso-date"), "type": d.get("type")})
        activity["activity_dates"] = dates

        # contact-info
        contact = next((c for c in act if localname(c.tag) == "contact-info"), None)
        if contact is not None:
            activity["contact"] = {
                "organisation": first_text(contact.find(".//organisation")),
                "person_name": first_text(contact.find(".//person-name")),
                "website": first_text(contact.find(".//website")),
            }
        else:
            activity["contact"] = None

        # recipient-country
        rc = next((c for c in act if localname(c.tag) == "recipient-country"), None)
        activity["recipient_country"] = rc.get("code") if rc is not None else None

        # locations -> collect list of {name, lat, lon, id, exactness, reach}
        locs = []
        for loc in [c for c in act if localname(c.tag) == "location"]:
            name = first_text(loc.find(".//name"))
            # find <pos> text
            pos_el = None
            # search for point/pos using localname matching
            for el in loc.iter():
                if localname(el.tag) == "pos":
                    pos_el = el
                    break
            lat = lon = None
            if pos_el is not None and pos_el.text:
                # pos seems "lat lon" or "lat lon" reversed often; IATI uses "lat lon" as in your sample: "27.95179 85.19261"
                try:
                    parts = pos_el.text.strip().split()
                    if len(parts) >= 2:
                        lat = float(parts[0])
                        lon = float(parts[1])
                except Exception:
                    lat = lon = None
            # location-id
            loc_id_el = next(
                (c for c in loc if localname(c.tag) == "location-id"), None
            )
            locs.append(
                {
                    "name": name,
                    "lat": lat,
                    "lon": lon,
                    "location_id": (
                        loc_id_el.get("code") if loc_id_el is not None else None
                    ),
                    "exactness": (
                        loc.find(".//exactness").get("code")
                        if loc.find(".//exactness") is not None
                        else None
                    ),
                    "reach": (
                        next(
                            (
                                c.get("code")
                                for c in loc
                                if localname(c.tag) == "location-reach"
                            ),
                            None,
                        )
                    ),
                }
            )
        activity["locations"] = locs

        # sectors
        sectors = []
        for s in [c for c in act if localname(c.tag) == "sector"]:
            sectors.append({"code": s.get("code"), "vocabulary": s.get("vocabulary")})
        activity["sectors"] = sectors

        # policy-marker(s)
        policy = []
        for p in [c for c in act if localname(c.tag) == "policy-marker"]:
            policy.append(
                {
                    "code": p.get("code"),
                    "vocabulary": p.get("vocabulary"),
                    "vocabulary_uri": p.get("vocabulary-uri"),
                    "narrative": first_text(p),
                }
            )
        activity["policy_markers"] = policy

        # store raw xml snippet? optional
        # activity['raw'] = ET.tostring(act, encoding='unicode')

        activities.append(activity)
    return activities


class ADBAPIClient:
    """HTTP client for ADB IATI XML data with rate limiting and retry logic."""

    def __init__(
        self,
        requests_per_second: float = 0.5,  # Conservative rate limit
        requests_per_minute: int = 30,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """Initialize the ADB API client.

        Args:
            requests_per_second: Maximum requests per second per domain
            requests_per_minute: Maximum requests per minute per domain
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        self.rate_limiter = RateLimiter(
            requests_per_second=requests_per_second,
            requests_per_minute=requests_per_minute,
        )
        self.retry_handler = RetryHandler(max_retries=max_retries)
        self.timeout = timeout
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        # Create a session that can store cookies for authentication
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
                "Accept": "application/xml, text/xml, */*",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _make_request(
        self, url: str, params: Optional[Dict] = None
    ) -> Optional[str]:
        """Make a request to the ADB API endpoint with rate limiting and error handling.

        Args:
            url: The API endpoint URL
            params: Query parameters for the request

        Returns:
            Response data or None if request fails
        """
        if not self.session:
            raise RuntimeError(
                "Client not initialized. Use within async context manager."
            )

        # Apply rate limiting
        await self.rate_limiter.acquire("www.adb.org")

        # Prepare URL with parameters
        if params:
            query_string = urlencode(params)
            full_url = f"{url}?{query_string}"
        else:
            full_url = url

        try:
            # Use browser-like headers to mimic web requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
                "Accept": "application/json, application/xml, text/xml, */*",
                "Accept-Encoding": "gzip, deflate",  # Removed 'br' to avoid brotli issues
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }

            async with self.session.get(full_url, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 401:
                    logger.warning(
                        f"Unauthorized access to {full_url}. Need proper authentication."
                    )
                elif response.status == 403:
                    logger.warning(
                        f"Forbidden access to {full_url}. May require login or special permissions."
                    )
                elif response.status == 404:
                    logger.warning(f"Endpoint not found: {full_url}")

                logger.warning(
                    f"API request failed with status {response.status}: {full_url}"
                )
                logger.warning(f"Response text: {await response.text()}")
                return None
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for URL: {full_url}")
            return None
        except Exception as e:
            logger.error(f"Error making request to {full_url}: {e}")
            return None


class ADBProjectScraper:
    """Scraper for ADB (Asian Development Bank) projects in Nepal."""

    # ADB IATI XML endpoint for Nepal projects
    ADB_IATI_XML_URL = "https://www.adb.org/iati/iati-activities-np.xml"

    def __init__(self, client: Optional[ADBAPIClient] = None):
        """Initialize the ADB project scraper.

        Args:
            client: ADBAPIClient instance. If None, a default client will be created
        """
        self.client = client or ADBAPIClient()

    async def search_adb_projects(self) -> List[Dict[str, Any]]:
        """Search for ADB projects related to Nepal.

        Returns:
            List of project data dictionaries
        """
        async with self.client:
            projects = await self._fetch_projects_from_adb_api()
            logger.info(f"Successfully scraped {len(projects)} projects from ADB")
            return projects

    async def _fetch_projects_from_adb_api(self) -> List[Dict[str, Any]]:
        """Fetch projects from ADB JSON API, with fallback to local XML if API fails.

        Returns:
            List of project data dictionaries
        """
        # Try to fetch from ADB JSON API for projects instead of XML
        # This is based on known ADB API endpoints for project data
        # Try multiple potential endpoints for ADB project data
        potential_urls = [
            "https://www.adb.org/api/projects/country/NP",  # Official ADB endpoint for Nepal projects
            "https://www.adb.org/api/v2/projects?country_code=NP",  # Alternative format
            "https://data.adb.org/api/v2/projects/search?country_code=NP&format=json",  # Data portal API
            "https://www.adb.org/api/v2/projects/search?country_code=NP&format=json",  # Search API
            "https://www.adb.org/api/projects/search?query=Nepal&format=json",  # Search by query
        ]

        for api_url in potential_urls:
            try:
                logger.info(f"Attempting to fetch data from ADB JSON API: {api_url}")
                import json as json_mod

                # Use the client's _make_request but expect JSON response
                json_data = await self.client._make_request(api_url)

                if json_data:
                    logger.info("Successfully fetched ADB JSON data")

                    # Save the raw JSON data to all_projects.json in the ADB directory
                    raw_json_path = os.path.join(
                        os.path.dirname(__file__), "all_projects.json"
                    )
                    try:
                        parsed_data = json_mod.loads(json_data)
                        with open(raw_json_path, "w", encoding="utf-8") as f:
                            json.dump(parsed_data, f, ensure_ascii=False, indent=2)
                        logger.info(f"Saved raw JSON data to {raw_json_path}")
                    except json_mod.JSONDecodeError as e:
                        logger.warning(f"Could not save raw JSON data: {e}")

                    # Parse the JSON response
                    try:
                        parsed_data = json_mod.loads(json_data)
                        # Extract projects from the JSON response
                        projects = self._extract_projects_from_json_api_response(
                            parsed_data
                        )
                        if projects:
                            logger.info(
                                f"Successfully extracted {len(projects)} projects from JSON API"
                            )
                            return projects
                    except json_mod.JSONDecodeError as e:
                        logger.warning(
                            f"Could not parse JSON response from {api_url}: {e}"
                        )
                        continue  # Try next URL
            except Exception as e:
                logger.error(f"Error fetching from {api_url}: {e}")
                continue  # Try next URL

        logger.warning("All ADB JSON API attempts failed, trying IATI XML...")

        # If JSON API fails, try the IATI XML as a fallback
        xml_url = self.ADB_IATI_XML_URL
        try:
            logger.info(f"Attempting to fetch data from ADB IATI XML: {xml_url}")
            xml_data = await self.client._make_request(xml_url)

            if xml_data is not None:
                logger.info("Successfully fetched ADB IATI XML data")

                # Save the raw XML data to all_projects.xml in the ADB directory
                raw_xml_path = os.path.join(
                    os.path.dirname(__file__), "all_projects.xml"
                )
                try:
                    with open(raw_xml_path, "w", encoding="utf-8") as f:
                        f.write(xml_data)
                    logger.info(f"Saved raw XML data to {raw_xml_path}")
                except Exception as e:
                    logger.warning(f"Could not save raw XML data: {e}")

                # Parse the XML data directly
                activities = parse_iati_xml(xml_data)

                # Save the parsed XML data as JSON (in the standard format) to all_projects.json
                parsed_json_path = os.path.join(
                    os.path.dirname(__file__), "all_projects.json"
                )
                try:
                    with open(parsed_json_path, "w", encoding="utf-8") as f:
                        json.dump(activities, f, ensure_ascii=False, indent=2)
                    logger.info(f"Saved parsed XML data as JSON to {parsed_json_path}")
                except Exception as e:
                    logger.warning(f"Could not save parsed XML as JSON: {e}")

                # Transform to the standardized format
                transformed_projects = [
                    self._normalize_adb_project(activity) for activity in activities
                ]
                # Filter out any None values
                transformed_projects = [
                    p for p in transformed_projects if p is not None
                ]
                return transformed_projects
            else:
                logger.warning(
                    "ADB IATI XML request failed, trying to load from local file..."
                )
        except Exception as e:
            logger.error(f"Error fetching from ADB IATI XML: {e}")

        # If both API attempts fail, load from the local file as fallback
        return await self._load_from_local_file()

    def _extract_projects_from_json_api_response(
        self, json_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract project data from ADB JSON API response.

        Args:
            json_data: Parsed JSON response from ADB API

        Returns:
            List of project data dictionaries in standard format
        """
        projects = []

        # Handle different possible JSON response structures
        if isinstance(json_data, dict):
            # Look for projects in various possible fields
            possible_project_fields = [
                "data",
                "projects",
                "results",
                "items",
                "entities",
            ]

            for field in possible_project_fields:
                if field in json_data:
                    data = json_data[field]
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                normalized = self._normalize_adb_json_project(item)
                                if normalized:
                                    projects.append(normalized)
                        return projects
                    elif isinstance(data, dict):
                        # If it's a single project or a complex object
                        normalized = self._normalize_adb_json_project(data)
                        if normalized:
                            projects.append(normalized)
                        return projects

        elif isinstance(json_data, list):
            # If the response is directly a list of projects
            for item in json_data:
                if isinstance(item, dict):
                    normalized = self._normalize_adb_json_project(item)
                    if normalized:
                        projects.append(normalized)

        return projects

    def _normalize_adb_json_project(
        self, project_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Normalize a single ADB project from JSON API to match the standardized project format.

        Args:
            project_data: Raw project data from ADB JSON API

        Returns:
            Normalized project data in standard format, or None if invalid
        """
        try:
            # Extract project_id with fallbacks
            project_id = (
                project_data.get("id")
                or project_data.get("project_id")
                or project_data.get("projectId")
                or project_data.get("project_number")
                or project_data.get("projectNumber")
                or ""
            )

            # Extract title with fallbacks
            title = (
                project_data.get("title")
                or project_data.get("name")
                or project_data.get("project_name")
                or project_data.get("projectName")
                or str(project_id)
                if project_id
                else ""
            ).strip()

            # Extract description
            description = (
                project_data.get("description")
                or project_data.get("project_description")
                or project_data.get("projectDescription")
                or project_data.get("summary", "")
                or ""
            )

            # Extract implementing agency
            implementing_agency = (
                project_data.get("implementing_agency")
                or project_data.get("implementingAgency")
                or project_data.get("executing_agency")
                or project_data.get("executingAgency")
                or project_data.get("agency", "")
                or ""
            )

            # Extract location info
            country_code = (
                project_data.get("country_code")
                or project_data.get("countryCode")
                or project_data.get("recipient_country")
                or project_data.get("recipientCountry", "")
            ).upper()

            # Default to Nepal if not specified otherwise
            location = {
                "country": (
                    "Nepal"
                    if country_code == "NP"
                    else project_data.get("country", "Nepal")
                ),
                "country_code": country_code if country_code else "NP",
                "region": (
                    project_data.get("region")
                    or project_data.get("project_region", "")
                    or project_data.get("location", "")
                ),
                "province": project_data.get("province", ""),
                "district": project_data.get("district", ""),
                "municipality": project_data.get("municipality", ""),
            }

            # Extract dates
            start_date = (
                project_data.get("start_date")
                or project_data.get("startDate")
                or project_data.get("approval_date")
                or project_data.get("approvalDate", "")
            )
            end_date = (
                project_data.get("end_date")
                or project_data.get("endDate")
                or project_data.get("closing_date")
                or project_data.get("closingDate", "")
            )

            # Extract funding source information
            funding_source = (
                project_data.get("funding_source")
                or project_data.get("funder")
                or project_data.get("financier", "Asian Development Bank")
            )

            # Create normalized project
            normalized_project = {
                "project_id": str(project_id) if project_id else "",
                "title": title,
                "description": description,
                "implementing_agency": implementing_agency,
                "start_date": start_date,
                "end_date": end_date,
                "location": location,
                "funding_source": funding_source,
                "total_allocated_budget": str(
                    project_data.get("total_amount")
                    or project_data.get("totalAmount")
                    or project_data.get("amount")
                    or project_data.get("budget", "")
                ),
                "real_time_spending": str(
                    project_data.get("spending")
                    or project_data.get("disbursement", "")
                    or ""
                ),
                "loan_amount": str(
                    project_data.get("loan_amount")
                    or project_data.get("loanAmount", "")
                    or ""
                ),
                "grant_amount": str(
                    project_data.get("grant_amount")
                    or project_data.get("grantAmount", "")
                    or ""
                ),
                "physical_progress": str(
                    project_data.get("physical_progress")
                    or project_data.get("physicalProgress", "")
                    or ""
                ),
                "financial_progress": str(
                    project_data.get("financial_progress")
                    or project_data.get("financialProgress", "")
                    or ""
                ),
                "borrower": (
                    project_data.get("borrower")
                    or project_data.get("borrowing_entity", "")
                    or ""
                ),
                "sector": (
                    project_data.get("sector")
                    or project_data.get("project_sector", "")
                    or project_data.get("sector_name", "")
                    or ""
                ),
                "major_theme": (
                    project_data.get("theme")
                    or project_data.get("major_theme", "")
                    or project_data.get("category", "")
                    or ""
                ),
                "environmental_category": (
                    project_data.get("environmental_category")
                    or project_data.get("environmentCategory", "")
                    or ""
                ),
                "implementation_status": (
                    project_data.get("status")
                    or project_data.get("project_status")
                    or project_data.get("implementationStatus", "")
                    or ""
                ),
                "url": (
                    project_data.get("url")
                    or project_data.get("project_url")
                    or project_data.get("projectUrl", "")
                    or f"https://www.adb.org/projects/{project_id}"
                    if project_id
                    else ""
                ),
                "project_document_url": (
                    project_data.get("document_url")
                    or project_data.get("documents_url")
                    or project_data.get("docsUrl", "")
                    or ""
                ),
                "milestones": project_data.get(
                    "milestones", project_data.get("milestone", [])
                ),
                "yearly_budget_breakdown": project_data.get(
                    "yearly_budget", project_data.get("annualBudget", [])
                ),
                "cost_overruns": project_data.get(
                    "cost_overruns", project_data.get("budget_overruns", {})
                ),
                "reports": project_data.get(
                    "reports", project_data.get("project_reports", [])
                ),
                "verification_documents": project_data.get(
                    "documents", project_data.get("verification_docs", [])
                ),
                "photos": project_data.get("photos", project_data.get("images", [])),
                "contractor_change_log": project_data.get(
                    "contractors", project_data.get("contractor_log", [])
                ),
                "last_updated": datetime.now().isoformat(),
                "source": "ADB (Asian Development Bank)",
                "source_api": "ADB Data API (JSON)",
            }

            # Only return if there's a valid title
            if normalized_project["title"]:
                return normalized_project
            else:
                logger.debug(f"Skipping project with no title: {project_data}")
                return None
        except Exception as e:
            logger.error(f"Error normalizing ADB JSON project: {e}")
            logger.debug(f"Problematic project data: {project_data}")
            return None

    def _extract_projects_from_json_api(
        self, json_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract project data from ADB JSON API response.

        Args:
            json_data: Parsed JSON response from ADB API

        Returns:
            List of project data dictionaries in standard format
        """
        projects = []

        # The API response seems to be a dataset descriptor, not individual projects
        # Let's look for actual project data within the response
        if "data" in json_data:
            # This appears to be a dataset description, not individual projects
            # Let's check for related links or dataset resources that might contain projects
            dataset_data = json_data["data"]
            attributes = dataset_data.get("attributes", {})

            # For now, we'll create a placeholder to indicate we found the dataset
            # In a real implementation, you'd need to find the actual project endpoint
            project = {
                "project_id": dataset_data.get("id", "dataset-info"),
                "title": attributes.get("title", "ADB Projects in Nepal"),
                "description": attributes.get("body", {}).get(
                    "summary", attributes.get("body", {}).get("value", "")
                ),
                "implementing_agency": "Asian Development Bank",
                "start_date": attributes.get("field_publish_date", ""),
                "end_date": attributes.get("changed", ""),
                "location": {
                    "country": "Nepal",
                    "country_code": "NP",
                    "region": "South Asia",
                    "province": "",
                    "district": "",
                    "municipality": "",
                },
                "funding_source": "Asian Development Bank",
                "total_allocated_budget": "",
                "real_time_spending": "",
                "loan_amount": "",
                "grant_amount": "",
                "physical_progress": "",
                "financial_progress": "",
                "borrower": "",
                "sector": "",
                "major_theme": "",
                "environmental_category": "",
                "implementation_status": "Active",
                "url": (
                    f"https://data.adb.org/dataset/{dataset_data.get('id', '')}"
                    if "id" in dataset_data
                    else ""
                ),
                "project_document_url": "",
                "milestones": [],
                "yearly_budget_breakdown": [],
                "cost_overruns": {},
                "reports": [],
                "verification_documents": [],
                "photos": [],
                "contractor_change_log": [],
                "last_updated": datetime.now().isoformat(),
                "source": "ADB (Asian Development Bank)",
                "source_api": "ADB Data API (JSON)",
            }
            projects.append(project)

        # If we get actual projects, we'll add them to the list
        # In a real implementation, you'd need to call another endpoint to get actual projects
        return projects

    async def _load_from_local_file(self) -> List[Dict[str, Any]]:
        """Load projects from the local all_projects.xml file as a fallback.

        Returns:
            List of project data dictionaries
        """
        try:
            # Try to locate the all_projects.xml file
            local_paths = [
                "sample_projects.xml",  # Sample file with properly formatted XML - in same directory as script
                "all_projects_fixed_comprehensive.xml",  # Most comprehensive fix
                "all_projects_fixed.xml",  # Fixed version
                "all_projects.xml",  # Original file
                "../asian_development_bank/sample_projects.xml",  # Sample one level up (relative to project root)
                "../asian_development_bank/all_projects_fixed.xml",  # One level up fixed version
                "../asian_development_bank/all_projects.xml",  # One level up
                "migrations/007-source-projects/asian_development_bank/all_projects.xml",  # Full path relative to project
                "migrations/007-source-projects/asian_development_bank/all_projects_fixed.xml",  # Full path fixed version
                "migrations/007-source-projects/asian_development_bank/sample_projects.xml",  # Full path sample
                "/Users/interstellarninja/Documents/projects/nyc/Nepal-Development-Project-Service/migrations/007-source-projects/asian_development_bank/all_projects.xml",
                "/Users/interstellarninja/Documents/projects/nyc/Nepal-Development-Project-Service/migrations/007-source-projects/asian_development_bank/all_projects_fixed.xml",
                "/Users/interstellarninja/Documents/projects/nyc/Nepal-Development-Project-Service/migrations/007-source-projects/asian_development_bank/sample_projects.xml",
            ]

            xml_data = None
            file_path = None

            for path in local_paths:
                try:
                    abs_path = os.path.join(os.path.dirname(__file__), path)
                    if os.path.exists(abs_path):
                        file_path = abs_path
                        with open(abs_path, "r", encoding="utf-8") as f:
                            xml_data = f.read()
                        logger.info(f"Loaded data from local file: {file_path}")
                        break
                except Exception as e:
                    logger.debug(f"Could not load from {path}: {e}")
                    continue

            if xml_data is None:
                logger.error(
                    "Could not find all_projects.xml in any of the expected locations"
                )
                return []

            # Parse the XML data with error handling
            try:
                activities = parse_iati_xml(xml_data)
            except Exception as parse_error:
                logger.error(f"Error parsing XML: {parse_error}")
                # Try to fix common XML issues and re-parse
                xml_data = self._fix_common_xml_issues(xml_data)
                try:
                    activities = parse_iati_xml(xml_data)
                    logger.info("Successfully re-parsed XML after fixing common issues")
                except Exception as second_parse_error:
                    logger.error(
                        f"Still unable to parse XML after fixing common issues: {second_parse_error}"
                    )
                    return []

            # Transform to the standard format
            transformed_projects = [
                self._normalize_adb_project(activity) for activity in activities
            ]
            # Filter out any None values
            transformed_projects = [p for p in transformed_projects if p is not None]

            logger.info(f"Loaded {len(transformed_projects)} projects from local file")
            return transformed_projects

        except Exception as e:
            logger.error(f"Error loading from local file: {e}")
            return []

    def _fix_common_xml_issues(self, xml_content: str) -> str:
        """Fix common XML issues like unescaped ampersands, less-than, and greater-than signs."""
        import re

        # Use a proper XML content tokenizer to handle tags vs text content
        # This splits the content into XML tags and the text between them
        parts = []
        last_end = 0

        # Find all XML tags and process the content between them
        for match in re.finditer(r"(<[^>]*>)", xml_content):
            # Add the text content before this tag
            text_before = xml_content[last_end : match.start()]
            if text_before:
                # Process text content, escaping <, >, and & characters properly
                processed_text = self._escape_text_content(text_before)
                parts.append(processed_text)

            # Add the tag as-is
            parts.append(match.group(1))
            last_end = match.end()

        # Add any remaining content after the last tag
        remaining = xml_content[last_end:]
        if remaining:
            processed_text = self._escape_text_content(remaining)
            parts.append(processed_text)

        return "".join(parts)

    def _escape_text_content(self, text_content: str) -> str:
        """Escape XML special characters in text content while preserving existing entities."""
        # Handle the text content carefully to avoid double-escaping

        # First, temporarily substitute existing valid XML entities
        # This prevents double-encoding when processing
        text_content = text_content.replace("&amp;", "___AMP___")
        text_content = text_content.replace("&lt;", "___LT___")
        text_content = text_content.replace("&gt;", "___GT___")
        text_content = text_content.replace("&quot;", "___QUOT___")
        text_content = text_content.replace("&apos;", "___APOS___")

        # Now escape the special characters
        # First escape ampersands (this is the most complex one)
        # Replace unescaped & with &amp; (only ones not followed by valid entity names)
        text_content = re.sub(
            r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", text_content
        )

        # Then escape < and >
        text_content = text_content.replace("<", "&lt;")
        text_content = text_content.replace(">", "&gt;")

        # Restore the original entities
        text_content = text_content.replace("___AMP___", "&amp;")
        text_content = text_content.replace("___LT___", "&lt;")
        text_content = text_content.replace("___GT___", "&gt;")
        text_content = text_content.replace("___QUOT___", "&quot;")
        text_content = text_content.replace("___APOS___", "&apos;")

        return text_content

    def _normalize_adb_project(
        self, project_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Normalize ADB project to match nes.core.models.project.Project schema.

        Uses the new FinancingCommitment format with donor at top level.

        Args:
            project_data: Raw project data from ADB IATI XML

        Returns:
            Normalized project data compatible with Project model, or None if invalid
        """
        try:
            # --- Extract IATI identifier ---
            iati_identifier = project_data.get("iati_identifier") or ""
            if not iati_identifier:
                other_ids = project_data.get("other_identifiers", [])
                if other_ids and isinstance(other_ids, list) and other_ids[0]:
                    iati_identifier = other_ids[0].get("ref", "")

            # --- Extract title ---
            title = (project_data.get("title") or iati_identifier or "").strip()
            if not title:
                logger.debug(f"Skipping project with no title: {project_data}")
                return None

            # --- Generate slug ---
            # Use IATI identifier or create from title
            if iati_identifier:
                # Clean IATI identifier for slug (e.g., XM-DAC-46004-001 -> adb-XM-DAC-46004-001)
                slug = f"adb-{iati_identifier}"
            else:
                # Fallback: create slug from title
                slug_base = title.lower()[:50].replace(" ", "-")
                slug_base = re.sub(r"[^a-z0-9-]", "", slug_base)
                slug = f"adb-{slug_base}"

            # --- Extract description ---
            description = project_data.get("description") or title

            # --- Map status to ProjectStage ---
            status_code = project_data.get("activity_status", "")
            stage = self._map_iati_status_to_stage(status_code)

            # --- Extract agencies from participating organizations ---
            participating_orgs = project_data.get("participating_orgs", [])
            implementing_agency = None
            executing_agency = None
            development_agencies = []

            for org in participating_orgs:
                role = str(org.get("role", "")).upper()
                name = org.get("name") or org.get("ref") or ""
                if not name:
                    continue

                # IATI role codes: 1=Funding, 2=Accountable, 3=Extending, 4=Implementing
                if role in ["4", "IMPLEMENTING"]:
                    implementing_agency = name
                elif role in ["3", "EXTENDING", "2", "ACCOUNTABLE"]:
                    executing_agency = name
                elif role in ["1", "FUNDING"]:
                    development_agencies.append(name)

            # Fallback: use first non-ADB org as implementing agency
            if not implementing_agency:
                for org in participating_orgs:
                    name = org.get("name") or org.get("ref") or ""
                    if name and "asian development bank" not in name.lower():
                        implementing_agency = name
                        break

            # --- Extract dates ---
            dates = []
            activity_dates = project_data.get("activity_dates", [])
            approval_date = None

            for date_info in activity_dates:
                date_type = str(date_info.get("type", ""))
                iso_date = date_info.get("iso_date", "")
                if not iso_date:
                    continue

                # IATI date type codes:
                # 1=Planned start, 2=Actual start, 3=Planned end, 4=Actual end
                if date_type in ["1", "2"]:
                    dates.append(
                        {
                            "date": iso_date,
                            "type": "START",
                            "source": "ADB",
                        }
                    )
                    if date_type == "2":  # Actual start often indicates approval
                        approval_date = iso_date
                elif date_type in ["3", "4"]:
                    dates.append(
                        {
                            "date": iso_date,
                            "type": "CLOSING",
                            "source": "ADB",
                        }
                    )

            # --- Extract financing (new FinancingCommitment format) ---
            financing = []
            currency = project_data.get("default_currency") or "USD"

            # ADB IATI typically doesn't have detailed budget, but check transactions
            transactions = project_data.get("transactions", [])
            total_commitment_amt = 0.0
            total_disbursement_amt = 0.0

            for tx in transactions:
                tx_type = str(tx.get("type", "")).lower()
                value = tx.get("value")
                if not value:
                    continue

                try:
                    amount = float(value)
                except (ValueError, TypeError):
                    continue

                # IATI transaction types: 2=Commitment, 3=Disbursement, 4=Expenditure
                if "commitment" in tx_type or tx_type == "2":
                    total_commitment_amt += amount
                elif "disbursement" in tx_type or tx_type in ["3", "4"]:
                    total_disbursement_amt += amount

            # Create financing commitment entry
            if total_commitment_amt > 0:
                financing.append(
                    {
                        "donor": "Asian Development Bank",
                        "amount": total_commitment_amt,
                        "currency": currency,
                        "assistance_type": "loan",  # ADB primarily provides loans
                        "financing_instrument": "ADB Loan",
                        "budget_type": "on_budget",
                        "terms": None,
                        "transaction_date": approval_date,
                        "transaction_type": "commitment",
                        "is_actual": True,
                        "source": "ADB",
                    }
                )

            # --- Extract sectors ---
            sectors = []
            raw_sectors = project_data.get("sectors", [])
            for sector in raw_sectors:
                code = sector.get("code", "")
                vocabulary = sector.get("vocabulary", "")
                if code:
                    sectors.append(
                        {
                            "normalized_sector": None,
                            "donor_sector": (
                                f"{vocabulary}:{code}" if vocabulary else code
                            ),
                            "donor_subsector": None,
                            "donor": "Asian Development Bank",
                            "percentage": None,
                        }
                    )

            # --- Extract tags from policy markers ---
            tags = []
            policy_markers = project_data.get("policy_markers", [])
            for marker in policy_markers:
                code = marker.get("code", "")
                narrative = marker.get("narrative", "")
                marker_text = (narrative or code).lower()

                if any(w in marker_text for w in ["climate", "environment", "green"]):
                    tags.append(
                        {
                            "category": "CLIMATE",
                            "normalized_tag": None,
                            "donor_tag": narrative or code,
                            "donor": "Asian Development Bank",
                        }
                    )
                elif any(w in marker_text for w in ["gender", "women"]):
                    tags.append(
                        {
                            "category": "GENDER",
                            "normalized_tag": None,
                            "donor_tag": narrative or code,
                            "donor": "Asian Development Bank",
                        }
                    )
                elif any(w in marker_text for w in ["governance", "institution"]):
                    tags.append(
                        {
                            "category": "GOVERNANCE",
                            "normalized_tag": None,
                            "donor_tag": narrative or code,
                            "donor": "Asian Development Bank",
                        }
                    )

            # --- Build donor extension ---
            donor_extensions = [
                {
                    "donor": "ADB",
                    "donor_project_id": iati_identifier,
                    "raw_payload": {
                        "iati_identifier": iati_identifier,
                        "activity_status": status_code,
                        "default_currency": currency,
                        "hierarchy": project_data.get("hierarchy"),
                        "last_updated": project_data.get("last_updated"),
                        "reporting_org_ref": project_data.get("reporting_org_ref"),
                        "recipient_country": project_data.get("recipient_country"),
                        "locations": project_data.get("locations", []),
                        "contact": project_data.get("contact"),
                    },
                }
            ]

            # --- Build project URL ---
            # ADB project URLs use numeric IDs, not IATI identifiers
            # Extract numeric ID if present in IATI identifier (e.g., XM-DAC-46004-001)
            project_url = None
            if iati_identifier:
                # Try to extract numeric project ID from IATI identifier
                parts = iati_identifier.split("-")
                if len(parts) >= 4 and parts[-1].isdigit():
                    project_url = f"https://www.adb.org/projects/{parts[-1]}"

            # --- Build normalized project ---
            normalized_project = {
                # Entity fields
                "slug": slug,
                "names": [{"en": {"full": title}}],
                "description": description,
                # Project-specific fields
                "stage": stage,
                "implementing_agency": implementing_agency,
                "executing_agency": executing_agency,
                # Financing (new FinancingCommitment format)
                "financing": financing if financing else None,
                "total_commitment": (
                    total_commitment_amt if total_commitment_amt > 0 else None
                ),
                "total_disbursement": (
                    total_disbursement_amt if total_disbursement_amt > 0 else None
                ),
                # Timeline
                "dates": dates if dates else None,
                # Classification
                "sectors": sectors if sectors else None,
                "tags": tags if tags else None,
                # Donor extensions
                "donor_extensions": donor_extensions,
                # URL
                "project_url": project_url,
                # Migration metadata (for relationship creation)
                "_migration_metadata": {
                    "adb_project_id": iati_identifier,
                    "implementing_agencies": (
                        [implementing_agency] if implementing_agency else []
                    ),
                    "executing_agencies": (
                        [executing_agency] if executing_agency else []
                    ),
                    "development_agencies": development_agencies,
                    "locations": project_data.get("locations", []),
                },
            }

            return normalized_project

        except Exception as e:
            logger.error(f"Error normalizing ADB project: {e}")
            logger.debug(f"Problematic project data: {project_data}")
            return None

    def _map_iati_status_to_stage(self, status_code: str) -> str:
        """Map IATI activity status code to ProjectStage enum value.

        IATI status codes:
        1 = Pipeline/identification
        2 = Implementation
        3 = Completion
        4 = Post-completion
        5 = Cancelled
        6 = Suspended
        """
        mapping = {
            "1": "pipeline",
            "2": "ongoing",
            "3": "completed",
            "4": "completed",
            "5": "cancelled",
            "6": "suspended",
        }
        return mapping.get(str(status_code), "unknown")


async def scrape_and_save_adb_projects(output_file: str = "adb_projects.jsonl") -> int:
    """Scrape ADB projects and save to a JSONL file.

    Args:
        output_file: Name of the output file (JSONL format)

    Returns:
        Number of projects scraped and saved
    """
    logger.info("Starting ADB project scraping...")

    # Define the source directory
    project_root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    source_dir = os.path.join(
        project_root, "migrations", "007-source-projects", "source"
    )
    os.makedirs(source_dir, exist_ok=True)

    # Create the full output path
    output_path = os.path.join(source_dir, output_file)

    scraper = ADBProjectScraper()
    projects = await scraper.search_adb_projects()

    # Save projects to JSONL file (one JSON object per line)
    with open(output_path, "w", encoding="utf-8") as f:
        for project in projects:
            f.write(json.dumps(project, ensure_ascii=False, default=str) + "\n")

    logger.info(f"Saved {len(projects)} ADB projects to {output_path}")
    return len(projects)


if __name__ == "__main__":
    # For development and testing
    async def main():
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        logger.info("Running ADB project scraper/transformer...")

        # Scrape and save projects
        count = await scrape_and_save_adb_projects()
        logger.info(f"Completed scraping/transformation. Total projects: {count}")

    # Run the scraper
    asyncio.run(main())

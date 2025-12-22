"""
JICA (Japan International Cooperation Agency) Data Scraper for Nepal Development Projects.

This module provides functionality to transform project data from JICA's loan database
for projects related to Nepal. It follows the existing architecture patterns in the nes 
project and transforms JICA data to match the standardized project schema used by other sources.
"""

import asyncio
import csv
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

from nes.services.scraping.web_scraper import RateLimiter, RetryHandler

# Configure logging
logger = logging.getLogger(__name__)


class JICAAPIClient:
    """HTTP client for JICA data access with rate limiting and retry logic."""

    def __init__(
        self,
        requests_per_second: float = 0.5,  # Conservative rate limit
        requests_per_minute: int = 30,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """Initialize the JICA API client.

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
                "Accept": "application/json, text/html, */*",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _make_request(
        self, url: str, params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make a request to the JICA API endpoint with rate limiting and error handling.

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
        await self.rate_limiter.acquire("jica.go.jp")

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
                "Accept": "application/json, text/html, */*",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }

            async with self.session.get(full_url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
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


class JICAProjectScraper:
    """Scraper for JICA (Japan International Cooperation Agency) projects in Nepal."""

    def __init__(self, client: Optional[JICAAPIClient] = None):
        """Initialize the JICA project scraper.

        Args:
            client: JICAAPIClient instance. If None, a default client will be created
        """
        self.client = client or JICAAPIClient()

    async def search_jica_projects(self) -> List[Dict[str, Any]]:
        """Search for JICA projects related to Nepal.

        Returns:
            List of project data dictionaries
        """
        async with self.client:
            projects = await self._load_jica_projects_from_csv()
            logger.info(
                f"Successfully loaded and transformed {len(projects)} projects from JICA"
            )
            return projects

    async def _load_jica_projects_from_csv(self) -> List[Dict[str, Any]]:
        """Load JICA projects from the existing CSV file.

        Returns:
            List of project data dictionaries
        """
        try:
            # Try to locate the yen_loan.csv file
            local_paths = [
                "yen_loan.csv",  # Relative to current script
                "../jica/yen_loan.csv",  # One level up
                "migrations/007-source-projects/jica/yen_loan.csv",  # Full path relative to project
                "/Users/interstellarninja/Documents/projects/nyc/Nepal-Development-Project-Service/migrations/007-source-projects/jica/yen_loan.csv",
            ]

            csv_data = None
            file_path = None

            for path in local_paths:
                try:
                    abs_path = os.path.join(os.path.dirname(__file__), path)
                    if os.path.exists(abs_path):
                        file_path = abs_path
                        with open(abs_path, "r", encoding="utf-8") as f:
                            csv_content = f.read()
                        logger.info(f"Loaded data from local CSV file: {file_path}")

                        # Parse the CSV content
                        lines = csv_content.strip().split("\n")
                        reader = csv.DictReader(lines)
                        csv_data = [dict(row) for row in reader]
                        break
                except Exception as e:
                    logger.debug(f"Could not load from {path}: {e}")
                    continue

            if csv_data is None:
                logger.error(
                    "Could not find yen_loan.csv in any of the expected locations"
                )
                return []

            # Transform CSV data to normalized projects
            transformed_projects = []
            for row in csv_data:
                # Skip summary row
                if row.get("No", "").strip() == "":
                    continue

                normalized = self._normalize_jica_project(row)
                if normalized:
                    transformed_projects.append(normalized)

            # Filter out any None values
            transformed_projects = [p for p in transformed_projects if p is not None]
            logger.info(
                f"Successfully transformed {len(transformed_projects)} JICA projects from CSV data"
            )
            return transformed_projects

        except Exception as e:
            logger.error(f"Error loading from CSV file: {e}")
            return []

    def _normalize_jica_project(
        self, project_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Normalize JICA project to match nes.core.models.project.Project schema.

        Uses the new FinancingCommitment format with donor at top level.

        Args:
            project_data: Raw project data from JICA CSV

        Returns:
            Normalized project data compatible with Project model, or None if invalid
        """
        try:
            import re

            # --- Extract title ---
            title = project_data.get("project name", "").strip()
            if not title:
                logger.debug(f"Skipping project with no title: {project_data}")
                return None

            # --- Generate slug and project ID ---
            approval_date = project_data.get(
                "Date of approval(year/month/day)", ""
            ).strip()
            clean_name = re.sub(r"[^\w\s-]", "", title).lower().replace(" ", "-")[:50]
            date_suffix = approval_date.replace("-", "") if approval_date else "unknown"
            slug = f"jica-{clean_name}-{date_suffix}"
            jica_project_id = f"JICA-{date_suffix}-{clean_name[:30]}"

            # --- Extract description ---
            sector = project_data.get("sector", "")
            subsector = project_data.get("subsector", "")
            description = f"JICA Yen Loan project: {title}"
            if sector:
                description += f". Sector: {sector}"
            if subsector:
                description += f". Subsector: {subsector}"

            # --- Extract executing agency ---
            executing_agency = (
                project_data.get("Executing agency", "")
                or project_data.get("executing_agency", "")
                or None
            )

            # --- Extract dates ---
            dates = []
            if approval_date:
                dates.append(
                    {
                        "date": approval_date,
                        "type": "APPROVAL",
                        "source": "JICA",
                    }
                )

            # --- Extract financing (new FinancingCommitment format) ---
            financing = []
            loan_amount_str = project_data.get("Amount of approval(millions; jpy)", "")

            # Parse loan amount (in millions JPY)
            loan_amount = None
            if loan_amount_str:
                try:
                    loan_amount = float(loan_amount_str) * 1_000_000  # Convert to JPY
                except (ValueError, TypeError):
                    pass

            # Determine financing instrument
            special_loan = project_data.get("Special yen (ODA) loan / STEP", "").strip()
            if special_loan:
                financing_instrument = f"JICA {special_loan}"
            else:
                financing_instrument = "JICA Yen Loan"

            # Parse loan terms for main portion
            def parse_float(val):
                try:
                    return float(val) if val else None
                except (ValueError, TypeError):
                    return None

            def parse_int(val):
                try:
                    return int(float(val)) if val else None
                except (ValueError, TypeError):
                    return None

            main_terms = None
            main_interest = parse_float(
                project_data.get("Main portion Interest rate(%)", "")
            )
            main_repayment = parse_int(
                project_data.get("Main portion Repayment period(years)", "")
            )
            main_grace = parse_int(
                project_data.get("Main portion Grace period(years)", "")
            )
            main_tying = project_data.get("Main portion Tying status", "").strip()

            if any([main_interest, main_repayment, main_grace, main_tying]):
                main_terms = {
                    "interest_rate": main_interest,
                    "repayment_period_years": main_repayment,
                    "grace_period_years": main_grace,
                    "tying_status": main_tying if main_tying else None,
                }

            # Create main financing commitment
            if loan_amount:
                financing.append(
                    {
                        "donor": "Japan International Cooperation Agency",
                        "amount": loan_amount,
                        "currency": "JPY",
                        "assistance_type": "loan",
                        "financing_instrument": financing_instrument,
                        "budget_type": "on_budget",
                        "terms": main_terms,
                        "transaction_date": approval_date if approval_date else None,
                        "transaction_type": "commitment",
                        "is_actual": True,
                        "source": "JICA",
                    }
                )

            # Check for consulting portion (separate financing entry)
            consulting_interest = parse_float(
                project_data.get("Consulting portion Interest rate(%)", "")
            )
            consulting_repayment = parse_int(
                project_data.get("Consulting portion Repayment period(years)", "")
            )
            consulting_grace = parse_int(
                project_data.get("Consulting portion Grace period(years)", "")
            )
            consulting_tying = project_data.get(
                "Consulting portion Tying status", ""
            ).strip()

            if any(
                [
                    consulting_interest,
                    consulting_repayment,
                    consulting_grace,
                    consulting_tying,
                ]
            ):
                consulting_terms = {
                    "interest_rate": consulting_interest,
                    "repayment_period_years": consulting_repayment,
                    "grace_period_years": consulting_grace,
                    "tying_status": consulting_tying if consulting_tying else None,
                }
                # Note: Consulting portion amount not separately specified in CSV
                # We record the terms but not a separate amount
                financing.append(
                    {
                        "donor": "Japan International Cooperation Agency",
                        "amount": None,  # Consulting portion amount not specified
                        "currency": "JPY",
                        "assistance_type": "loan",
                        "financing_instrument": "JICA Consulting Portion",
                        "budget_type": "on_budget",
                        "terms": consulting_terms,
                        "transaction_date": approval_date if approval_date else None,
                        "transaction_type": "commitment",
                        "is_actual": True,
                        "source": "JICA",
                    }
                )

            # --- Extract sectors ---
            sectors = []
            if sector:
                sectors.append(
                    {
                        "normalized_sector": None,
                        "donor_sector": sector,
                        "donor_subsector": subsector if subsector else None,
                        "donor": "Japan International Cooperation Agency",
                        "percentage": None,
                    }
                )

            # --- Build donor extension ---
            donor_extensions = [
                {
                    "donor": "JICA",
                    "donor_project_id": jica_project_id,
                    "raw_payload": {
                        "no": project_data.get("No", ""),
                        "region": project_data.get("region", ""),
                        "country": project_data.get("country", ""),
                        "special_loan_type": special_loan,
                        "ex_ante_evaluation": project_data.get(
                            "ex-ante evaluation", ""
                        ),
                        "ex_post_evaluation": project_data.get(
                            "ex-post evaluation", ""
                        ),
                        "other_url": project_data.get("other url", ""),
                        "memo": project_data.get("Memo", ""),
                    },
                }
            ]

            # --- Build project URL ---
            project_url = project_data.get("project url", "").strip() or None

            # --- Build normalized project ---
            normalized_project = {
                # Entity fields
                "slug": slug,
                "names": [{"en": {"full": title}}],
                "description": description,
                # Project-specific fields
                "stage": "ongoing",  # JICA loans are typically ongoing
                "implementing_agency": None,  # Not specified in JICA data
                "executing_agency": executing_agency,
                # Financing (new FinancingCommitment format)
                "financing": financing if financing else None,
                "total_commitment": loan_amount,
                "total_disbursement": None,  # Not provided in JICA data
                # Timeline
                "dates": dates if dates else None,
                # Classification
                "sectors": sectors if sectors else None,
                "tags": None,  # Not provided in JICA data
                # Donor extensions
                "donor_extensions": donor_extensions,
                # URL
                "project_url": project_url,
                # Migration metadata (for relationship creation)
                "_migration_metadata": {
                    "jica_project_id": jica_project_id,
                    "implementing_agencies": [],
                    "executing_agencies": (
                        [executing_agency] if executing_agency else []
                    ),
                    "development_agencies": ["Japan International Cooperation Agency"],
                },
            }

            return normalized_project

        except Exception as e:
            logger.error(f"Error normalizing JICA project: {e}")
            logger.debug(f"Problematic project data: {project_data}")
            return None


async def scrape_and_save_jica_projects(
    output_file: str = "jica_projects.jsonl",
) -> int:
    """Scrape JICA projects and save to a JSONL file.

    Args:
        output_file: Name of the output file (JSONL format)

    Returns:
        Number of projects scraped and saved
    """
    logger.info("Starting JICA project transformation...")

    # Define the source directory
    project_root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    source_dir = os.path.join(
        project_root, "migrations", "007-source-projects", "source"
    )
    os.makedirs(source_dir, exist_ok=True)

    # Create the full output path
    output_path = os.path.join(source_dir, output_file)

    scraper = JICAProjectScraper()
    projects = await scraper.search_jica_projects()

    # Save projects to JSONL file (one JSON object per line)
    with open(output_path, "w", encoding="utf-8") as f:
        for project in projects:
            f.write(json.dumps(project, ensure_ascii=False, default=str) + "\n")

    logger.info(f"Saved {len(projects)} JICA projects to {output_path}")
    return len(projects)


if __name__ == "__main__":
    # For development and testing
    async def main():
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        logger.info("Running JICA project scraper/transformer...")

        # Scrape and save projects
        count = await scrape_and_save_jica_projects()
        logger.info(f"Completed scraping/transformation. Total projects: {count}")

    # Run the scraper
    asyncio.run(main())

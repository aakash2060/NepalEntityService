"""Authentic Nepali test data fixtures for comprehensive testing.

This module provides real Nepali entities including politicians, political parties,
government bodies, and administrative divisions for use in tests.
"""

from typing import Any, Dict, List

# Authentic Nepali Politicians
NEPALI_POLITICIANS = [
    {
        "slug": "pushpa-kamal-dahal",
        "names": {
            "en": {
                "full": "Pushpa Kamal Dahal",
                "given": "Pushpa Kamal",
                "family": "Dahal",
            },
            "ne": {"full": "पुष्पकमल दाहाल", "given": "पुष्पकमल", "family": "दाहाल"},
        },
        "aliases": [{"en": "Prachanda", "ne": "प्रचण्ड"}],
        "party": "nepal-communist-party-maoist-centre",
        "constituency": "Gorkha-2",
        "positions": ["Prime Minister", "Party Chairman"],
    },
    {
        "slug": "sher-bahadur-deuba",
        "names": {
            "en": {
                "full": "Sher Bahadur Deuba",
                "given": "Sher Bahadur",
                "family": "Deuba",
            },
            "ne": {"full": "शेरबहादुर देउवा", "given": "शेरबहादुर", "family": "देउवा"},
        },
        "party": "nepali-congress",
        "constituency": "Dadeldhura-1",
        "positions": ["Prime Minister", "Party President"],
    },
    {
        "slug": "khadga-prasad-oli",
        "names": {
            "en": {
                "full": "Khadga Prasad Sharma Oli",
                "given": "Khadga Prasad",
                "family": "Oli",
            },
            "ne": {"full": "खड्ग प्रसाद शर्मा ओली", "given": "खड्ग प्रसाद", "family": "ओली"},
        },
        "aliases": [{"en": "KP Sharma Oli", "ne": "के पी शर्मा ओली"}],
        "party": "cpn-uml",
        "constituency": "Jhapa-5",
        "positions": ["Prime Minister", "Party Chairman"],
    },
    {
        "slug": "ram-chandra-poudel",
        "names": {
            "en": {
                "full": "Ram Chandra Poudel",
                "given": "Ram Chandra",
                "family": "Poudel",
            },
            "ne": {"full": "राम चन्द्र पौडेल", "given": "राम चन्द्र", "family": "पौडेल"},
        },
        "party": "nepali-congress",
        "constituency": "Tanahun-1",
        "positions": ["President of Nepal", "Senior Leader"],
    },
    {
        "slug": "baburam-bhattarai",
        "names": {
            "en": {
                "full": "Baburam Bhattarai",
                "given": "Baburam",
                "family": "Bhattarai",
            },
            "ne": {"full": "बाबुराम भट्टराई", "given": "बाबुराम", "family": "भट्टराई"},
        },
        "party": "nepal-samajbadi-party",
        "constituency": "Gorkha-1",
        "positions": ["Prime Minister", "Finance Minister"],
    },
    {
        "slug": "bimalendra-nidhi",
        "names": {
            "en": {
                "full": "Bimalendra Nidhi",
                "given": "Bimalendra",
                "family": "Nidhi",
            },
            "ne": {"full": "विमलेन्द्र निधि", "given": "विमलेन्द्र", "family": "निधि"},
        },
        "party": "nepali-congress",
        "constituency": "Dhanusha-3",
        "positions": ["Deputy Prime Minister", "Minister"],
    },
    {
        "slug": "rabi-lamichhane",
        "names": {
            "en": {"full": "Rabi Lamichhane", "given": "Rabi", "family": "Lamichhane"},
            "ne": {"full": "रवि लामिछाने", "given": "रवि", "family": "लामिछाने"},
        },
        "party": "rastriya-swatantra-party",
        "constituency": "Chitwan-2",
        "positions": ["Home Minister", "Party President"],
    },
    {
        "slug": "agni-prasad-sapkota",
        "names": {
            "en": {
                "full": "Agni Prasad Sapkota",
                "given": "Agni Prasad",
                "family": "Sapkota",
            },
            "ne": {
                "full": "अग्नि प्रसाद सापकोटा",
                "given": "अग्नि प्रसाद",
                "family": "सापकोटा",
            },
        },
        "party": "nepal-communist-party-maoist-centre",
        "constituency": "Sindhupalchok-1",
        "positions": ["Speaker of House of Representatives"],
    },
]


# Authentic Nepali Political Parties
NEPALI_POLITICAL_PARTIES = [
    {
        "slug": "nepali-congress",
        "names": {"en": {"full": "Nepali Congress"}, "ne": {"full": "नेपाली कांग्रेस"}},
        "abbreviation": {"en": "NC", "ne": "ने.कां."},
        "founded": "1947",
        "ideology": ["Social Democracy", "Democratic Socialism"],
        "headquarters": "Sanepa, Lalitpur",
        "president": "Sher Bahadur Deuba",
    },
    {
        "slug": "cpn-uml",
        "names": {
            "en": {"full": "Communist Party of Nepal (Unified Marxist-Leninist)"},
            "ne": {"full": "नेपाल कम्युनिष्ट पार्टी (एकीकृत मार्क्सवादी-लेनिनवादी)"},
        },
        "abbreviation": {"en": "CPN-UML", "ne": "ने.क.पा. (एमाले)"},
        "founded": "1991",
        "ideology": ["Communism", "Marxism-Leninism"],
        "headquarters": "Dhumbarahi, Kathmandu",
        "chairman": "Khadga Prasad Sharma Oli",
    },
    {
        "slug": "nepal-communist-party-maoist-centre",
        "names": {
            "en": {"full": "Communist Party of Nepal (Maoist Centre)"},
            "ne": {"full": "नेपाल कम्युनिष्ट पार्टी (माओवादी केन्द्र)"},
        },
        "abbreviation": {"en": "CPN-MC", "ne": "ने.क.पा. (माओवादी केन्द्र)"},
        "founded": "2009",
        "ideology": ["Maoism", "Communism"],
        "headquarters": "Paris Danda, Kathmandu",
        "chairman": "Pushpa Kamal Dahal",
    },
    {
        "slug": "rastriya-swatantra-party",
        "names": {
            "en": {"full": "Rastriya Swatantra Party"},
            "ne": {"full": "राष्ट्रिय स्वतन्त्र पार्टी"},
        },
        "abbreviation": {"en": "RSP", "ne": "रा.स्व.पा."},
        "founded": "2022",
        "ideology": ["Good Governance", "Anti-Corruption"],
        "headquarters": "Kathmandu",
        "president": "Rabi Lamichhane",
    },
    {
        "slug": "nepal-samajbadi-party",
        "names": {
            "en": {"full": "Nepal Samajbadi Party"},
            "ne": {"full": "नेपाल समाजवादी पार्टी"},
        },
        "abbreviation": {"en": "NSP", "ne": "ने.स.पा."},
        "founded": "2020",
        "ideology": ["Socialism", "Federalism"],
        "headquarters": "Kathmandu",
        "chairman": "Baburam Bhattarai",
    },
    {
        "slug": "rastriya-prajatantra-party",
        "names": {
            "en": {"full": "Rastriya Prajatantra Party"},
            "ne": {"full": "राष्ट्रिय प्रजातन्त्र पार्टी"},
        },
        "abbreviation": {"en": "RPP", "ne": "रा.प्र.पा."},
        "founded": "1990",
        "ideology": ["Constitutional Monarchy", "Hindu State"],
        "headquarters": "Dhumbarahi, Kathmandu",
        "chairman": "Rajendra Lingden",
    },
]


# Nepali Provinces (7 provinces)
NEPALI_PROVINCES = [
    {
        "slug": "koshi-province",
        "names": {"en": {"full": "Koshi Province"}, "ne": {"full": "कोशी प्रदेश"}},
        "number": 1,
        "capital": "Biratnagar",
        "area_km2": 25905,
        "districts": [
            "Bhojpur",
            "Dhankuta",
            "Ilam",
            "Jhapa",
            "Khotang",
            "Morang",
            "Okhaldhunga",
            "Panchthar",
            "Sankhuwasabha",
            "Solukhumbu",
            "Sunsari",
            "Taplejung",
            "Terhathum",
            "Udayapur",
        ],
    },
    {
        "slug": "madhesh-province",
        "names": {"en": {"full": "Madhesh Province"}, "ne": {"full": "मधेश प्रदेश"}},
        "number": 2,
        "capital": "Janakpur",
        "area_km2": 9661,
        "districts": [
            "Bara",
            "Dhanusha",
            "Mahottari",
            "Parsa",
            "Rautahat",
            "Saptari",
            "Sarlahi",
            "Siraha",
        ],
    },
    {
        "slug": "bagmati-province",
        "names": {"en": {"full": "Bagmati Province"}, "ne": {"full": "बागमती प्रदेश"}},
        "number": 3,
        "capital": "Hetauda",
        "area_km2": 20300,
        "districts": [
            "Bhaktapur",
            "Chitwan",
            "Dhading",
            "Dolakha",
            "Kathmandu",
            "Kavrepalanchok",
            "Lalitpur",
            "Makwanpur",
            "Nuwakot",
            "Ramechhap",
            "Rasuwa",
            "Sindhuli",
            "Sindhupalchok",
        ],
    },
    {
        "slug": "gandaki-province",
        "names": {"en": {"full": "Gandaki Province"}, "ne": {"full": "गण्डकी प्रदेश"}},
        "number": 4,
        "capital": "Pokhara",
        "area_km2": 21504,
        "districts": [
            "Baglung",
            "Gorkha",
            "Kaski",
            "Lamjung",
            "Manang",
            "Mustang",
            "Myagdi",
            "Nawalpur",
            "Parbat",
            "Syangja",
            "Tanahun",
        ],
    },
    {
        "slug": "lumbini-province",
        "names": {"en": {"full": "Lumbini Province"}, "ne": {"full": "लुम्बिनी प्रदेश"}},
        "number": 5,
        "capital": "Deukhuri",
        "area_km2": 22288,
        "districts": [
            "Arghakhanchi",
            "Banke",
            "Bardiya",
            "Dang",
            "Gulmi",
            "Kapilvastu",
            "Nawalparasi West",
            "Palpa",
            "Pyuthan",
            "Rolpa",
            "Rukum East",
            "Rupandehi",
        ],
    },
    {
        "slug": "karnali-province",
        "names": {"en": {"full": "Karnali Province"}, "ne": {"full": "कर्णाली प्रदेश"}},
        "number": 6,
        "capital": "Birendranagar",
        "area_km2": 27984,
        "districts": [
            "Dailekh",
            "Dolpa",
            "Humla",
            "Jajarkot",
            "Jumla",
            "Kalikot",
            "Mugu",
            "Rukum West",
            "Salyan",
            "Surkhet",
        ],
    },
    {
        "slug": "sudurpashchim-province",
        "names": {
            "en": {"full": "Sudurpashchim Province"},
            "ne": {"full": "सुदूरपश्चिम प्रदेश"},
        },
        "number": 7,
        "capital": "Godawari",
        "area_km2": 19539,
        "districts": [
            "Achham",
            "Baitadi",
            "Bajhang",
            "Bajura",
            "Dadeldhura",
            "Darchula",
            "Doti",
            "Kailali",
            "Kanchanpur",
        ],
    },
]


# Major Nepali Districts (sample from different provinces)
NEPALI_DISTRICTS = [
    {
        "slug": "kathmandu-district",
        "names": {
            "en": {"full": "Kathmandu District"},
            "ne": {"full": "काठमाडौं जिल्ला"},
        },
        "province": "bagmati-province",
        "headquarters": "Kathmandu",
        "area_km2": 395,
    },
    {
        "slug": "lalitpur-district",
        "names": {"en": {"full": "Lalitpur District"}, "ne": {"full": "ललितपुर जिल्ला"}},
        "province": "bagmati-province",
        "headquarters": "Lalitpur",
        "area_km2": 385,
    },
    {
        "slug": "bhaktapur-district",
        "names": {"en": {"full": "Bhaktapur District"}, "ne": {"full": "भक्तपुर जिल्ला"}},
        "province": "bagmati-province",
        "headquarters": "Bhaktapur",
        "area_km2": 119,
    },
    {
        "slug": "morang-district",
        "names": {"en": {"full": "Morang District"}, "ne": {"full": "मोरङ जिल्ला"}},
        "province": "koshi-province",
        "headquarters": "Biratnagar",
        "area_km2": 1855,
    },
    {
        "slug": "kaski-district",
        "names": {"en": {"full": "Kaski District"}, "ne": {"full": "कास्की जिल्ला"}},
        "province": "gandaki-province",
        "headquarters": "Pokhara",
        "area_km2": 2017,
    },
]


# Nepali Municipalities (Metropolitan Cities, Sub-Metropolitan Cities, Municipalities)
NEPALI_MUNICIPALITIES = [
    {
        "slug": "kathmandu-metropolitan-city",
        "names": {
            "en": {"full": "Kathmandu Metropolitan City"},
            "ne": {"full": "काठमाडौं महानगरपालिका"},
        },
        "type": "metropolitan_city",
        "district": "kathmandu-district",
        "province": "bagmati-province",
        "wards": 32,
    },
    {
        "slug": "pokhara-metropolitan-city",
        "names": {
            "en": {"full": "Pokhara Metropolitan City"},
            "ne": {"full": "पोखरा महानगरपालिका"},
        },
        "type": "metropolitan_city",
        "district": "kaski-district",
        "province": "gandaki-province",
        "wards": 33,
    },
    {
        "slug": "lalitpur-metropolitan-city",
        "names": {
            "en": {"full": "Lalitpur Metropolitan City"},
            "ne": {"full": "ललितपुर महानगरपालिका"},
        },
        "type": "metropolitan_city",
        "district": "lalitpur-district",
        "province": "bagmati-province",
        "wards": 29,
    },
    {
        "slug": "bharatpur-metropolitan-city",
        "names": {
            "en": {"full": "Bharatpur Metropolitan City"},
            "ne": {"full": "भरतपुर महानगरपालिका"},
        },
        "type": "metropolitan_city",
        "district": "chitwan-district",
        "province": "bagmati-province",
        "wards": 29,
    },
    {
        "slug": "biratnagar-metropolitan-city",
        "names": {
            "en": {"full": "Biratnagar Metropolitan City"},
            "ne": {"full": "विराटनगर महानगरपालिका"},
        },
        "type": "metropolitan_city",
        "district": "morang-district",
        "province": "koshi-province",
        "wards": 19,
    },
    {
        "slug": "dharan-sub-metropolitan-city",
        "names": {
            "en": {"full": "Dharan Sub-Metropolitan City"},
            "ne": {"full": "धरान उपमहानगरपालिका"},
        },
        "type": "sub_metropolitan_city",
        "district": "sunsari-district",
        "province": "koshi-province",
        "wards": 20,
    },
    {
        "slug": "butwal-sub-metropolitan-city",
        "names": {
            "en": {"full": "Butwal Sub-Metropolitan City"},
            "ne": {"full": "बुटवल उपमहानगरपालिका"},
        },
        "type": "sub_metropolitan_city",
        "district": "rupandehi-district",
        "province": "lumbini-province",
        "wards": 19,
    },
]


# Nepali Government Bodies
NEPALI_GOVERNMENT_BODIES = [
    {
        "slug": "office-of-president",
        "names": {
            "en": {"full": "Office of the President"},
            "ne": {"full": "राष्ट्रपति कार्यालय"},
        },
        "type": "constitutional_office",
        "location": "Shital Niwas, Kathmandu",
    },
    {
        "slug": "office-of-prime-minister",
        "names": {
            "en": {"full": "Office of the Prime Minister and Council of Ministers"},
            "ne": {"full": "प्रधानमन्त्री तथा मन्त्रिपरिषद्को कार्यालय"},
        },
        "type": "executive_office",
        "location": "Singha Durbar, Kathmandu",
    },
    {
        "slug": "supreme-court-nepal",
        "names": {
            "en": {"full": "Supreme Court of Nepal"},
            "ne": {"full": "नेपालको सर्वोच्च अदालत"},
        },
        "type": "judiciary",
        "location": "Ramshah Path, Kathmandu",
    },
    {
        "slug": "election-commission-nepal",
        "names": {
            "en": {"full": "Election Commission of Nepal"},
            "ne": {"full": "निर्वाचन आयोग नेपाल"},
        },
        "type": "constitutional_body",
        "location": "Kantipath, Kathmandu",
    },
    {
        "slug": "ministry-of-home-affairs",
        "names": {
            "en": {"full": "Ministry of Home Affairs"},
            "ne": {"full": "गृह मन्त्रालय"},
        },
        "type": "ministry",
        "location": "Singha Durbar, Kathmandu",
    },
    {
        "slug": "ministry-of-foreign-affairs",
        "names": {
            "en": {"full": "Ministry of Foreign Affairs"},
            "ne": {"full": "परराष्ट्र मन्त्रालय"},
        },
        "type": "ministry",
        "location": "Singha Durbar, Kathmandu",
    },
    {
        "slug": "ministry-of-finance",
        "names": {"en": {"full": "Ministry of Finance"}, "ne": {"full": "अर्थ मन्त्रालय"}},
        "type": "ministry",
        "location": "Singha Durbar, Kathmandu",
    },
    {
        "slug": "national-planning-commission",
        "names": {
            "en": {"full": "National Planning Commission"},
            "ne": {"full": "राष्ट्रिय योजना आयोग"},
        },
        "type": "planning_body",
        "location": "Singha Durbar, Kathmandu",
    },
]


# Electoral Constituencies (sample)
NEPALI_CONSTITUENCIES = [
    {
        "slug": "kathmandu-1",
        "names": {
            "en": {"full": "Kathmandu Constituency 1"},
            "ne": {"full": "काठमाडौं क्षेत्र नं. १"},
        },
        "district": "kathmandu-district",
        "type": "parliamentary_constituency",
    },
    {
        "slug": "lalitpur-3",
        "names": {
            "en": {"full": "Lalitpur Constituency 3"},
            "ne": {"full": "ललितपुर क्षेत्र नं. ३"},
        },
        "district": "lalitpur-district",
        "type": "parliamentary_constituency",
    },
    {
        "slug": "chitwan-2",
        "names": {
            "en": {"full": "Chitwan Constituency 2"},
            "ne": {"full": "चितवन क्षेत्र नं. २"},
        },
        "district": "chitwan-district",
        "type": "parliamentary_constituency",
    },
]


def get_politician_entity(slug: str) -> Dict[str, Any]:
    """Get a complete entity dict for a politician by slug."""
    politician = next((p for p in NEPALI_POLITICIANS if p["slug"] == slug), None)
    if not politician:
        raise ValueError(f"Politician with slug '{slug}' not found")

    # Generate tags from positions
    tags = ["politician"]  # All politicians get this tag
    for position in politician.get("positions", []):
        # Convert position to tag format (lowercase, hyphenated)
        if "President" in position:
            tags.append("president")
        if "Prime Minister" in position:
            tags.append("prime-minister")
        if "Senior Leader" in position:
            tags.append("senior-leader")
        if "Minister" in position and "Prime" not in position:
            tags.append("minister")
        if "Speaker" in position:
            tags.append("speaker")
        if "Chairman" in position:
            tags.append("party-leader")

    entity = {
        "slug": politician["slug"],
        "type": "person",
        "sub_type": "politician",
        "names": [
            {
                "kind": "PRIMARY",
                "en": politician["names"]["en"],
                "ne": politician["names"]["ne"],
            }
        ],
        "tags": tags,
        "attributes": {
            "party": politician["party"],
            "constituency": politician.get("constituency"),
            "positions": politician.get("positions", []),
        },
    }

    # Add aliases if present
    if "aliases" in politician:
        for alias in politician["aliases"]:
            entity["names"].append(
                {
                    "kind": "ALIAS",
                    "en": {"full": alias["en"]},
                    "ne": {"full": alias["ne"]},
                }
            )

    return entity


def get_party_entity(slug: str) -> Dict[str, Any]:
    """Get a complete entity dict for a political party by slug."""
    party = next((p for p in NEPALI_POLITICAL_PARTIES if p["slug"] == slug), None)
    if not party:
        raise ValueError(f"Party with slug '{slug}' not found")

    return {
        "slug": party["slug"],
        "type": "organization",
        "sub_type": "political_party",
        "names": [
            {"kind": "PRIMARY", "en": party["names"]["en"], "ne": party["names"]["ne"]}
        ],
        "attributes": {
            "abbreviation": party.get("abbreviation"),
            "founded": party.get("founded"),
            "ideology": party.get("ideology", []),
            "headquarters": party.get("headquarters"),
        },
    }


def get_location_entity(slug: str, location_type: str) -> Dict[str, Any]:
    """Get a complete entity dict for a location by slug and type."""
    if location_type == "province":
        locations = NEPALI_PROVINCES
    elif location_type == "district":
        locations = NEPALI_DISTRICTS
    elif location_type in [
        "metropolitan_city",
        "sub_metropolitan_city",
        "municipality",
    ]:
        locations = NEPALI_MUNICIPALITIES
    else:
        raise ValueError(f"Unknown location type: {location_type}")

    location = next((loc for loc in locations if loc["slug"] == slug), None)
    if not location:
        raise ValueError(f"Location with slug '{slug}' not found")

    entity = {
        "slug": location["slug"],
        "type": "location",
        "sub_type": location.get("type", location_type),
        "names": [
            {
                "kind": "PRIMARY",
                "en": location["names"]["en"],
                "ne": location["names"]["ne"],
            }
        ],
        "attributes": {},
    }

    # Add type-specific attributes
    if "province" in location:
        entity["attributes"]["province"] = location["province"]
    if "district" in location:
        entity["attributes"]["district"] = location["district"]
    if "capital" in location:
        entity["attributes"]["capital"] = location["capital"]
    if "area_km2" in location:
        entity["attributes"]["area_km2"] = location["area_km2"]
    if "wards" in location:
        entity["attributes"]["wards"] = location["wards"]

    return entity


def get_government_body_entity(slug: str) -> Dict[str, Any]:
    """Get a complete entity dict for a government body by slug."""
    body = next((b for b in NEPALI_GOVERNMENT_BODIES if b["slug"] == slug), None)
    if not body:
        raise ValueError(f"Government body with slug '{slug}' not found")

    return {
        "slug": body["slug"],
        "type": "organization",
        "sub_type": "government_body",
        "names": [
            {"kind": "PRIMARY", "en": body["names"]["en"], "ne": body["names"]["ne"]}
        ],
        "attributes": {"body_type": body.get("type"), "location": body.get("location")},
    }

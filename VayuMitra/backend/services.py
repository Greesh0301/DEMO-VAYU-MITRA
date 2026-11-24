import base64
import csv
import hashlib
import io
import json
import math
import os
import re
import secrets
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from config import Config, DATABASE_DIR, DATABASE_PATH, UPLOAD_FOLDER

WMO_WEATHER_LABELS = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    61: "Light Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    71: "Light Snow",
    73: "Moderate Snow",
    75: "Heavy Snow",
    80: "Light Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Hail",
    99: "Severe Thunderstorm",
}

COMMUNITY_CATEGORIES = [
    "Smoke and burning",
    "Construction dust",
    "Industrial emissions",
    "Garbage burning",
    "Vehicle-related pollution",
    "Other environmental issues",
]

LEGACY_CATEGORY_MAP = {
    "Garbage dumping": "Other environmental issues",
    "Open burning": "Smoke and burning",
    "Vehicle emissions": "Vehicle-related pollution",
    "Industrial smoke": "Industrial emissions",
    "Smoke emissions": "Smoke and burning",
    "Industrial pollution": "Industrial emissions",
    "Water pollution": "Other environmental issues",
}

REPORT_STATUSES = ["Submitted", "Under Review", "Verified", "Resolved", "Rejected"]

INDIA_BOUNDS = {
    "min_lat": 6.4,
    "max_lat": 37.6,
    "min_lon": 68.0,
    "max_lon": 97.5,
}

INDIA_STATES_DIRECTORY: List[Dict[str, Any]] = [
    {
        "state": "Andhra Pradesh",
        "type": "State",
        "capital": "Amaravati",
        "cities": [
            {"name": "Visakhapatnam", "latitude": 17.6868, "longitude": 83.2185},
            {"name": "Vijayawada", "latitude": 16.5062, "longitude": 80.6480},
            {"name": "Amaravati", "latitude": 16.5131, "longitude": 80.5165},
            {"name": "Tirupati", "latitude": 13.6288, "longitude": 79.4192},
            {"name": "Guntur", "latitude": 16.3067, "longitude": 80.4365},
        ],
    },
    {
        "state": "Arunachal Pradesh",
        "type": "State",
        "capital": "Itanagar",
        "cities": [
            {"name": "Itanagar", "latitude": 27.0844, "longitude": 93.6053},
            {"name": "Tawang", "latitude": 27.5860, "longitude": 91.8594},
            {"name": "Pasighat", "latitude": 28.0660, "longitude": 95.3264},
        ],
    },
    {
        "state": "Assam",
        "type": "State",
        "capital": "Dispur",
        "cities": [
            {"name": "Guwahati", "latitude": 26.1445, "longitude": 91.7362},
            {"name": "Dispur", "latitude": 26.1433, "longitude": 91.7898},
            {"name": "Silchar", "latitude": 24.8333, "longitude": 92.7789},
            {"name": "Dibrugarh", "latitude": 27.4728, "longitude": 94.9120},
            {"name": "Jorhat", "latitude": 26.7509, "longitude": 94.2037},
        ],
    },
    {
        "state": "Bihar",
        "type": "State",
        "capital": "Patna",
        "cities": [
            {"name": "Patna", "latitude": 25.5941, "longitude": 85.1376},
            {"name": "Gaya", "latitude": 24.7914, "longitude": 85.0002},
            {"name": "Muzaffarpur", "latitude": 26.1197, "longitude": 85.3910},
            {"name": "Bhagalpur", "latitude": 25.2425, "longitude": 86.9842},
        ],
    },
    {
        "state": "Chhattisgarh",
        "type": "State",
        "capital": "Raipur",
        "cities": [
            {"name": "Raipur", "latitude": 21.2514, "longitude": 81.6296},
            {"name": "Bilaspur", "latitude": 22.0797, "longitude": 82.1409},
            {"name": "Bhilai", "latitude": 21.1938, "longitude": 81.3509},
            {"name": "Jagdalpur", "latitude": 19.0748, "longitude": 82.0085},
        ],
    },
    {
        "state": "Goa",
        "type": "State",
        "capital": "Panaji",
        "cities": [
            {"name": "Panaji", "latitude": 15.4909, "longitude": 73.8278},
            {"name": "Margao", "latitude": 15.2832, "longitude": 73.9862},
            {"name": "Vasco da Gama", "latitude": 15.3982, "longitude": 73.8113},
        ],
    },
    {
        "state": "Gujarat",
        "type": "State",
        "capital": "Gandhinagar",
        "cities": [
            {"name": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714},
            {"name": "Gandhinagar", "latitude": 23.2156, "longitude": 72.6369},
            {"name": "Surat", "latitude": 21.1702, "longitude": 72.8311},
            {"name": "Vadodara", "latitude": 22.3072, "longitude": 73.1812},
            {"name": "Rajkot", "latitude": 22.3039, "longitude": 70.8022},
        ],
    },
    {
        "state": "Haryana",
        "type": "State",
        "capital": "Chandigarh",
        "cities": [
            {"name": "Gurugram", "latitude": 28.4595, "longitude": 77.0266},
            {"name": "Faridabad", "latitude": 28.4089, "longitude": 77.3178},
            {"name": "Panipat", "latitude": 29.3909, "longitude": 76.9635},
            {"name": "Ambala", "latitude": 30.3782, "longitude": 76.7767},
            {"name": "Hisar", "latitude": 29.1492, "longitude": 75.7217},
        ],
    },
    {
        "state": "Himachal Pradesh",
        "type": "State",
        "capital": "Shimla",
        "cities": [
            {"name": "Shimla", "latitude": 31.1048, "longitude": 77.1734},
            {"name": "Dharamshala", "latitude": 32.2190, "longitude": 76.3234},
            {"name": "Manali", "latitude": 32.2432, "longitude": 77.1892},
            {"name": "Solan", "latitude": 30.9045, "longitude": 77.0967},
        ],
    },
    {
        "state": "Jharkhand",
        "type": "State",
        "capital": "Ranchi",
        "cities": [
            {"name": "Ranchi", "latitude": 23.3441, "longitude": 85.3096},
            {"name": "Jamshedpur", "latitude": 22.8046, "longitude": 86.2029},
            {"name": "Dhanbad", "latitude": 23.7957, "longitude": 86.4304},
            {"name": "Bokaro", "latitude": 23.6693, "longitude": 86.1511},
        ],
    },
    {
        "state": "Karnataka",
        "type": "State",
        "capital": "Bengaluru",
        "cities": [
            {"name": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946},
            {"name": "Mysuru", "latitude": 12.2958, "longitude": 76.6394},
            {"name": "Mangaluru", "latitude": 12.9141, "longitude": 74.8560},
            {"name": "Hubballi", "latitude": 15.3647, "longitude": 75.1240},
            {"name": "Belagavi", "latitude": 15.8497, "longitude": 74.4977},
        ],
    },
    {
        "state": "Kerala",
        "type": "State",
        "capital": "Thiruvananthapuram",
        "cities": [
            {"name": "Thiruvananthapuram", "latitude": 8.5241, "longitude": 76.9366},
            {"name": "Kochi", "latitude": 9.9312, "longitude": 76.2673},
            {"name": "Kozhikode", "latitude": 11.2588, "longitude": 75.7804},
            {"name": "Thrissur", "latitude": 10.5276, "longitude": 76.2144},
        ],
    },
    {
        "state": "Madhya Pradesh",
        "type": "State",
        "capital": "Bhopal",
        "cities": [
            {"name": "Bhopal", "latitude": 23.2599, "longitude": 77.4126},
            {"name": "Indore", "latitude": 22.7196, "longitude": 75.8577},
            {"name": "Gwalior", "latitude": 26.2183, "longitude": 78.1828},
            {"name": "Jabalpur", "latitude": 23.1815, "longitude": 79.9864},
            {"name": "Ujjain", "latitude": 23.1765, "longitude": 75.7885},
        ],
    },
    {
        "state": "Maharashtra",
        "type": "State",
        "capital": "Mumbai",
        "cities": [
            {"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777},
            {"name": "Pune", "latitude": 18.5204, "longitude": 73.8567},
            {"name": "Nagpur", "latitude": 21.1458, "longitude": 79.0882},
            {"name": "Nashik", "latitude": 19.9975, "longitude": 73.7898},
            {"name": "Thane", "latitude": 19.2183, "longitude": 72.9781},
            {"name": "Navi Mumbai", "latitude": 19.0330, "longitude": 73.0297},
            {"name": "Chhatrapati Sambhajinagar", "latitude": 19.8762, "longitude": 75.3433},
        ],
    },
    {
        "state": "Manipur",
        "type": "State",
        "capital": "Imphal",
        "cities": [
            {"name": "Imphal", "latitude": 24.8170, "longitude": 93.9368},
            {"name": "Thoubal", "latitude": 24.6340, "longitude": 93.9856},
        ],
    },
    {
        "state": "Meghalaya",
        "type": "State",
        "capital": "Shillong",
        "cities": [
            {"name": "Shillong", "latitude": 25.5788, "longitude": 91.8933},
            {"name": "Tura", "latitude": 25.5141, "longitude": 90.2032},
        ],
    },
    {
        "state": "Mizoram",
        "type": "State",
        "capital": "Aizawl",
        "cities": [
            {"name": "Aizawl", "latitude": 23.7271, "longitude": 92.7176},
            {"name": "Lunglei", "latitude": 22.8883, "longitude": 92.7347},
        ],
    },
    {
        "state": "Nagaland",
        "type": "State",
        "capital": "Kohima",
        "cities": [
            {"name": "Kohima", "latitude": 25.6751, "longitude": 94.1086},
            {"name": "Dimapur", "latitude": 25.9091, "longitude": 93.7266},
        ],
    },
    {
        "state": "Odisha",
        "type": "State",
        "capital": "Bhubaneswar",
        "cities": [
            {"name": "Bhubaneswar", "latitude": 20.2961, "longitude": 85.8245},
            {"name": "Cuttack", "latitude": 20.4625, "longitude": 85.8830},
            {"name": "Rourkela", "latitude": 22.2604, "longitude": 84.8536},
            {"name": "Puri", "latitude": 19.8135, "longitude": 85.8312},
        ],
    },
    {
        "state": "Punjab",
        "type": "State",
        "capital": "Chandigarh",
        "cities": [
            {"name": "Ludhiana", "latitude": 30.9010, "longitude": 75.8573},
            {"name": "Amritsar", "latitude": 31.6340, "longitude": 74.8723},
            {"name": "Jalandhar", "latitude": 31.3260, "longitude": 75.5762},
            {"name": "Patiala", "latitude": 30.3398, "longitude": 76.3869},
        ],
    },
    {
        "state": "Rajasthan",
        "type": "State",
        "capital": "Jaipur",
        "cities": [
            {"name": "Jaipur", "latitude": 26.9124, "longitude": 75.7873},
            {"name": "Jodhpur", "latitude": 26.2389, "longitude": 73.0243},
            {"name": "Udaipur", "latitude": 24.5854, "longitude": 73.7125},
            {"name": "Kota", "latitude": 25.2138, "longitude": 75.8648},
            {"name": "Bikaner", "latitude": 28.0229, "longitude": 73.3119},
        ],
    },
    {
        "state": "Sikkim",
        "type": "State",
        "capital": "Gangtok",
        "cities": [
            {"name": "Gangtok", "latitude": 27.3389, "longitude": 88.6065},
            {"name": "Namchi", "latitude": 27.1667, "longitude": 88.3638},
        ],
    },
    {
        "state": "Tamil Nadu",
        "type": "State",
        "capital": "Chennai",
        "cities": [
            {"name": "Chennai", "latitude": 13.0827, "longitude": 80.2707},
            {"name": "Coimbatore", "latitude": 11.0168, "longitude": 76.9558},
            {"name": "Madurai", "latitude": 9.9252, "longitude": 78.1198},
            {"name": "Tiruchirappalli", "latitude": 10.7905, "longitude": 78.7047},
            {"name": "Salem", "latitude": 11.6643, "longitude": 78.1460},
        ],
    },
    {
        "state": "Telangana",
        "type": "State",
        "capital": "Hyderabad",
        "cities": [
            {"name": "Hyderabad", "latitude": 17.3850, "longitude": 78.4867},
            {"name": "Warangal", "latitude": 17.9689, "longitude": 79.5941},
            {"name": "Nizamabad", "latitude": 18.6725, "longitude": 78.0941},
            {"name": "Karimnagar", "latitude": 18.4386, "longitude": 79.1288},
        ],
    },
    {
        "state": "Tripura",
        "type": "State",
        "capital": "Agartala",
        "cities": [
            {"name": "Agartala", "latitude": 23.8315, "longitude": 91.2868},
            {"name": "Udaipur (Tripura)", "latitude": 23.5333, "longitude": 91.4833},
        ],
    },
    {
        "state": "Uttar Pradesh",
        "type": "State",
        "capital": "Lucknow",
        "cities": [
            {"name": "Lucknow", "latitude": 26.8467, "longitude": 80.9462},
            {"name": "Kanpur", "latitude": 26.4499, "longitude": 80.3319},
            {"name": "Varanasi", "latitude": 25.3176, "longitude": 82.9739},
            {"name": "Agra", "latitude": 27.1767, "longitude": 78.0081},
            {"name": "Noida", "latitude": 28.5355, "longitude": 77.3910},
            {"name": "Ghaziabad", "latitude": 28.6692, "longitude": 77.4538},
            {"name": "Prayagraj", "latitude": 25.4358, "longitude": 81.8463},
        ],
    },
    {
        "state": "Uttarakhand",
        "type": "State",
        "capital": "Dehradun",
        "cities": [
            {"name": "Dehradun", "latitude": 30.3165, "longitude": 78.0322},
            {"name": "Haridwar", "latitude": 29.9457, "longitude": 78.1642},
            {"name": "Rishikesh", "latitude": 30.0869, "longitude": 78.2676},
            {"name": "Nainital", "latitude": 29.3919, "longitude": 79.4542},
        ],
    },
    {
        "state": "West Bengal",
        "type": "State",
        "capital": "Kolkata",
        "cities": [
            {"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639},
            {"name": "Howrah", "latitude": 22.5958, "longitude": 88.2636},
            {"name": "Siliguri", "latitude": 26.7271, "longitude": 88.3953},
            {"name": "Durgapur", "latitude": 23.5204, "longitude": 87.3119},
            {"name": "Darjeeling", "latitude": 27.0410, "longitude": 88.2663},
        ],
    },
    {
        "state": "Andaman and Nicobar Islands",
        "type": "Union Territory",
        "capital": "Port Blair",
        "cities": [
            {"name": "Port Blair", "latitude": 11.6234, "longitude": 92.7265},
        ],
    },
    {
        "state": "Chandigarh",
        "type": "Union Territory",
        "capital": "Chandigarh",
        "cities": [
            {"name": "Chandigarh", "latitude": 30.7333, "longitude": 76.7794},
        ],
    },
    {
        "state": "Dadra and Nagar Haveli and Daman and Diu",
        "type": "Union Territory",
        "capital": "Daman",
        "cities": [
            {"name": "Daman", "latitude": 20.3974, "longitude": 72.8328},
            {"name": "Silvassa", "latitude": 20.2763, "longitude": 73.0083},
            {"name": "Diu", "latitude": 20.7144, "longitude": 70.9874},
        ],
    },
    {
        "state": "Delhi",
        "type": "Union Territory",
        "capital": "New Delhi",
        "cities": [
            {"name": "Delhi", "latitude": 28.6139, "longitude": 77.2090},
            {"name": "New Delhi", "latitude": 28.6139, "longitude": 77.2090},
        ],
    },
    {
        "state": "Jammu and Kashmir",
        "type": "Union Territory",
        "capital": "Srinagar",
        "cities": [
            {"name": "Srinagar", "latitude": 34.0837, "longitude": 74.7973},
            {"name": "Jammu", "latitude": 32.7266, "longitude": 74.8570},
            {"name": "Anantnag", "latitude": 33.7311, "longitude": 75.1487},
        ],
    },
    {
        "state": "Ladakh",
        "type": "Union Territory",
        "capital": "Leh",
        "cities": [
            {"name": "Leh", "latitude": 34.1526, "longitude": 77.5771},
            {"name": "Kargil", "latitude": 34.5539, "longitude": 76.1349},
        ],
    },
    {
        "state": "Lakshadweep",
        "type": "Union Territory",
        "capital": "Kavaratti",
        "cities": [
            {"name": "Kavaratti", "latitude": 10.5669, "longitude": 72.6420},
        ],
    },
    {
        "state": "Puducherry",
        "type": "Union Territory",
        "capital": "Puducherry",
        "cities": [
            {"name": "Puducherry", "latitude": 11.9416, "longitude": 79.8083},
            {"name": "Karaikal", "latitude": 10.9254, "longitude": 79.8380},
        ],
    },
]

KNOWN_CITY_COORDS: Dict[str, Dict[str, Any]] = {}
for _st in INDIA_STATES_DIRECTORY:
    _st_name = _st["state"]
    _cap_name = _st["capital"]
    _cap_entry = next((c for c in _st["cities"] if c["name"] == _cap_name), _st["cities"][0])
    # Map the state/UT name itself to its capital/primary monitoring city
    KNOWN_CITY_COORDS[_st_name.lower()] = {
        "name": f"{_cap_entry['name']} ({_st_name})",
        "country": "India",
        "admin1": _st_name,
        "latitude": _cap_entry["latitude"],
        "longitude": _cap_entry["longitude"],
    }
    for _city in _st["cities"]:
        KNOWN_CITY_COORDS[_city["name"].lower()] = {
            "name": _city["name"],
            "country": "India",
            "admin1": _st_name,
            "latitude": _city["latitude"],
            "longitude": _city["longitude"],
        }

# Common historical & regional aliases across India
_CITY_ALIASES = {
    "bombay": "mumbai",
    "bangalore": "bengaluru",
    "mysore": "mysuru",
    "mangalore": "mangaluru",
    "madras": "chennai",
    "calcutta": "kolkata",
    "trivandrum": "thiruvananthapuram",
    "cochin": "kochi",
    "calicut": "kozhikode",
    "gurgaon": "gurugram",
    "allahabad": "prayagraj",
    "baroda": "vadodara",
    "poona": "pune",
    "pondicherry": "puducherry",
    "aurangabad": "chhatrapati sambhajinagar",
    "benares": "varanasi",
    "vizag": "visakhapatnam",
    "jammu & kashmir": "jammu and kashmir",
    "andaman & nicobar": "andaman and nicobar islands",
    "andaman and nicobar": "andaman and nicobar islands",
}
for _alias, _target in _CITY_ALIASES.items():
    if _target in KNOWN_CITY_COORDS:
        KNOWN_CITY_COORDS[_alias] = dict(KNOWN_CITY_COORDS[_target])


def get_india_locations_directory() -> Dict[str, Any]:
    flat_options: List[Dict[str, str]] = []
    for st in INDIA_STATES_DIRECTORY:
        state_name = st["state"]
        flat_options.append(
            {"label": f"{state_name} ({st['type']})", "value": state_name, "state": state_name, "kind": st["type"]}
        )
        for c in st["cities"]:
            flat_options.append(
                {"label": f"{c['name']}, {state_name}", "value": c["name"], "state": state_name, "kind": "City"}
            )
    return {
        "country": "India",
        "total_states_and_uts": len(INDIA_STATES_DIRECTORY),
        "states": [
            {
                "state": s["state"],
                "type": s["type"],
                "capital": s["capital"],
                "cities": [c["name"] for c in s["cities"]],
            }
            for s in INDIA_STATES_DIRECTORY
        ],
        "options": flat_options,
    }


def is_within_india(lat: float, lon: float, country_code: Optional[str] = None) -> bool:
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return False
    if country_code is not None and str(country_code).strip() != "":
        if str(country_code).strip().upper() != "IN":
            return False
    return (
        INDIA_BOUNDS["min_lat"] <= lat_f <= INDIA_BOUNDS["max_lat"]
        and INDIA_BOUNDS["min_lon"] <= lon_f <= INDIA_BOUNDS["max_lon"]
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(DATABASE_DIR, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT 'VayuMitra Citizen',
                email TEXT NOT NULL DEFAULT '',
                bio TEXT NOT NULL DEFAULT '',
                preferred_city TEXT NOT NULL DEFAULT 'Mumbai',
                preferred_lat REAL NOT NULL DEFAULT 19.0760,
                preferred_lon REAL NOT NULL DEFAULT 72.8777,
                password_hash TEXT NOT NULL DEFAULT '',
                password_salt TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                default_city TEXT NOT NULL DEFAULT 'Mumbai',
                auto_detect_location INTEGER NOT NULL DEFAULT 0,
                temp_unit TEXT NOT NULL DEFAULT 'C',
                pollutant_unit TEXT NOT NULL DEFAULT 'ugm3',
                aqi_standard TEXT NOT NULL DEFAULT 'US',
                share_location INTEGER NOT NULL DEFAULT 1,
                anonymous_reports INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES user_profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notification_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                aqi_warnings INTEGER NOT NULL DEFAULT 1,
                location_alerts INTEGER NOT NULL DEFAULT 1,
                aqi_threshold INTEGER NOT NULL DEFAULT 100,
                pm25_threshold REAL NOT NULL DEFAULT 35.0,
                browser_notifications INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES user_profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS environmental_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                aqi INTEGER NOT NULL,
                aqi_category TEXT NOT NULL,
                pm2_5 REAL,
                pm10 REAL,
                co REAL,
                no2 REAL,
                so2 REAL,
                o3 REAL,
                temperature_c REAL,
                humidity REAL,
                wind_speed REAL,
                weather_condition TEXT,
                source TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS environmental_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                alert_title TEXT NOT NULL,
                alert_level TEXT NOT NULL,
                metric TEXT NOT NULL,
                metric_value REAL,
                threshold_value REAL,
                description TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS community_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_code TEXT NOT NULL UNIQUE,
                profile_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                location_name TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                status TEXT NOT NULL DEFAULT 'Submitted',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES user_profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS report_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (report_id) REFERENCES community_reports(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS personal_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                city TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES user_profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS personal_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                location_id INTEGER,
                location_label TEXT NOT NULL DEFAULT '',
                hours_per_day REAL NOT NULL DEFAULT 1.0,
                intensity TEXT NOT NULL DEFAULT 'Moderate',
                is_outdoor INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES user_profiles(id) ON DELETE CASCADE,
                FOREIGN KEY (location_id) REFERENCES personal_locations(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS exposure_diary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                entry_date TEXT NOT NULL,
                city TEXT NOT NULL,
                activity_summary TEXT NOT NULL,
                estimated_aqi REAL NOT NULL,
                estimated_pm25 REAL,
                calculated_exposure_score REAL NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES user_profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES user_profiles(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_readings_city_time
                ON environmental_readings(city, recorded_at DESC);
            CREATE INDEX IF NOT EXISTS idx_alerts_city_time
                ON environmental_alerts(city, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_reports_created
                ON community_reports(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_diary_date
                ON exposure_diary(entry_date DESC);
            CREATE INDEX IF NOT EXISTS idx_sessions_token
                ON user_sessions(token);
            """
        )

        # Ensure personal_locations has hours_per_day column on existing DBs
        loc_cols = {r["name"] for r in cur.execute("PRAGMA table_info(personal_locations)").fetchall()}
        if "hours_per_day" not in loc_cols:
            cur.execute("ALTER TABLE personal_locations ADD COLUMN hours_per_day REAL NOT NULL DEFAULT 8.0")

        # Ensure default profile row exists with demo login credentials
        row = cur.execute("SELECT id, email, password_hash FROM user_profiles ORDER BY id ASC LIMIT 1").fetchone()
        if not row:
            now = utc_now_iso()
            salt_hex, pw_hash = _hash_password("vayumitra123")
            cur.execute(
                """
                INSERT INTO user_profiles (
                    name, email, bio, preferred_city, preferred_lat, preferred_lon,
                    password_hash, password_salt, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Aarav Sharma",
                    "aarav@vayumitra.in",
                    "Environmental observer tracking urban air quality.",
                    Config.DEFAULT_CITY,
                    19.0760,
                    72.8777,
                    pw_hash,
                    salt_hex,
                    now,
                    now,
                ),
            )
            profile_id = cur.lastrowid
            cur.execute(
                """
                INSERT INTO user_preferences (profile_id, default_city, auto_detect_location, temp_unit, pollutant_unit, aqi_standard, share_location, anonymous_reports, updated_at)
                VALUES (?, ?, 0, 'C', 'ugm3', 'NAQI', 1, 0, ?)
                """,
                (profile_id, Config.DEFAULT_CITY, now),
            )
            cur.execute(
                """
                INSERT INTO notification_preferences (profile_id, enabled, aqi_warnings, location_alerts, aqi_threshold, pm25_threshold, browser_notifications, updated_at)
                VALUES (?, 1, 1, 1, 100, 35.0, 0, ?)
                """,
                (profile_id, now),
            )
            profile_row_id = profile_id
        else:
            profile_row_id = row["id"]
            if not row["password_hash"] or not row["email"]:
                now = utc_now_iso()
                email_to_set = row["email"] or "aarav@vayumitra.in"
                if not row["password_hash"]:
                    salt_hex, pw_hash = _hash_password("vayumitra123")
                    cur.execute(
                        "UPDATE user_profiles SET email = ?, password_hash = ?, password_salt = ?, updated_at = ? WHERE id = ?",
                        (email_to_set, pw_hash, salt_hex, now, profile_row_id),
                    )
                elif not row["email"]:
                    cur.execute(
                        "UPDATE user_profiles SET email = ?, updated_at = ? WHERE id = ?",
                        (email_to_set, now, profile_row_id),
                    )

        rep_cnt = cur.execute("SELECT COUNT(*) AS cnt FROM community_reports").fetchone()["cnt"]
        if rep_cnt == 0:
            now_seed = utc_now_iso()
            seeded_reports = [
                (
                    "VM-INDIA-101",
                    profile_row_id,
                    "Heavy smoke from construction site",
                    "Visible dust and diesel generator smoke near metro pillar corridor affecting pedestrians.",
                    "Construction dust",
                    "MG Road, Bengaluru",
                    12.9756,
                    77.6066,
                    "Under Review",
                    now_seed,
                    now_seed,
                ),
                (
                    "VM-INDIA-102",
                    profile_row_id,
                    "Open garbage burning near flyover",
                    "Piles of mixed waste burning along the service lane producing dense acrid smoke.",
                    "Garbage burning",
                    "Andheri East, Mumbai",
                    19.1136,
                    72.8697,
                    "Verified",
                    now_seed,
                    now_seed,
                ),
                (
                    "VM-INDIA-103",
                    profile_row_id,
                    "Heavy traffic exhaust congestion",
                    "Long peak-hour idling of heavy commercial vehicles creating high particulate levels.",
                    "Vehicle-related pollution",
                    "ITO Junction, Delhi",
                    28.6289,
                    77.2416,
                    "Verified",
                    now_seed,
                    now_seed,
                ),
                (
                    "VM-INDIA-104",
                    profile_row_id,
                    "Factory chimney smoke plume",
                    "Dark smoke observed emitting continuously from nearby industrial estate shed.",
                    "Industrial emissions",
                    "Pimpri-Chinchwad, Pune",
                    18.6298,
                    73.7997,
                    "Under Review",
                    now_seed,
                    now_seed,
                ),
                (
                    "VM-INDIA-105",
                    profile_row_id,
                    "Uncovered road widening dust",
                    "Dry soil and gravel left uncovered along busy intersection causing thick dust clouds.",
                    "Construction dust",
                    "T. Nagar, Chennai",
                    13.0418,
                    80.2341,
                    "Resolved",
                    now_seed,
                    now_seed,
                ),
                (
                    "VM-INDIA-106",
                    profile_row_id,
                    "Evening dry leaf and brush burning",
                    "Multiple small bonfires of dry garden leaves lowering visibility in residential block.",
                    "Smoke and burning",
                    "Mansarovar, Jaipur",
                    26.8505,
                    75.7628,
                    "Submitted",
                    now_seed,
                    now_seed,
                ),
            ]
            cur.executemany(
                """
                INSERT INTO community_reports (
                    report_code, profile_id, title, description, category, location_name,
                    latitude, longitude, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                seeded_reports,
            )
        conn.commit()
    finally:
        conn.close()


import threading
import time

_HTTP_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_HTTP_CACHE_LOCK = threading.Lock()


def _http_get_json(url: str, headers: Optional[Dict[str, str]] = None, cache_ttl: int = 90) -> Dict[str, Any]:
    now = time.time()
    if cache_ttl > 0:
        with _HTTP_CACHE_LOCK:
            cached = _HTTP_CACHE.get(url)
            if cached and (now - cached[0]) < cache_ttl:
                return cached[1]

    req_headers = {"User-Agent": "VayuMitra/1.0 (Environmental Monitoring Platform)"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=Config.HTTP_TIMEOUT) as resp:
        raw = resp.read().decode("utf-8")
        parsed = json.loads(raw)

    if cache_ttl > 0:
        with _HTTP_CACHE_LOCK:
            _HTTP_CACHE[url] = (now, parsed)
    return parsed


def _linear_subindex(val: Optional[float], breakpoints: List[Tuple[float, float, int, int]]) -> Optional[int]:
    if val is None:
        return None
    v = max(0.0, float(val))
    for c_low, c_high, i_low, i_high in breakpoints:
        if v <= c_high:
            return int(round(((i_high - i_low) / (c_high - c_low)) * (v - c_low) + i_low))
    _, c_high, _, i_high = breakpoints[-1]
    return int(round(i_high + (v - c_high) * 0.5))


def compute_indian_naqi(pollutants: Dict[str, Optional[float]]) -> Optional[int]:
    """Calculate Indian CPCB National AQI (NAQI 0-500) sub-index maximum from real pollutant concentrations."""
    sub_indices: List[int] = []
    pm25_bp = [(0, 30, 0, 50), (30.01, 60, 51, 100), (60.01, 90, 101, 200), (90.01, 120, 201, 300), (120.01, 250, 301, 400), (250.01, 380, 401, 500)]
    pm10_bp = [(0, 50, 0, 50), (50.01, 100, 51, 100), (100.01, 250, 101, 200), (250.01, 350, 201, 300), (350.01, 430, 301, 400), (430.01, 550, 401, 500)]
    no2_bp = [(0, 40, 0, 50), (40.01, 80, 51, 100), (80.01, 180, 101, 200), (180.01, 280, 201, 300), (280.01, 400, 301, 400), (400.01, 520, 401, 500)]
    so2_bp = [(0, 40, 0, 50), (40.01, 80, 51, 100), (80.01, 380, 101, 200), (380.01, 800, 201, 300), (800.01, 1600, 301, 400), (1600.01, 2000, 401, 500)]
    o3_bp = [(0, 50, 0, 50), (50.01, 100, 51, 100), (100.01, 168, 101, 200), (168.01, 208, 201, 300), (208.01, 748, 301, 400), (748.01, 900, 401, 500)]
    co_mg = (pollutants.get("co") / 1000.0) if pollutants.get("co") is not None else None
    co_bp = [(0, 1.0, 0, 50), (1.01, 2.0, 51, 100), (2.01, 10.0, 101, 200), (10.01, 17.0, 201, 300), (17.01, 34.0, 301, 400), (34.01, 46.0, 401, 500)]

    for val, bp in [
        (pollutants.get("pm2_5"), pm25_bp),
        (pollutants.get("pm10"), pm10_bp),
        (pollutants.get("no2"), no2_bp),
        (pollutants.get("so2"), so2_bp),
        (pollutants.get("o3"), o3_bp),
        (co_mg, co_bp),
    ]:
        si = _linear_subindex(val, bp)
        if si is not None:
            sub_indices.append(si)
    return max(sub_indices) if sub_indices else None


def classify_aqi(aqi_value: Optional[float], standard: str = "NAQI") -> Dict[str, Any]:
    val = float(aqi_value) if aqi_value is not None else 0.0
    std = str(standard or "NAQI").upper()

    if std == "EU":
        # European AQI (EAQI) scale: 0-20 Good, 21-40 Fair, 41-60 Moderate, 61-80 Poor, 81-100 Very Poor, >100 Extremely Poor
        if val <= 20:
            return {
                "level": "good", "category": "Good", "standard": "EU", "scale_label": "European EAQI (0–20)",
                "color": "green", "hex": "#16A34A", "bg_tint": "rgba(22, 163, 74, 0.12)",
                "message": "Air quality is good under the European AQI index.",
                "recommendation": "Enjoy outdoor activities.",
                "illustration": "assets/images/aqi-good.svg",
                "precautions": ["Air quality poses negligible respiratory risk.", "Ideal conditions for walking, cycling, and outdoor exercise.", "Open windows for natural ventilation."],
            }
        if val <= 40:
            return {
                "level": "satisfactory", "category": "Satisfactory", "standard": "EU", "scale_label": "European EAQI (21–40 Fair)",
                "color": "lime", "hex": "#65A30D", "bg_tint": "rgba(101, 163, 13, 0.12)",
                "message": "Air quality is fair/satisfactory under the European AQI index.",
                "recommendation": "Normal outdoor activities are suitable.",
                "illustration": "assets/images/aqi-good.svg",
                "precautions": ["Suitable for routine outdoor activities.", "Sensitive individuals should monitor symptoms near heavy traffic."],
            }
        if val <= 60:
            return {
                "level": "moderate", "category": "Moderate", "standard": "EU", "scale_label": "European EAQI (41–60)",
                "color": "yellow", "hex": "#D97706", "bg_tint": "rgba(217, 119, 6, 0.14)",
                "message": "Air quality is moderate under the European AQI index.",
                "recommendation": "Sensitive groups should limit intense outdoor exertion.",
                "illustration": "assets/images/aqi-moderate.svg",
                "precautions": ["Sensitive individuals should reduce prolonged traffic-corridor exposure.", "Prefer cleaner forecast windows for workouts."],
            }
        if val <= 80:
            return {
                "level": "bad", "category": "Poor", "standard": "EU", "scale_label": "European EAQI (61–80)",
                "color": "orange", "hex": "#EA580C", "bg_tint": "rgba(234, 88, 12, 0.14)",
                "message": "Air quality is poor under the European AQI index.",
                "recommendation": "Reduce prolonged outdoor activities and wear a protective mask.",
                "illustration": "assets/images/aqi-bad.svg",
                "precautions": ["Wear a fitted N95/KN95 mask outdoors.", "Move vigorous exercise indoors."],
            }
        if val <= 100:
            return {
                "level": "worse", "category": "Very Poor", "standard": "EU", "scale_label": "European EAQI (81–100)",
                "color": "red", "hex": "#DC2626", "bg_tint": "rgba(220, 38, 38, 0.14)",
                "message": "Air quality is very poor under the European AQI index.",
                "recommendation": "Avoid outdoor physical exertion and stay indoors.",
                "illustration": "assets/images/aqi-worse.svg",
                "precautions": ["Stay indoors with windows closed.", "Use N95 respiratory protection if travel is unavoidable."],
            }
        return {
            "level": "severe", "category": "Severe", "standard": "EU", "scale_label": "European EAQI (>100 Extremely Poor)",
            "color": "crimson", "hex": "#991B1B", "bg_tint": "rgba(153, 27, 27, 0.16)",
            "message": "Air quality is severely elevated under the European AQI index.",
            "recommendation": "Remain indoors and follow emergency clean-air precautions.",
            "illustration": "assets/images/aqi-worse.svg",
            "precautions": ["Remain indoors and keep doors/windows sealed.", "Avoid all outdoor exertion and monitor vulnerable individuals."],
        }

    # Indian NAQI (0-50 Good, 51-100 Satisfactory, 101-200 Moderate, 201-300 Poor, 301-400 Very Poor, >400 Severe)
    # and US EPA (0-50 Good, 51-100 Satisfactory/Moderate, 101-150 Moderate/USG, 151-200 Poor/Unhealthy, 201-300 Very Poor, >300 Severe/Hazardous)
    if std == "US":
        thresholds = (50, 100, 150, 200, 300)
        scale_prefix = "US EPA AQI"
    else:
        thresholds = (50, 100, 200, 300, 400)
        scale_prefix = "Indian NAQI"

    t1, t2, t3, t4, t5 = thresholds
    if val <= t1:
        return {
            "level": "good", "category": "Good", "standard": std, "scale_label": f"{scale_prefix} (0–{t1})",
            "color": "green", "hex": "#16A34A", "bg_tint": "rgba(22, 163, 74, 0.12)",
            "message": "Air quality is minimal impact and satisfactory.",
            "recommendation": "Enjoy outdoor activities.",
            "illustration": "assets/images/aqi-good.svg",
            "precautions": [
                "Air quality poses little or no respiratory risk.",
                "Ideal conditions for walking, cycling, and outdoor exercise.",
                "Keep windows open for natural cross-ventilation.",
            ],
        }
    if val <= t2:
        return {
            "level": "satisfactory", "category": "Satisfactory", "standard": std, "scale_label": f"{scale_prefix} ({t1 + 1}–{t2})",
            "color": "lime", "hex": "#65A30D", "bg_tint": "rgba(101, 163, 13, 0.12)",
            "message": "Air quality is acceptable; sensitive people may feel minor discomfort.",
            "recommendation": "Suitable for outdoor activity; sensitive groups should pace exertion.",
            "illustration": "assets/images/aqi-good.svg",
            "precautions": [
                "People with asthma or heart conditions should avoid lingering near busy intersections.",
                "Prefer morning or post-rain hours for strenuous outdoor workouts.",
                "Stay hydrated and track hourly AQI updates.",
            ],
        }
    if val <= t3:
        return {
            "level": "moderate", "category": "Moderate", "standard": std, "scale_label": f"{scale_prefix} ({t2 + 1}–{t3})",
            "color": "yellow", "hex": "#D97706", "bg_tint": "rgba(217, 119, 6, 0.14)",
            "message": "Breathing discomfort possible for children, older adults, and sensitive groups.",
            "recommendation": "Reduce prolonged outdoor exertion and take precautions.",
            "illustration": "assets/images/aqi-moderate.svg",
            "precautions": [
                "Sensitive groups (asthma, children, older adults) should wear a light N95/KN95 mask outdoors.",
                "Prefer low-traffic routes via Smart Clean-Air Route Finder.",
                "Close street-facing windows during peak traffic hours.",
            ],
        }
    if val <= t4:
        return {
            "level": "bad", "category": "Poor", "standard": std, "scale_label": f"{scale_prefix} ({t3 + 1}–{t4})",
            "color": "orange", "hex": "#EA580C", "bg_tint": "rgba(234, 88, 12, 0.14)",
            "message": "Breathing discomfort likely on prolonged exposure for most people.",
            "recommendation": "Wear a mask outdoors and shift vigorous exercise indoors.",
            "illustration": "assets/images/aqi-bad.svg",
            "precautions": [
                "Wear a properly fitted N95/KN95 mask when stepping outdoors.",
                "Limit outdoor exercise and move workouts indoors.",
                "Use Emergency Escape Mode on Routes to avoid reported hotspots.",
            ],
        }
    if val <= t5:
        return {
            "level": "worse", "category": "Very Poor", "standard": std, "scale_label": f"{scale_prefix} ({t4 + 1}–{t5})",
            "color": "red", "hex": "#DC2626", "bg_tint": "rgba(220, 38, 38, 0.14)",
            "message": "Respiratory illness risk on prolonged exposure. Serious impact on vulnerable groups.",
            "recommendation": "Stay indoors and avoid outdoor physical exertion.",
            "illustration": "assets/images/aqi-worse.svg",
            "precautions": [
                "Stay indoors with windows sealed and run HEPA filtration if available.",
                "Wear an N95/FFP2 respirator if essential outdoor travel cannot be avoided.",
                "Monitor children, older adults, and people with cardiac/respiratory conditions.",
            ],
        }
    return {
        "level": "severe", "category": "Severe", "standard": std, "scale_label": f"{scale_prefix} (> {t5})",
        "color": "crimson", "hex": "#991B1B", "bg_tint": "rgba(153, 27, 27, 0.16)",
        "message": "Severe air pollution affecting healthy people and seriously impacting vulnerable groups.",
        "recommendation": "Emergency caution: remain indoors and avoid all outdoor exertion.",
        "illustration": "assets/images/aqi-worse.svg",
        "precautions": [
            "Remain indoors with doors and windows sealed.",
            "Avoid all outdoor physical activity and high-traffic corridors.",
            "Use Emergency Escape Mode if relocating from an affected hotspot.",
        ],
    }


def _hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
    salt_bytes = salt if salt is not None else os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", str(password).encode("utf-8"), salt_bytes, 100_000).hex()
    return salt_bytes.hex(), pw_hash


def _verify_password(password: str, pw_hash: str, pw_salt: str) -> bool:
    if not pw_hash or not pw_salt:
        return False
    try:
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            str(password).encode("utf-8"),
            bytes.fromhex(pw_salt),
            100_000,
        ).hex()
        return secrets.compare_digest(expected, pw_hash)
    except Exception:
        return False


def _resolve_profile_row(conn: sqlite3.Connection, auth_token: Optional[str] = None) -> sqlite3.Row:
    if auth_token:
        tok = str(auth_token).strip()
        if tok:
            sess = conn.execute(
                """
                SELECT p.*
                FROM user_sessions s
                JOIN user_profiles p ON p.id = s.profile_id
                WHERE s.token = ? AND s.expires_at > ?
                LIMIT 1
                """,
                (tok, utc_now_iso()),
            ).fetchone()
            if sess:
                return sess
    return conn.execute("SELECT * FROM user_profiles ORDER BY id ASC LIMIT 1").fetchone()


def _create_session_token(conn: sqlite3.Connection, profile_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=14)
    conn.execute(
        "INSERT INTO user_sessions (profile_id, token, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (profile_id, token, now.replace(microsecond=0).isoformat(), expires.replace(microsecond=0).isoformat()),
    )
    return token


def register_user(name: str, email: str, password: str, preferred_city: str = "Mumbai") -> Dict[str, Any]:
    name = (name or "").strip()
    email = (email or "").strip().lower()
    pw = str(password or "")
    city_in = (preferred_city or Config.DEFAULT_CITY).strip() or Config.DEFAULT_CITY

    if len(name) < 2:
        raise ValueError("Please enter your full name (at least 2 characters).")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ValueError("Please enter a valid email address.")
    if len(pw) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    geo = resolve_location(city=city_in)
    if not geo:
        raise ValueError("Preferred city must be located within India (e.g., Mumbai, Delhi, Bengaluru).")

    init_db()
    conn = get_db_connection()
    now = utc_now_iso()
    try:
        existing = conn.execute("SELECT id FROM user_profiles WHERE LOWER(email) = ? LIMIT 1", (email,)).fetchone()
        if existing:
            raise ValueError("An account with this email already exists. Please sign in instead.")

        salt_hex, pw_hash = _hash_password(pw)
        cur = conn.execute(
            """
            INSERT INTO user_profiles (
                name, email, bio, preferred_city, preferred_lat, preferred_lon,
                password_hash, password_salt, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                email,
                "VayuMitra environmental citizen tracking air quality.",
                geo["name"],
                geo["latitude"],
                geo["longitude"],
                pw_hash,
                salt_hex,
                now,
                now,
            ),
        )
        pid = cur.lastrowid
        conn.execute(
            """
            INSERT INTO user_preferences (profile_id, default_city, auto_detect_location, temp_unit, pollutant_unit, aqi_standard, share_location, anonymous_reports, updated_at)
            VALUES (?, ?, 0, 'C', 'ugm3', 'NAQI', 1, 0, ?)
            """,
            (pid, geo["name"], now),
        )
        conn.execute(
            """
            INSERT INTO notification_preferences (profile_id, enabled, aqi_warnings, location_alerts, aqi_threshold, pm25_threshold, browser_notifications, updated_at)
            VALUES (?, 1, 1, 1, 100, 35.0, 0, ?)
            """,
            (pid, now),
        )
        token = _create_session_token(conn, pid)
        conn.commit()
    finally:
        conn.close()

    bundle = get_profile_bundle(auth_token=token)
    return {
        "token": token,
        "authenticated": True,
        "user": bundle["profile"],
        "bundle": bundle,
        "message": f"Welcome to VayuMitra, {bundle['profile']['name']}!",
    }


def login_user(email: str, password: str) -> Dict[str, Any]:
    email_norm = (email or "").strip().lower()
    pw = str(password or "")
    if not email_norm or not pw:
        raise ValueError("Please enter both email and password.")

    init_db()
    conn = get_db_connection()
    try:
        profile = conn.execute(
            "SELECT * FROM user_profiles WHERE LOWER(email) = ? ORDER BY id ASC LIMIT 1",
            (email_norm,),
        ).fetchone()
        if not profile or not _verify_password(pw, profile["password_hash"], profile["password_salt"]):
            raise ValueError("Invalid email or password.")

        token = _create_session_token(conn, profile["id"])
        conn.commit()
    finally:
        conn.close()

    bundle = get_profile_bundle(auth_token=token)
    return {
        "token": token,
        "authenticated": True,
        "user": bundle["profile"],
        "bundle": bundle,
        "message": f"Signed in as {bundle['profile']['name']}.",
    }


def logout_user(auth_token: Optional[str] = None) -> Dict[str, Any]:
    init_db()
    if auth_token:
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM user_sessions WHERE token = ?", (str(auth_token).strip(),))
            conn.commit()
        finally:
            conn.close()
    return {"authenticated": False, "message": "You have been logged out of VayuMitra."}


def get_auth_session(auth_token: Optional[str] = None) -> Dict[str, Any]:
    init_db()
    if not auth_token or not str(auth_token).strip():
        return {"authenticated": False, "user": None}
    conn = get_db_connection()
    try:
        sess = conn.execute(
            """
            SELECT p.*
            FROM user_sessions s
            JOIN user_profiles p ON p.id = s.profile_id
            WHERE s.token = ? AND s.expires_at > ?
            LIMIT 1
            """,
            (str(auth_token).strip(), utc_now_iso()),
        ).fetchone()
        if not sess:
            return {"authenticated": False, "user": None}
        return {
            "authenticated": True,
            "user": {
                "id": sess["id"],
                "name": sess["name"],
                "email": sess["email"],
                "preferred_city": sess["preferred_city"],
            },
        }
    finally:
        conn.close()


def get_profile_bundle(auth_token: Optional[str] = None) -> Dict[str, Any]:
    init_db()
    conn = get_db_connection()
    try:
        profile = _resolve_profile_row(conn, auth_token)
        prefs = conn.execute("SELECT * FROM user_preferences WHERE profile_id = ?", (profile["id"],)).fetchone()
        notif = conn.execute("SELECT * FROM notification_preferences WHERE profile_id = ?", (profile["id"],)).fetchone()
        return {
            "profile": {
                "id": profile["id"],
                "name": profile["name"],
                "email": profile["email"],
                "bio": profile["bio"],
                "preferred_city": profile["preferred_city"],
                "preferred_lat": profile["preferred_lat"],
                "preferred_lon": profile["preferred_lon"],
                "has_password": bool(profile["password_hash"]),
                "updated_at": profile["updated_at"],
            },
            "preferences": {
                "default_city": prefs["default_city"],
                "auto_detect_location": bool(prefs["auto_detect_location"]),
                "temp_unit": prefs["temp_unit"],
                "pollutant_unit": prefs["pollutant_unit"],
                "aqi_standard": prefs["aqi_standard"],
                "share_location": bool(prefs["share_location"]),
                "anonymous_reports": bool(prefs["anonymous_reports"]),
                "updated_at": prefs["updated_at"],
            },
            "notifications": {
                "enabled": bool(notif["enabled"]),
                "aqi_warnings": bool(notif["aqi_warnings"]),
                "location_alerts": bool(notif["location_alerts"]),
                "aqi_threshold": notif["aqi_threshold"],
                "pm25_threshold": notif["pm25_threshold"],
                "browser_notifications": bool(notif["browser_notifications"]),
                "updated_at": notif["updated_at"],
            },
        }
    finally:
        conn.close()


def update_profile_bundle(payload: Dict[str, Any], auth_token: Optional[str] = None) -> Dict[str, Any]:
    init_db()
    conn = get_db_connection()
    now = utc_now_iso()
    try:
        profile = _resolve_profile_row(conn, auth_token)
        pid = profile["id"]

        prof_in = payload.get("profile") or {}
        prefs_in = payload.get("preferences") or {}
        notif_in = payload.get("notifications") or {}
        sec_in = payload.get("security") or {}

        preferred_city = (
            str(prof_in.get("preferred_city") or prefs_in.get("default_city") or profile["preferred_city"]).strip()
            or "Mumbai"
        )
        geo = resolve_location(city=preferred_city)
        if not geo:
            raise ValueError("Default city must be located within India (e.g., Mumbai, Delhi, Bengaluru, Pune).")
        pref_lat = geo["latitude"]
        pref_lon = geo["longitude"]
        resolved_city_name = geo["name"]

        name = str(prof_in.get("name", profile["name"])).strip() or profile["name"]
        email = str(prof_in.get("email", profile["email"])).strip()
        if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("Please provide a valid email address.")
        bio = str(prof_in.get("bio", profile["bio"])).strip()[:400]

        conn.execute(
            """
            UPDATE user_profiles
            SET name = ?, email = ?, bio = ?, preferred_city = ?, preferred_lat = ?, preferred_lon = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, email, bio, resolved_city_name, pref_lat, pref_lon, now, pid),
        )

        # Password update (salted PBKDF2-HMAC-SHA256)
        new_password = sec_in.get("new_password")
        if new_password is not None and str(new_password).strip() != "":
            pw = str(new_password)
            if len(pw) < 8:
                raise ValueError("Password must be at least 8 characters long.")
            if profile["password_hash"]:
                current_pw = str(sec_in.get("current_password") or "")
                expected = hashlib.pbkdf2_hmac(
                    "sha256",
                    current_pw.encode("utf-8"),
                    bytes.fromhex(profile["password_salt"]),
                    100_000,
                ).hex()
                if expected != profile["password_hash"]:
                    raise ValueError("Current password does not match.")
            salt = os.urandom(16)
            pw_hash = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, 100_000).hex()
            conn.execute(
                "UPDATE user_profiles SET password_hash = ?, password_salt = ?, updated_at = ? WHERE id = ?",
                (pw_hash, salt.hex(), now, pid),
            )

        cur_prefs = conn.execute("SELECT * FROM user_preferences WHERE profile_id = ?", (pid,)).fetchone()
        temp_unit = str(prefs_in.get("temp_unit", cur_prefs["temp_unit"])).upper()
        if temp_unit not in ("C", "F"):
            temp_unit = "C"
        pollutant_unit = str(prefs_in.get("pollutant_unit", cur_prefs["pollutant_unit"])).lower()
        if pollutant_unit not in ("ugm3", "mgm3"):
            pollutant_unit = "ugm3"
        aqi_standard = str(prefs_in.get("aqi_standard", cur_prefs["aqi_standard"])).upper()
        if aqi_standard not in ("NAQI", "US", "EU"):
            aqi_standard = "NAQI"

        conn.execute(
            """
            UPDATE user_preferences
            SET default_city = ?, auto_detect_location = ?, temp_unit = ?, pollutant_unit = ?, aqi_standard = ?,
                share_location = ?, anonymous_reports = ?, updated_at = ?
            WHERE profile_id = ?
            """,
            (
                resolved_city_name,
                int(bool(prefs_in.get("auto_detect_location", cur_prefs["auto_detect_location"]))),
                temp_unit,
                pollutant_unit,
                aqi_standard,
                int(bool(prefs_in.get("share_location", cur_prefs["share_location"]))),
                int(bool(prefs_in.get("anonymous_reports", cur_prefs["anonymous_reports"]))),
                now,
                pid,
            ),
        )

        cur_notif = conn.execute("SELECT * FROM notification_preferences WHERE profile_id = ?", (pid,)).fetchone()
        aqi_thresh = int(notif_in.get("aqi_threshold", cur_notif["aqi_threshold"]))
        aqi_thresh = max(25, min(400, aqi_thresh))
        pm25_thresh = float(notif_in.get("pm25_threshold", cur_notif["pm25_threshold"]))
        pm25_thresh = max(5.0, min(250.0, pm25_thresh))

        conn.execute(
            """
            UPDATE notification_preferences
            SET enabled = ?, aqi_warnings = ?, location_alerts = ?, aqi_threshold = ?, pm25_threshold = ?,
                browser_notifications = ?, updated_at = ?
            WHERE profile_id = ?
            """,
            (
                int(bool(notif_in.get("enabled", cur_notif["enabled"]))),
                int(bool(notif_in.get("aqi_warnings", cur_notif["aqi_warnings"]))),
                int(bool(notif_in.get("location_alerts", cur_notif["location_alerts"]))),
                aqi_thresh,
                pm25_thresh,
                int(bool(notif_in.get("browser_notifications", cur_notif["browser_notifications"]))),
                now,
                pid,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get_profile_bundle(auth_token=auth_token)


def resolve_location(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    if lat is not None and lon is not None:
        if not is_within_india(lat, lon):
            raise LookupError("VayuMitra currently supports locations within India only.")
        resolved_name = city or f"{lat:.3f}, {lon:.3f}"
        admin1 = ""
        try:
            rev_url = (
                f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
            )
            rev = _http_get_json(rev_url)
            addr = rev.get("address", {})
            cc = str(addr.get("country_code", "")).lower()
            if cc and cc != "in":
                raise LookupError("VayuMitra currently supports locations within India only.")
            admin1 = addr.get("state", "")
            if not city:
                resolved_name = (
                    addr.get("city")
                    or addr.get("town")
                    or addr.get("state_district")
                    or addr.get("state")
                    or rev.get("name")
                    or resolved_name
                )
        except LookupError:
            raise
        except Exception:
            pass
        return {
            "name": resolved_name,
            "country": "India",
            "admin1": admin1,
            "latitude": float(lat),
            "longitude": float(lon),
        }

    query = (city or "").strip()
    if not query:
        bundle = get_profile_bundle()
        query = bundle["preferences"]["default_city"] or Config.DEFAULT_CITY

    # Coordinate pair input e.g. "19.076, 72.877"
    coord_match = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", query)
    if coord_match:
        return resolve_location(lat=float(coord_match.group(1)), lon=float(coord_match.group(2)))

    if "," in query:
        parts = [p.strip() for p in query.split(",") if p.strip()]
        if len(parts) == 2:
            c_hit = KNOWN_CITY_COORDS.get(parts[0].lower())
            if c_hit and (parts[1].lower() == "india" or c_hit["admin1"].lower() == parts[1].lower()):
                return dict(c_hit)

    if "," not in query:
        fallback = KNOWN_CITY_COORDS.get(query.lower())
        if fallback:
            return dict(fallback)
        in_results = []
        try:
            encoded = urllib.parse.quote(query)
            url = (
                f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}"
                "&count=5&language=en&format=json&countryCode=IN"
            )
            data = _http_get_json(url)
            in_results = [
                r for r in (data.get("results") or [])
                if is_within_india(r.get("latitude"), r.get("longitude"), r.get("country_code"))
            ]
        except Exception:
            in_results = []

        # Guard against foreign major cities (e.g. London, Paris, Tokyo) matching tiny hamlets or streets
        try:
            encoded = urllib.parse.quote(query)
            global_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=1&language=en&format=json"
            g_data = _http_get_json(global_url)
            g_top = (g_data.get("results") or [None])[0]
            if g_top and str(g_top.get("country_code", "")).upper() != "IN" and (g_top.get("population") or 0) >= 200000:
                big_in = [r for r in in_results if (r.get("population") or 0) >= 50000]
                if not big_in:
                    return None
        except Exception:
            pass

        if in_results:
            r = in_results[0]
            return {
                "name": r.get("name", query),
                "country": "India",
                "admin1": r.get("admin1", ""),
                "latitude": float(r["latitude"]),
                "longitude": float(r["longitude"]),
            }

    try:
        encoded = urllib.parse.quote(query)
        nom_url = (
            f"https://nominatim.openstreetmap.org/search?q={encoded}"
            "&countrycodes=in&format=json&limit=5&addressdetails=1"
        )
        nom_res = _http_get_json(nom_url)
        if isinstance(nom_res, list):
            allowed_classes = ("place", "boundary") if "," not in query else ("place", "boundary", "railway", "landuse", "highway")
            ordered = sorted(
                nom_res,
                key=lambda it: 0 if it.get("class") in ("place", "boundary") else 1,
            )
            for item in ordered:
                if item.get("class") not in allowed_classes:
                    continue
                addr = item.get("address") or {}
                cc = addr.get("country_code", "")
                if is_within_india(item.get("lat"), item.get("lon"), cc):
                    short_name = (
                        addr.get("suburb")
                        or addr.get("neighbourhood")
                        or addr.get("city")
                        or addr.get("town")
                        or addr.get("village")
                        or addr.get("state_district")
                        or query.split(",")[0].strip()
                    )
                    return {
                        "name": short_name,
                        "country": "India",
                        "admin1": addr.get("state", ""),
                        "latitude": float(item["lat"]),
                        "longitude": float(item["lon"]),
                    }
    except Exception:
        pass

    fallback = KNOWN_CITY_COORDS.get(query.lower())
    if fallback:
        return dict(fallback)
    return None


def fetch_air_quality_bundle(
    lat: float,
    lon: float,
    past_days: int = 2,
    forecast_days: int = 2,
) -> Dict[str, Any]:
    url = (
        "https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={lat}&longitude={lon}"
        "&current=us_aqi,european_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"
        "&hourly=us_aqi,european_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"
        f"&past_days={past_days}&forecast_days={forecast_days}&timezone=auto"
    )
    return _http_get_json(url)


def fetch_weather_current(lat: float, lon: float) -> Dict[str, Any]:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
        "&timezone=auto"
    )
    return _http_get_json(url)


def format_temp(temp_c: Optional[float], unit: str) -> Optional[float]:
    if temp_c is None:
        return None
    if unit == "F":
        return round((float(temp_c) * 9.0 / 5.0) + 32.0, 1)
    return round(float(temp_c), 1)


def _persist_reading_and_evaluate_alerts(
    city: str,
    lat: float,
    lon: float,
    current_aqi: int,
    category: str,
    pollutants: Dict[str, Optional[float]],
    weather: Dict[str, Any],
    recorded_at: str,
    prev_hour_aqi: Optional[float],
    source: str,
) -> List[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    now = utc_now_iso()
    triggered: List[Dict[str, Any]] = []
    try:
        # Store reading snapshot if not already stored for this city + recorded_at
        existing = conn.execute(
            "SELECT id FROM environmental_readings WHERE city = ? AND recorded_at = ? LIMIT 1",
            (city, recorded_at),
        ).fetchone()
        if not existing:
            conn.execute(
                """
                INSERT INTO environmental_readings (
                    city, latitude, longitude, aqi, aqi_category, pm2_5, pm10, co, no2, so2, o3,
                    temperature_c, humidity, wind_speed, weather_condition, source, recorded_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    city,
                    lat,
                    lon,
                    current_aqi,
                    category,
                    pollutants.get("pm2_5"),
                    pollutants.get("pm10"),
                    pollutants.get("co"),
                    pollutants.get("no2"),
                    pollutants.get("so2"),
                    pollutants.get("o3"),
                    weather.get("temperature_c"),
                    weather.get("humidity"),
                    weather.get("wind_speed"),
                    weather.get("condition"),
                    source,
                    recorded_at,
                    now,
                ),
            )

        notif_row = conn.execute("SELECT * FROM notification_preferences ORDER BY id ASC LIMIT 1").fetchone()
        aqi_threshold = int(notif_row["aqi_threshold"]) if notif_row else 100
        pm25_threshold = float(notif_row["pm25_threshold"]) if notif_row else 35.0
        alerts_enabled = bool(notif_row["enabled"]) if notif_row else True

        rules: List[Tuple[str, str, str, float, float, str]] = []
        if current_aqi > 200:
            rules.append(
                (
                    f"Hazardous Air Quality in {city}",
                    "Worse",
                    "AQI",
                    float(current_aqi),
                    200.0,
                    f"AQI reached {current_aqi} (Hazardous). Stay indoors and avoid outdoor physical activity.",
                )
            )
        elif current_aqi > 100:
            rules.append(
                (
                    f"Poor Air Quality in {city}",
                    "Bad",
                    "AQI",
                    float(current_aqi),
                    100.0,
                    f"AQI is {current_aqi} (Bad). Reduce prolonged outdoor activity and wear a protective mask.",
                )
            )
        elif alerts_enabled and current_aqi >= aqi_threshold:
            rules.append(
                (
                    f"AQI Exceeded Custom Threshold in {city}",
                    "Moderate" if current_aqi <= 100 else "Bad",
                    "AQI",
                    float(current_aqi),
                    float(aqi_threshold),
                    f"Current AQI ({current_aqi}) crossed your configured alert threshold ({aqi_threshold}).",
                )
            )

        pm25 = pollutants.get("pm2_5")
        if pm25 is not None and pm25 >= pm25_threshold:
            rules.append(
                (
                    f"Elevated PM2.5 Concentration in {city}",
                    "Bad" if pm25 >= 55 else "Moderate",
                    "PM2.5",
                    float(pm25),
                    pm25_threshold,
                    f"PM2.5 measured at {pm25:.1f} µg/m³ (threshold: {pm25_threshold:.0f} µg/m³).",
                )
            )

        pm10 = pollutants.get("pm10")
        if pm10 is not None and pm10 >= 100.0:
            rules.append(
                (
                    f"High Coarse Particulate (PM10) in {city}",
                    "Bad" if pm10 >= 150 else "Moderate",
                    "PM10",
                    float(pm10),
                    100.0,
                    f"PM10 measured at {pm10:.1f} µg/m³, indicating elevated dust or particulate load.",
                )
            )

        if prev_hour_aqi is not None and (current_aqi - prev_hour_aqi) >= 20:
            diff = round(current_aqi - prev_hour_aqi)
            rules.append(
                (
                    f"Sudden AQI Spike Detected in {city}",
                    "Bad" if current_aqi > 100 else "Moderate",
                    "AQI_SPIKE",
                    float(current_aqi),
                    float(prev_hour_aqi),
                    f"AQI jumped by +{diff} points compared to the previous hour (from {int(prev_hour_aqi)} to {current_aqi}).",
                )
            )

        for title, level, metric, val, thresh, desc in rules:
            triggered.append(
                {
                    "city": city,
                    "alert_title": title,
                    "alert_level": level,
                    "metric": metric,
                    "metric_value": val,
                    "threshold_value": thresh,
                    "description": desc,
                    "source": source,
                    "created_at": recorded_at,
                }
            )
            recent = conn.execute(
                """
                SELECT id FROM environmental_alerts
                WHERE city = ? AND metric = ? AND created_at >= datetime('now', '-1 hour')
                LIMIT 1
                """,
                (city, metric),
            ).fetchone()
            if not recent:
                conn.execute(
                    """
                    INSERT INTO environmental_alerts (city, alert_title, alert_level, metric, metric_value, threshold_value, description, source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (city, title, level, metric, val, thresh, desc, source, now),
                )

        conn.commit()
    finally:
        conn.close()
    return triggered


def get_air_quality_data(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> Dict[str, Any]:
    bundle_cfg = get_profile_bundle()
    prefs = bundle_cfg["preferences"]
    location = resolve_location(city=city, lat=lat, lon=lon)
    if not location:
        raise LookupError(
            f"Location '{city}' was not found in India. VayuMitra supports Indian cities and neighborhoods only (e.g., Mumbai, Delhi, Bengaluru, Pune, Chennai, Kolkata)."
        )

    aq = fetch_air_quality_bundle(location["latitude"], location["longitude"], past_days=2, forecast_days=2)
    wx = fetch_weather_current(location["latitude"], location["longitude"])

    cur_aq = aq.get("current") or {}
    cur_wx = wx.get("current") or {}
    hourly = aq.get("hourly") or {}
    times: List[str] = hourly.get("time") or []
    aqi_series = hourly.get("us_aqi") or []
    pm25_series = hourly.get("pm2_5") or []
    pm10_series = hourly.get("pm10") or []

    pollutants = {
        "pm2_5": cur_aq.get("pm2_5"),
        "pm10": cur_aq.get("pm10"),
        "co": cur_aq.get("carbon_monoxide"),
        "no2": cur_aq.get("nitrogen_dioxide"),
        "so2": cur_aq.get("sulphur_dioxide"),
        "o3": cur_aq.get("ozone"),
    }

    selected_std = str(prefs.get("aqi_standard") or "NAQI").upper()
    if selected_std not in ("NAQI", "US", "EU"):
        selected_std = "NAQI"

    if selected_std == "EU":
        raw_aqi = cur_aq.get("european_aqi")
        if raw_aqi is None:
            raw_aqi = cur_aq.get("us_aqi") or 0
            selected_std = "US"
    elif selected_std == "US":
        raw_aqi = cur_aq.get("us_aqi")
        if raw_aqi is None:
            raw_aqi = cur_aq.get("european_aqi") or 0
    else:
        naqi_val = compute_indian_naqi(pollutants)
        if naqi_val is not None:
            raw_aqi = naqi_val
        else:
            raw_aqi = cur_aq.get("us_aqi") or 0
            selected_std = "US"

    current_aqi = int(round(float(raw_aqi)))
    classification = classify_aqi(current_aqi, standard=selected_std)

    recorded_at = cur_aq.get("time") or utc_now_iso()

    # Slice real historical hourly points up to current time
    cur_prefix = recorded_at[:13]
    current_idx = len(times) - 1
    for i, t in enumerate(times):
        if t[:13] == cur_prefix:
            current_idx = i
            break
        if t <= recorded_at:
            current_idx = i

    history_points = []
    start_idx = max(0, current_idx - 23)
    for i in range(start_idx, current_idx + 1):
        if i < len(times) and aqi_series[i] is not None:
            history_points.append(
                {
                    "time": times[i],
                    "aqi": int(round(aqi_series[i])),
                    "pm2_5": pm25_series[i] if i < len(pm25_series) else None,
                    "pm10": pm10_series[i] if i < len(pm10_series) else None,
                }
            )

    prev_hour_aqi = history_points[-2]["aqi"] if len(history_points) >= 2 else None

    temp_c = cur_wx.get("temperature_2m")
    weather = {
        "temperature_c": temp_c,
        "temperature": format_temp(temp_c, prefs["temp_unit"]),
        "temp_unit": f"°{prefs['temp_unit']}",
        "humidity": cur_wx.get("relative_humidity_2m"),
        "wind_speed": cur_wx.get("wind_speed_10m"),
        "weather_code": cur_wx.get("weather_code"),
        "condition": WMO_WEATHER_LABELS.get(cur_wx.get("weather_code"), "Clear"),
    }

    source_label = "Open-Meteo Air Quality & Weather API"
    active_alerts = _persist_reading_and_evaluate_alerts(
        location["name"],
        location["latitude"],
        location["longitude"],
        current_aqi,
        classification["category"],
        pollutants,
        weather,
        recorded_at,
        prev_hour_aqi,
        source_label,
    )

    return {
        "location": location,
        "aqi": current_aqi,
        "indian_naqi": compute_indian_naqi(pollutants),
        "european_aqi": cur_aq.get("european_aqi"),
        "us_aqi": cur_aq.get("us_aqi"),
        "aqi_standard": selected_std,
        "classification": classification,
        "pollutants": pollutants,
        "pollutant_units": {
            "pm2_5": "µg/m³",
            "pm10": "µg/m³",
            "co": "mg/m³" if prefs["pollutant_unit"] == "mgm3" else "µg/m³",
            "no2": "µg/m³",
            "so2": "µg/m³",
            "o3": "µg/m³",
        },
        "pollutant_unit_mode": prefs["pollutant_unit"],
        "weather": weather,
        "recorded_at": recorded_at,
        "timezone": aq.get("timezone", "GMT"),
        "source": source_label,
        "is_live": True,
        "data_classification": {
            "aqi_and_pollutants": f"Measured / Regional Atmospheric Grid (Open-Meteo CAMS · {classification['scale_label']})",
            "weather": "Measured / Synoptic Weather Grid (Open-Meteo WMO)",
            "health_alerts": "Calculated / Rule-based Threshold Evaluation",
        },
        "hourly_history": history_points,
        "active_alerts": active_alerts,
        "preferences": prefs,
    }


def get_forecast_data(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> Dict[str, Any]:
    location = resolve_location(city=city, lat=lat, lon=lon)
    if not location:
        raise LookupError(
            f"Location '{city}' was not found in India. VayuMitra supports Indian cities only."
        )

    bundle_cfg = get_profile_bundle()
    std = str(bundle_cfg["preferences"].get("aqi_standard") or "NAQI").upper()

    aq = fetch_air_quality_bundle(location["latitude"], location["longitude"], past_days=3, forecast_days=3)
    hourly = aq.get("hourly") or {}
    times: List[str] = hourly.get("time") or []
    cur_time = (aq.get("current") or {}).get("time") or utc_now_iso()

    us_aqi = hourly.get("us_aqi") or []
    eu_aqi = hourly.get("european_aqi") or []
    pm25 = hourly.get("pm2_5") or []
    pm10 = hourly.get("pm10") or []
    co_arr = hourly.get("carbon_monoxide") or []
    no2 = hourly.get("nitrogen_dioxide") or []
    so2 = hourly.get("sulphur_dioxide") or []
    o3 = hourly.get("ozone") or []

    forecast_points = []
    all_future_points = []
    past_points = []
    fc_idx = 0
    for i, t in enumerate(times):
        p_snap = {
            "pm2_5": pm25[i] if i < len(pm25) else None,
            "pm10": pm10[i] if i < len(pm10) else None,
            "co": co_arr[i] if i < len(co_arr) else None,
            "no2": no2[i] if i < len(no2) else None,
            "so2": so2[i] if i < len(so2) else None,
            "o3": o3[i] if i < len(o3) else None,
        }
        if std == "EU" and i < len(eu_aqi) and eu_aqi[i] is not None:
            val = eu_aqi[i]
        elif std == "NAQI":
            val = compute_indian_naqi(p_snap)
            if val is None:
                val = us_aqi[i] if i < len(us_aqi) else None
        else:
            val = us_aqi[i] if i < len(us_aqi) else None

        if val is None:
            continue
        aqi_int = int(round(val))
        item = {
            "time": t,
            "aqi": aqi_int,
            "category": classify_aqi(val, standard=std)["category"],
            **p_snap,
        }
        if t <= cur_time:
            past_points.append(item)
        else:
            all_future_points.append(item)
            if len(forecast_points) < 24:
                spread = max(6, int(round(aqi_int * (0.08 + fc_idx * 0.008))))
                item["confidence_low"] = max(0, aqi_int - spread)
                item["confidence_high"] = min(500, aqi_int + spread)
                item["uncertainty_margin"] = spread
                item["confidence_level"] = "High" if fc_idx < 6 else ("Medium" if fc_idx < 15 else "Lower")
                forecast_points.append(item)
                fc_idx += 1

    # Daily forecast rollup across future days
    daily_buckets: Dict[str, List[int]] = {}
    for fp in all_future_points:
        daily_buckets.setdefault(fp["time"][:10], []).append(fp["aqi"])
    daily_forecast = []
    for d_key in sorted(daily_buckets.keys())[:3]:
        vals = daily_buckets[d_key]
        avg_v = round(sum(vals) / len(vals), 1)
        daily_forecast.append(
            {
                "date": d_key,
                "avg_aqi": avg_v,
                "min_aqi": min(vals),
                "max_aqi": max(vals),
                "category": classify_aqi(avg_v, standard=std)["category"],
                "hours": len(vals),
            }
        )

    completeness_pct = round((len(forecast_points) / 24.0) * 100.0, 1) if forecast_points else 0.0

    return {
        "location": location,
        "aqi_standard": std,
        "is_prediction": True,
        "forecast_period": "Next 24 Hours (Hourly) & 3-Day Daily Outlook",
        "forecast_method": "Open-Meteo CAMS Global Atmospheric Composition Forecast",
        "historical_basis_note": (
            f"Combines the past {len(past_points)} hours of Open-Meteo regional pollutant assimilation "
            "(PM2.5, PM10, NO2, SO2, CO, O3) with CAMS numerical atmospheric transport and meteorological forecasts."
        ),
        "disclaimer": "Hourly values and shaded uncertainty intervals are model-based atmospheric forecasts, not measured future observations.",
        "available": len(forecast_points) > 0,
        "data_quality": {
            "completeness_pct": completeness_pct,
            "forecast_hours_available": len(forecast_points),
            "history_hours_available": len(past_points[-24:]),
            "spatial_resolution": "Regional grid (~10–40 km)",
            "quality_badge": "Good Feed" if completeness_pct >= 90 else ("Partial Feed" if completeness_pct > 0 else "Unavailable"),
        },
        "forecast_24h": forecast_points,
        "daily_forecast": daily_forecast,
        "recent_history": past_points,
        "source": "Open-Meteo Air Quality Forecast API",
        "generated_at": utc_now_iso(),
    }


def _build_clean_air_windows(
    forecast_points: List[Dict[str, Any]],
    current_aqi: Optional[float] = None,
    standard: str = "NAQI",
) -> List[Dict[str, Any]]:
    if not forecast_points:
        return []

    def _delta_text(aqi_v: int) -> str:
        if current_aqi is None:
            return "Compared to forecast baseline"
        diff = int(round(aqi_v - current_aqi))
        if diff <= -5:
            return f"Expected {abs(diff)} pts cleaner than current ({int(round(current_aqi))})"
        if diff >= 5:
            return f"Expected +{diff} pts higher than current ({int(round(current_aqi))})"
        return f"Near current level (~{int(round(current_aqi))} AQI)"

    def _precaution(aqi_v: int) -> str:
        cls = classify_aqi(aqi_v, standard=standard)
        return cls["precautions"][0] if cls.get("precautions") else cls["recommendation"]

    windows: List[Dict[str, Any]] = []
    cleanest = min(forecast_points, key=lambda x: x["aqi"])
    worst = max(forecast_points, key=lambda x: x["aqi"])

    windows.append(
        {
            "label": "Cleanest 1-Hour Window (Next 24h)",
            "time": cleanest["time"],
            "aqi": cleanest["aqi"],
            "category": cleanest["category"],
            "expected_change": _delta_text(cleanest["aqi"]),
            "guidance": "Lowest predicted exposure window for brisk walks, cycling, or outdoor errands.",
            "precaution": _precaution(cleanest["aqi"]),
            "status": "Recommended",
        }
    )

    morning = [p for p in forecast_points if 5 <= int(p["time"][11:13]) <= 10]
    if morning:
        bm = min(morning, key=lambda x: x["aqi"])
        windows.append(
            {
                "label": "Best Morning Window (05:00–10:00)",
                "time": bm["time"],
                "aqi": bm["aqi"],
                "category": bm["category"],
                "expected_change": _delta_text(bm["aqi"]),
                "guidance": "Optimal morning hour for school commute or light outdoor activity.",
                "precaution": _precaution(bm["aqi"]),
                "status": "Good" if bm["aqi"] <= 100 else "Caution",
            }
        )

    afternoon = [p for p in forecast_points if 11 <= int(p["time"][11:13]) <= 15]
    if afternoon:
        ba = min(afternoon, key=lambda x: x["aqi"])
        windows.append(
            {
                "label": "Best Midday Window (11:00–15:00)",
                "time": ba["time"],
                "aqi": ba["aqi"],
                "category": ba["category"],
                "expected_change": _delta_text(ba["aqi"]),
                "guidance": "Boundary-layer mixing is typically stronger midday; monitor daytime ozone.",
                "precaution": _precaution(ba["aqi"]),
                "status": "Good" if ba["aqi"] <= 100 else "Caution",
            }
        )

    evening = [p for p in forecast_points if 16 <= int(p["time"][11:13]) <= 21]
    if evening:
        be = min(evening, key=lambda x: x["aqi"])
        windows.append(
            {
                "label": "Best Evening Window (16:00–21:00)",
                "time": be["time"],
                "aqi": be["aqi"],
                "category": be["category"],
                "expected_change": _delta_text(be["aqi"]),
                "guidance": "Lowest predicted evening commute slot before nocturnal cooling traps smoke.",
                "precaution": _precaution(be["aqi"]),
                "status": "Good" if be["aqi"] <= 100 else "Caution",
            }
        )

    windows.append(
        {
            "label": "Highest Pollution Period to Avoid",
            "time": worst["time"],
            "aqi": worst["aqi"],
            "category": worst["category"],
            "expected_change": _delta_text(worst["aqi"]),
            "guidance": "Peak predicted AQI over next 24h; shift strenuous outdoor plans indoors.",
            "precaution": _precaution(worst["aqi"]),
            "status": "Avoid",
        }
    )
    return windows


def _analyze_pollution_sources(
    pollutants: Dict[str, Optional[float]],
    weather: Dict[str, Any],
    recorded_at: str,
    aqi: int,
    hist: List[Dict[str, Any]],
) -> Dict[str, Any]:
    pm25 = pollutants.get("pm2_5")
    pm10 = pollutants.get("pm10")
    no2 = pollutants.get("no2")
    co = pollutants.get("co")
    so2 = pollutants.get("so2")
    o3 = pollutants.get("o3")
    wind = weather.get("wind_speed")
    humidity = weather.get("humidity")

    try:
        local_hour = int(recorded_at[11:13]) if len(recorded_at) >= 13 else 12
    except ValueError:
        local_hour = 12

    # Build 24h and multi-day historical baseline comparison per pollutant
    hist_24h = hist[-24:] if len(hist) > 24 else hist
    pollutant_labels = [
        ("pm2_5", "PM2.5", "µg/m³"),
        ("pm10", "PM10", "µg/m³"),
        ("no2", "NO2", "µg/m³"),
        ("so2", "SO2", "µg/m³"),
        ("co", "CO", "µg/m³"),
        ("o3", "O3", "µg/m³"),
    ]
    historical_comparison: List[Dict[str, Any]] = []
    pct_vs_72h: Dict[str, Optional[float]] = {}

    for key, label, unit in pollutant_labels:
        cur_val = pollutants.get(key)
        vals_24 = [h[key] for h in hist_24h if h.get(key) is not None]
        vals_all = [h[key] for h in hist if h.get(key) is not None]
        avg_24 = round(sum(vals_24) / len(vals_24), 1) if vals_24 else None
        avg_all = round(sum(vals_all) / len(vals_all), 1) if vals_all else None
        ref_avg = avg_all if avg_all is not None else avg_24
        delta_pct = None
        status = "Near Baseline"
        if cur_val is not None and ref_avg and ref_avg > 0:
            delta_pct = round(((float(cur_val) - ref_avg) / ref_avg) * 100.0, 1)
            if delta_pct >= 15.0:
                status = "Above Average"
            elif delta_pct <= -15.0:
                status = "Below Average"
        pct_vs_72h[key] = delta_pct
        historical_comparison.append(
            {
                "pollutant": label,
                "key": key,
                "unit": unit,
                "current": round(float(cur_val), 1) if cur_val is not None else None,
                "avg_24h": avg_24,
                "avg_multiday": avg_all,
                "delta_pct": delta_pct,
                "status": status,
            }
        )

    candidates: List[Dict[str, Any]] = []

    # 1. Traffic / Vehicular Emissions pattern
    traffic_ev = []
    traffic_score = 0
    if no2 is not None and no2 >= 20:
        traffic_ev.append(f"NO2 measured at {no2:.1f} µg/m³ (combustion/traffic indicator).")
        traffic_score += 35 if no2 >= 40 else 20
    if pct_vs_72h.get("no2") is not None and pct_vs_72h["no2"] >= 15:
        traffic_ev.append(f"NO2 is {pct_vs_72h['no2']:+.1f}% above the multi-day baseline average.")
        traffic_score += 15
    if co is not None and co >= 400:
        traffic_ev.append(f"CO measured at {co:.0f} µg/m³ (incomplete engine combustion tracer).")
        traffic_score += 25 if co >= 700 else 15
    if (7 <= local_hour <= 11) or (17 <= local_hour <= 22):
        traffic_ev.append(f"Observation falls within peak urban commute window ({local_hour:02d}:00).")
        traffic_score += 20
    if traffic_ev and traffic_score >= 25:
        candidates.append(
            {
                "source_name": "Possible Contributor: Traffic & Vehicular Exhaust",
                "confidence": "High" if traffic_score >= 60 else ("Medium" if traffic_score >= 40 else "Low"),
                "signal_strength": min(95, traffic_score),
                "evidence": traffic_ev,
                "data_basis": "Calculated Pattern Inference from NO2, CO, Historical Baseline & Time-of-Day",
            }
        )

    # 2. Construction / Road & Coarse Dust pattern
    dust_ev = []
    dust_score = 0
    if pm10 is not None and pm25 is not None and pm25 > 0:
        ratio = pm10 / pm25
        if pm10 >= 65 and ratio >= 1.8:
            dust_ev.append(f"Coarse particulate PM10 ({pm10:.1f} µg/m³) is {ratio:.2f}x higher than PM2.5 ({pm25:.1f} µg/m³).")
            dust_score += 45 if pm10 >= 110 else 28
    elif pm10 is not None and pm10 >= 80:
        dust_ev.append(f"Elevated PM10 at {pm10:.1f} µg/m³.")
        dust_score += 30
    if pct_vs_72h.get("pm10") is not None and pct_vs_72h["pm10"] >= 18:
        dust_ev.append(f"PM10 is {pct_vs_72h['pm10']:+.1f}% above the multi-day baseline average.")
        dust_score += 15
    if wind is not None and wind >= 14 and pm10 is not None and pm10 >= 60:
        dust_ev.append(f"Wind speed ({wind:.1f} km/h) can resuspend road and construction dust.")
        dust_score += 20
    if dust_ev and dust_score >= 25:
        candidates.append(
            {
                "source_name": "Possible Contributor: Construction & Road Dust Resuspension",
                "confidence": "High" if dust_score >= 60 else ("Medium" if dust_score >= 40 else "Low"),
                "signal_strength": min(95, dust_score),
                "evidence": dust_ev,
                "data_basis": "Calculated Pattern Inference from PM10/PM2.5 Ratio, Baseline & Wind",
            }
        )

    # 3. Biomass / Open Burning / Fine Combustion Aerosol
    burn_ev = []
    burn_score = 0
    if pm25 is not None and pm10 is not None and pm10 > 0:
        fine_share = pm25 / pm10
        if pm25 >= 35 and fine_share >= 0.65:
            burn_ev.append(f"Fine PM2.5 ({pm25:.1f} µg/m³) accounts for {fine_share * 100:.0f}% of PM10 (typical of smoke/burning/secondary aerosols).")
            burn_score += 40 if pm25 >= 60 else 28
    if co is not None and co >= 550 and pm25 is not None and pm25 >= 35:
        burn_ev.append(f"Co-elevated CO ({co:.0f} µg/m³) alongside fine PM2.5 supports solid/biomass combustion.")
        burn_score += 25
    if pct_vs_72h.get("pm2_5") is not None and pct_vs_72h["pm2_5"] >= 20:
        burn_ev.append(f"PM2.5 is {pct_vs_72h['pm2_5']:+.1f}% above its multi-day average.")
        burn_score += 12
    if (local_hour >= 19 or local_hour <= 6) and pm25 is not None and pm25 >= 35:
        burn_ev.append("Evening/night accumulation aligns with open waste burning or low dispersion.")
        burn_score += 15
    if burn_ev and burn_score >= 25:
        candidates.append(
            {
                "source_name": "Suspected Source: Biomass, Waste Burning & Fine Smoke",
                "confidence": "High" if burn_score >= 60 else ("Medium" if burn_score >= 40 else "Low"),
                "signal_strength": min(95, burn_score),
                "evidence": burn_ev,
                "data_basis": "Calculated Pattern Inference from PM2.5/PM10 Share & CO",
            }
        )

    # 4. Industrial / Sulfur Fuel Plume
    ind_ev = []
    ind_score = 0
    if so2 is not None and so2 >= 15:
        ind_ev.append(f"Elevated SO2 at {so2:.1f} µg/m³ (fossil-fuel / industrial stack indicator).")
        ind_score += 45 if so2 >= 30 else 28
        if no2 is not None and no2 >= 25:
            ind_ev.append(f"Accompanied by NO2 at {no2:.1f} µg/m³.")
            ind_score += 20
    if pct_vs_72h.get("so2") is not None and pct_vs_72h["so2"] >= 25 and (so2 or 0) >= 10:
        ind_ev.append(f"SO2 is {pct_vs_72h['so2']:+.1f}% higher than the multi-day baseline.")
        ind_score += 15
    if ind_ev and ind_score >= 25:
        candidates.append(
            {
                "source_name": "Possible Contributor: Industrial & Stationary Fuel Combustion",
                "confidence": "High" if ind_score >= 60 else ("Medium" if ind_score >= 40 else "Low"),
                "signal_strength": min(95, ind_score),
                "evidence": ind_ev,
                "data_basis": "Calculated Pattern Inference from SO2, NO2 & Historical Spike",
            }
        )

    # 5. Meteorological Trapping / Photochemical Smog
    met_ev = []
    met_score = 0
    if wind is not None and wind <= 7.5 and aqi >= 60:
        met_ev.append(f"Low wind speed ({wind:.1f} km/h) limits horizontal dispersion.")
        met_score += 32
    if humidity is not None and humidity >= 75 and pm25 is not None and pm25 >= 30:
        met_ev.append(f"High relative humidity ({humidity:.0f}%) can promote hygroscopic particle growth and haze.")
        met_score += 22
    if o3 is not None and o3 >= 90:
        met_ev.append(f"Elevated Ozone ({o3:.1f} µg/m³) signals daytime photochemical smog formation.")
        met_score += 30
    if met_ev and met_score >= 25:
        candidates.append(
            {
                "source_name": "Weather Context: Meteorological Stagnation & Secondary Smog",
                "confidence": "High" if met_score >= 60 else ("Medium" if met_score >= 40 else "Low"),
                "signal_strength": min(95, met_score),
                "evidence": met_ev,
                "data_basis": "Calculated Pattern Inference from Wind, Humidity & O3",
            }
        )

    if not candidates:
        candidates.append(
            {
                "source_name": "Low Regional Background (No Dominant Spike)",
                "confidence": "Low",
                "signal_strength": 20,
                "evidence": [
                    f"Current AQI is {aqi} with no dominant pollutant ratio spike above diagnostic thresholds."
                ],
                "data_basis": "Calculated Baseline Check",
            }
        )

    candidates.sort(key=lambda c: c["signal_strength"], reverse=True)
    return {
        "candidates": candidates,
        "historical_comparison": historical_comparison,
        "weather_context": {
            "wind_speed_kmh": wind,
            "humidity_pct": humidity,
            "condition": weather.get("condition"),
            "observation_hour_local": f"{local_hour:02d}:00",
        },
        "methodology_note": (
            "Pollution Source Detection compares current pollutant concentrations against 24-hour and multi-day historical averages, "
            "pollutant ratios (PM2.5/PM10, NO2, CO, SO2, O3), wind/humidity weather context, and commute-hour traffic patterns. "
            "Results identify possible contributors with confidence levels—not verified physical point-source claims."
        ),
    }


def get_insights_data(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> Dict[str, Any]:
    current_data = get_air_quality_data(city=city, lat=lat, lon=lon)
    forecast_data = get_forecast_data(
        city=current_data["location"]["name"],
        lat=current_data["location"]["latitude"],
        lon=current_data["location"]["longitude"],
    )

    fc = forecast_data["forecast_24h"]
    hist = forecast_data["recent_history"]
    cur_aqi = current_data["aqi"]

    # Rate of change analysis
    aqi_3h_ago = hist[-4]["aqi"] if len(hist) >= 4 else (hist[0]["aqi"] if hist else cur_aqi)
    aqi_next_6h = fc[5]["aqi"] if len(fc) >= 6 else (fc[-1]["aqi"] if fc else cur_aqi)
    past_delta = cur_aqi - aqi_3h_ago
    future_delta = aqi_next_6h - cur_aqi

    if future_delta >= 8 or past_delta >= 10:
        trend_status = "Increasing"
        trend_summary = f"Pollution is trending upward (3h past change: {past_delta:+d} AQI; 6h projected change: {future_delta:+d} AQI)."
    elif future_delta <= -8 or past_delta <= -10:
        trend_status = "Decreasing"
        trend_summary = f"Air quality is projected to improve (3h past change: {past_delta:+d} AQI; 6h projected change: {future_delta:+d} AQI)."
    else:
        trend_status = "Stable"
        trend_summary = f"Pollution levels are relatively steady (3h change: {past_delta:+d} AQI; 6h projected change: {future_delta:+d} AQI)."

    peak_period = max(fc, key=lambda x: x["aqi"]) if fc else None
    cleanest_period = min(fc, key=lambda x: x["aqi"]) if fc else None

    hist_24h = hist[-24:] if len(hist) > 24 else hist
    day_vals = [p["aqi"] for p in hist_24h if 6 <= int(p["time"][11:13]) <= 18]
    night_vals = [p["aqi"] for p in hist_24h if not (6 <= int(p["time"][11:13]) <= 18)]
    day_avg = round(sum(day_vals) / len(day_vals), 1) if day_vals else None
    night_avg = round(sum(night_vals) / len(night_vals), 1) if night_vals else None

    observations = []
    if day_avg is not None and night_avg is not None:
        if night_avg > day_avg + 5:
            observations.append(
                f"Over the past 24 hours, nighttime AQI averaged {night_avg} vs daytime {day_avg}, typical of nocturnal boundary-layer trapping."
            )
        elif day_avg > night_avg + 5:
            observations.append(
                f"Daytime AQI averaged {day_avg} vs nighttime {night_avg}, reflecting daytime traffic and photochemical activity."
            )
        else:
            observations.append(
                f"Daytime ({day_avg}) and nighttime ({night_avg}) AQI averages remained closely balanced over the past 24 hours."
            )

    if peak_period:
        observations.append(
            f"Forecast indicates highest exposure around {peak_period['time'][11:16]} (predicted AQI {peak_period['aqi']}, range {peak_period.get('confidence_low')}–{peak_period.get('confidence_high')})."
        )
    if cleanest_period:
        observations.append(
            f"Cleanest predicted outdoor window in the next 24h is around {cleanest_period['time'][11:16]} (predicted AQI {cleanest_period['aqi']})."
        )

    fingerprinting = _analyze_pollution_sources(
        current_data["pollutants"],
        current_data["weather"],
        current_data["recorded_at"],
        cur_aqi,
        hist,
    )

    clean_windows = _build_clean_air_windows(
        fc,
        current_aqi=cur_aqi,
        standard=current_data.get("aqi_standard", "NAQI"),
    )

    return {
        "current": current_data,
        "forecast": forecast_data,
        "source_fingerprinting": fingerprinting,
        "clean_air_windows": clean_windows,
        "rate_analysis": {
            "status": trend_status,
            "past_3h_delta": past_delta,
            "next_6h_delta": future_delta,
            "summary": trend_summary,
        },
        "pattern_analysis": {
            "daytime_avg_aqi": day_avg,
            "nighttime_avg_aqi": night_avg,
            "peak_forecast": peak_period,
            "cleanest_forecast": cleanest_period,
            "observations": observations,
        },
    }


def get_time_machine_data(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    target_date: Optional[str] = None,
    compare_date: Optional[str] = None,
) -> Dict[str, Any]:
    location = resolve_location(city=city, lat=lat, lon=lon)
    if not location:
        raise LookupError(f"Location '{city}' was not found in India.")

    std = str(get_profile_bundle()["preferences"].get("aqi_standard") or "NAQI").upper()
    aq = fetch_air_quality_bundle(location["latitude"], location["longitude"], past_days=31, forecast_days=1)
    hourly = aq.get("hourly") or {}
    times: List[str] = hourly.get("time") or []
    cur_time = (aq.get("current") or {}).get("time") or utc_now_iso()

    us_aqi = hourly.get("us_aqi") or []
    eu_aqi = hourly.get("european_aqi") or []
    pm25 = hourly.get("pm2_5") or []
    pm10 = hourly.get("pm10") or []
    co_arr = hourly.get("carbon_monoxide") or []
    no2 = hourly.get("nitrogen_dioxide") or []
    so2 = hourly.get("sulphur_dioxide") or []
    o3 = hourly.get("ozone") or []

    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for i, t in enumerate(times):
        if t > cur_time:
            continue
        p_snap = {
            "pm2_5": pm25[i] if i < len(pm25) else None,
            "pm10": pm10[i] if i < len(pm10) else None,
            "co": co_arr[i] if i < len(co_arr) else None,
            "no2": no2[i] if i < len(no2) else None,
            "so2": so2[i] if i < len(so2) else None,
            "o3": o3[i] if i < len(o3) else None,
        }
        if std == "EU" and i < len(eu_aqi) and eu_aqi[i] is not None:
            val = eu_aqi[i]
        elif std == "NAQI":
            val = compute_indian_naqi(p_snap)
            if val is None:
                val = us_aqi[i] if i < len(us_aqi) else None
        else:
            val = us_aqi[i] if i < len(us_aqi) else None

        if val is None:
            continue
        d_str = t[:10]
        by_date.setdefault(d_str, []).append(
            {
                "time": t,
                "hour": t[11:16],
                "aqi": int(round(val)),
                "category": classify_aqi(val, standard=std)["category"],
                "pm2_5": p_snap["pm2_5"],
                "pm10": p_snap["pm10"],
                "no2": p_snap["no2"],
                "o3": p_snap["o3"],
            }
        )

    available_dates = sorted(by_date.keys())
    if not available_dates:
        return {
            "location": location,
            "available_dates": [],
            "message": "No historical archive dates returned for this location.",
        }

    sel_target = target_date if (target_date and target_date in by_date) else (available_dates[-2] if len(available_dates) >= 2 else available_dates[-1])
    default_cmp_idx = max(0, available_dates.index(sel_target) - 7)
    sel_compare = compare_date if (compare_date and compare_date in by_date) else available_dates[default_cmp_idx]

    target_series = by_date[sel_target]
    compare_series = by_date[sel_compare]

    def _summarize(series: List[Dict[str, Any]]) -> Dict[str, Any]:
        vals = [x["aqi"] for x in series]
        peak = max(series, key=lambda x: x["aqi"])
        low = min(series, key=lambda x: x["aqi"])
        return {
            "avg_aqi": round(sum(vals) / len(vals), 1),
            "max_aqi": peak["aqi"],
            "peak_hour": peak["hour"],
            "min_aqi": low["aqi"],
            "cleanest_hour": low["hour"],
            "hours_count": len(series),
        }

    t_sum = _summarize(target_series)
    c_sum = _summarize(compare_series)
    delta_avg = round(t_sum["avg_aqi"] - c_sum["avg_aqi"], 1)

    # Check local SQLite snapshots for transparency
    init_db()
    conn = get_db_connection()
    try:
        snap_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM environmental_readings WHERE LOWER(city) = LOWER(?)",
            (location["name"],),
        ).fetchone()["cnt"]
    finally:
        conn.close()

    return {
        "location": location,
        "available_dates": available_dates,
        "target_date": sel_target,
        "compare_date": sel_compare,
        "target_series": target_series,
        "compare_series": compare_series,
        "target_summary": t_sum,
        "compare_summary": c_sum,
        "comparison_delta_avg": delta_avg,
        "replay_frames": target_series,
        "sqlite_snapshots": snap_count,
        "data_classification": "Measured / Historical Archive (Open-Meteo CAMS + SQLite Snapshots)",
        "source": "Open-Meteo Air Quality Historical Archive",
    }


def simulate_what_if(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    traffic_reduction_pct: float = 0.0,
    dust_control_pct: float = 0.0,
    greenery_increase_pct: float = 0.0,
    burning_reduction_pct: float = 0.0,
    industrial_reduction_pct: float = 0.0,
) -> Dict[str, Any]:
    live = get_air_quality_data(city=city, lat=lat, lon=lon)
    std = live.get("aqi_standard", "NAQI")
    base_aqi = float(live["aqi"] or 0)
    p = live["pollutants"]
    base_pm25 = float(p.get("pm2_5") or 0)
    base_pm10 = float(p.get("pm10") or 0)
    base_no2 = float(p.get("no2") or 0)
    base_so2 = float(p.get("so2") or 0)
    base_co = float(p.get("co") or 0)

    t_pct = max(0.0, min(80.0, float(traffic_reduction_pct)))
    d_pct = max(0.0, min(80.0, float(dust_control_pct)))
    g_pct = max(0.0, min(60.0, float(greenery_increase_pct)))
    b_pct = max(0.0, min(90.0, float(burning_reduction_pct)))
    i_pct = max(0.0, min(80.0, float(industrial_reduction_pct)))

    # Conservative atmospheric sensitivity weights (hypothetical scenario only)
    sim_no2 = round(base_no2 * max(0.15, 1.0 - (0.52 * t_pct / 100.0) - (0.24 * i_pct / 100.0) - (0.08 * g_pct / 100.0)), 1)
    sim_so2 = round(base_so2 * max(0.15, 1.0 - (0.68 * i_pct / 100.0) - (0.10 * g_pct / 100.0)), 1)
    sim_co = round(base_co * max(0.20, 1.0 - (0.42 * t_pct / 100.0) - (0.28 * b_pct / 100.0) - (0.12 * i_pct / 100.0)), 1)
    sim_pm25 = round(
        base_pm25
        * max(
            0.20,
            1.0
            - (0.22 * t_pct / 100.0)
            - (0.12 * d_pct / 100.0)
            - (0.11 * g_pct / 100.0)
            - (0.24 * b_pct / 100.0)
            - (0.20 * i_pct / 100.0),
        ),
        1,
    )
    sim_pm10 = round(
        base_pm10
        * max(
            0.20,
            1.0
            - (0.16 * t_pct / 100.0)
            - (0.40 * d_pct / 100.0)
            - (0.13 * g_pct / 100.0)
            - (0.14 * b_pct / 100.0)
            - (0.14 * i_pct / 100.0),
        ),
        1,
    )

    aqi_reduction_fraction = (
        (0.22 * t_pct / 100.0)
        + (0.17 * d_pct / 100.0)
        + (0.11 * g_pct / 100.0)
        + (0.19 * b_pct / 100.0)
        + (0.21 * i_pct / 100.0)
    )
    aqi_reduction_fraction = min(0.72, aqi_reduction_fraction)
    sim_aqi = max(5, int(round(base_aqi * (1.0 - aqi_reduction_fraction))))
    aqi_delta = sim_aqi - int(round(base_aqi))
    pct_change = round((aqi_delta / base_aqi) * 100.0, 1) if base_aqi > 0 else 0.0

    assumptions = [
        f"Traffic reduction ({t_pct:.0f}%): modeled with 52% NO2 sensitivity, 42% CO, and 22% regional PM2.5 reduction.",
        f"Construction dust control ({d_pct:.0f}%): modeled with 40% coarse PM10 and 12% fine PM2.5 suppression.",
        f"Industrial emissions cut ({i_pct:.0f}%): modeled with 68% SO2, 24% NO2, and 20% primary/secondary PM2.5 sensitivity.",
        f"Green cover increase ({g_pct:.0f}%): conservative 11–13% particulate deposition & micro-dispersion weight.",
    ]
    if b_pct > 0:
        assumptions.append(f"Open burning reduction ({b_pct:.0f}%): 24% PM2.5 & 28% CO smoke sensitivity.")

    if aqi_delta == 0:
        impact_explanation = "No intervention sliders adjusted yet. Move any policy control above 0% to inspect projected sensitivity."
    else:
        impact_explanation = (
            f"Under this hypothetical scenario in {live['location']['name']}, composite {std} AQI shifts from "
            f"{int(round(base_aqi))} ({live['classification']['category']}) to {sim_aqi} ({classify_aqi(sim_aqi, standard=std)['category']}), "
            f"a {abs(pct_change):.1f}% reduction driven by combined PM2.5 ({base_pm25:.1f} → {sim_pm25:.1f} µg/m³), "
            f"PM10 ({base_pm10:.1f} → {sim_pm10:.1f} µg/m³), and NO2/SO2 abatement."
        )

    return {
        "is_hypothetical": True,
        "simulation_badge": "HYPOTHETICAL SCENARIO — NOT MEASURED OR FORECAST DATA",
        "disclaimer": (
            "All simulated values below are hypothetical sensitivity estimates computed from your selected scenario sliders "
            "against current live baseline readings. They do NOT represent actual measured improvements."
        ),
        "location": live["location"],
        "aqi_standard": std,
        "inputs": {
            "traffic_reduction_pct": t_pct,
            "dust_control_pct": d_pct,
            "greenery_increase_pct": g_pct,
            "burning_reduction_pct": b_pct,
            "industrial_reduction_pct": i_pct,
        },
        "assumptions": assumptions,
        "impact_explanation": impact_explanation,
        "comparison_chart_series": {
            "labels": ["Composite AQI", "PM2.5 (µg/m³)", "PM10 (µg/m³)", "NO2 (µg/m³)", "SO2 (µg/m³)"],
            "baseline": [int(round(base_aqi)), base_pm25, base_pm10, base_no2, base_so2],
            "simulated": [sim_aqi, sim_pm25, sim_pm10, sim_no2, sim_so2],
        },
        "baseline": {
            "aqi": int(round(base_aqi)),
            "category": live["classification"]["category"],
            "pm2_5": base_pm25,
            "pm10": base_pm10,
            "no2": base_no2,
            "so2": base_so2,
            "co": base_co,
        },
        "simulated": {
            "aqi": sim_aqi,
            "category": classify_aqi(sim_aqi, standard=std)["category"],
            "pm2_5": sim_pm25,
            "pm10": sim_pm10,
            "no2": sim_no2,
            "so2": sim_so2,
            "co": sim_co,
            "aqi_delta": aqi_delta,
            "pct_change": pct_change,
        },
    }


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _sample_route_coordinates(coords: List[List[float]], count: int = 5) -> List[List[float]]:
    if not coords:
        return []
    if len(coords) <= count or count <= 1:
        return coords if count > 1 else [coords[0]]
    step = (len(coords) - 1) / float(count - 1)
    indices = [int(round(i * step)) for i in range(count)]
    return [coords[idx] for idx in indices]


def get_clean_routes(
    origin: str,
    destination: str,
    mode: str = "walking",
    escape_mode: bool = False,
) -> Dict[str, Any]:
    if not origin or not destination:
        raise ValueError("Both starting location and destination are required.")

    orig_loc = resolve_location(city=origin)
    dest_loc = resolve_location(city=destination)
    if not orig_loc:
        raise LookupError(f"Starting location '{origin}' was not found in India. Please enter an Indian city or neighborhood.")
    if not dest_loc:
        raise LookupError(f"Destination '{destination}' was not found in India. Please enter an Indian city or neighborhood.")

    mode_clean = mode.lower().strip()
    if mode_clean not in ("walking", "cycling", "driving"):
        mode_clean = "walking"

    osrm_profile = {"walking": "foot", "cycling": "bike", "driving": "driving"}[mode_clean]
    osrm_url = (
        f"https://router.project-osrm.org/route/v1/{osrm_profile}/"
        f"{orig_loc['longitude']},{orig_loc['latitude']};"
        f"{dest_loc['longitude']},{dest_loc['latitude']}"
        "?overview=full&alternatives=true&geometries=geojson"
    )

    try:
        osrm_data = _http_get_json(osrm_url)
    except Exception as exc:
        raise RuntimeError(f"Routing service unavailable: {exc}") from exc

    raw_routes = osrm_data.get("routes") or []
    if not raw_routes:
        raise LookupError("No navigable route was found between those two points.")

    # Gather active community incident updates and geolocated hotspots near origin/destination
    init_db()
    conn = get_db_connection()
    nearby_incidents: List[Dict[str, Any]] = []
    incident_updates: List[Dict[str, Any]] = []
    try:
        rows = conn.execute(
            """
            SELECT id, report_code, title, category, location_name, latitude, longitude, status, created_at
            FROM community_reports
            WHERE status != 'Rejected' AND status != 'Resolved'
            ORDER BY id DESC LIMIT 40
            """
        ).fetchall()
        orig_city_l = (orig_loc.get("name") or "").lower()
        dest_city_l = (dest_loc.get("name") or "").lower()
        for r in rows:
            loc_l = (r["location_name"] or "").lower()
            is_near = False
            if r["latitude"] is not None and r["longitude"] is not None:
                d_orig = _haversine_km(orig_loc["latitude"], orig_loc["longitude"], r["latitude"], r["longitude"])
                d_dest = _haversine_km(dest_loc["latitude"], dest_loc["longitude"], r["latitude"], r["longitude"])
                is_near = min(d_orig, d_dest) <= 45.0
            elif (orig_city_l and orig_city_l in loc_l) or (dest_city_l and dest_city_l in loc_l):
                is_near = True

            item = {
                "id": r["id"],
                "report_code": r["report_code"],
                "title": r["title"],
                "category": r["category"],
                "location_name": r["location_name"],
                "lat": r["latitude"],
                "lon": r["longitude"],
                "status": r["status"],
                "is_verified": r["status"] == "Verified",
                "hotspot_type": "Verified Incident" if r["status"] == "Verified" else "Citizen Report",
                "created_at": r["created_at"],
            }
            if is_near and r["latitude"] is not None and r["longitude"] is not None:
                nearby_incidents.append(item)
            if is_near or len(incident_updates) < 4:
                incident_updates.append(item)
    finally:
        conn.close()

    # Ensure at least 2 real OSRM corridor candidates (Ordinary + Safe Air detour if OSRM returns only 1)
    candidate_raw_routes = list(raw_routes[:2])
    if len(candidate_raw_routes) == 1:
        dlat = dest_loc["latitude"] - orig_loc["latitude"]
        dlon = dest_loc["longitude"] - orig_loc["longitude"]
        span = math.hypot(dlat, dlon)
        if span > 0.004:
            # Perpendicular normalized vector shifted slightly to avoid exact overlap
            offset = min(0.038, max(0.008, span * 0.22))
            px = (-dlat / span) * offset
            py = (dlon / span) * offset
            mid_lat = (orig_loc["latitude"] + dest_loc["latitude"]) / 2.0
            mid_lon = (orig_loc["longitude"] + dest_loc["longitude"]) / 2.0
            for sign in (1.0, -1.0):
                wp_lat = mid_lat + sign * py
                wp_lon = mid_lon + sign * px
                detour_url = (
                    f"https://router.project-osrm.org/route/v1/{osrm_profile}/"
                    f"{orig_loc['longitude']:.5f},{orig_loc['latitude']:.5f};"
                    f"{wp_lon:.5f},{wp_lat:.5f};"
                    f"{dest_loc['longitude']:.5f},{dest_loc['latitude']:.5f}"
                    "?overview=full&geometries=geojson"
                )
                try:
                    detour_data = _http_get_json(detour_url)
                    detour_routes = detour_data.get("routes") or []
                    if detour_routes:
                        cand = detour_routes[0]
                        base_dist = candidate_raw_routes[0].get("distance", 0)
                        if cand.get("distance", 0) > 0 and abs(cand["distance"] - base_dist) >= 50:
                            candidate_raw_routes.append(cand)
                            break
                except Exception:
                    continue

    pref_std = get_profile_bundle().get("preferences", {}).get("aqi_standard", "NAQI").upper()
    if pref_std not in ("NAQI", "US", "EU"):
        pref_std = "NAQI"

    routes_out = []
    measured_hotspots: List[Dict[str, Any]] = []

    for idx, r in enumerate(candidate_raw_routes[:2]):
        distance_km = round(r["distance"] / 1000.0, 2)
        if mode_clean == "walking":
            duration_min = max(1, int(round((distance_km / 4.8) * 60.0)))
        elif mode_clean == "cycling":
            duration_min = max(1, int(round((distance_km / 15.0) * 60.0)))
        else:
            duration_min = max(1, int(round(r["duration"] / 60.0)))

        coords = r["geometry"]["coordinates"]
        samples = _sample_route_coordinates(coords, count=5)

        lats = ",".join(f"{pt[1]:.4f}" for pt in samples)
        lons = ",".join(f"{pt[0]:.4f}" for pt in samples)
        waypoint_aqi_list = []
        try:
            aq_url = (
                "https://air-quality-api.open-meteo.com/v1/air-quality"
                f"?latitude={lats}&longitude={lons}"
                "&current=us_aqi,european_aqi,pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,ozone"
            )
            aq_resp = _http_get_json(aq_url)
            aq_items = aq_resp if isinstance(aq_resp, list) else [aq_resp]
            for pt_idx, item in enumerate(aq_items):
                cur = item.get("current") or {}
                if pref_std == "NAQI":
                    aqi_v = compute_indian_naqi(
                        {
                            "pm2_5": cur.get("pm2_5"),
                            "pm10": cur.get("pm10"),
                            "no2": cur.get("nitrogen_dioxide"),
                            "so2": cur.get("sulphur_dioxide"),
                            "co": cur.get("carbon_monoxide"),
                            "o3": cur.get("ozone"),
                        }
                    )
                    if aqi_v is None:
                        aqi_v = cur.get("us_aqi")
                elif pref_std == "EU":
                    aqi_v = cur.get("european_aqi")
                else:
                    aqi_v = cur.get("us_aqi")

                if aqi_v is not None:
                    waypoint_aqi_list.append(
                        {
                            "lat": samples[pt_idx][1],
                            "lon": samples[pt_idx][0],
                            "aqi": int(round(aqi_v)),
                            "pm2_5": cur.get("pm2_5"),
                            "pm10": cur.get("pm10"),
                            "category": classify_aqi(aqi_v, standard=pref_std)["category"],
                        }
                    )
        except Exception:
            waypoint_aqi_list = []

        avg_aqi = (
            round(sum(w["aqi"] for w in waypoint_aqi_list) / len(waypoint_aqi_list), 1)
            if waypoint_aqi_list
            else None
        )
        max_aqi = max((w["aqi"] for w in waypoint_aqi_list), default=None)
        exposure_index = round((avg_aqi * duration_min) / 60.0, 1) if avg_aqi is not None else None
        hotspots = [w for w in waypoint_aqi_list if w["aqi"] > 100 or (max_aqi is not None and w["aqi"] == max_aqi and max_aqi > 50)]
        for hw in waypoint_aqi_list:
            if hw["aqi"] > 100:
                measured_hotspots.append(
                    {
                        "lat": hw["lat"],
                        "lon": hw["lon"],
                        "aqi": hw["aqi"],
                        "category": hw["category"],
                        "hotspot_type": "Elevated AQI Zone",
                        "is_verified": True,
                        "title": f"High AQI Spot ({hw['aqi']} {hw['category']})",
                    }
                )

        # Check proximity to reported incidents
        route_incident_hits = 0
        for inc in nearby_incidents:
            for pt in samples:
                if _haversine_km(pt[1], pt[0], inc["lat"], inc["lon"]) <= 2.5:
                    route_incident_hits += 1
                    break

        routes_out.append(
            {
                "id": f"route_{idx + 1}",
                "route_type": "ordinary" if idx == 0 else "safe_air",
                "label": "Ordinary Route" if idx == 0 else "Safe Air Route",
                "distance_km": distance_km,
                "duration_min": duration_min,
                "geometry": r["geometry"],
                "waypoints": waypoint_aqi_list,
                "avg_aqi": avg_aqi,
                "max_aqi": max_aqi,
                "exposure_index": exposure_index,
                "hotspots": hotspots,
                "incident_hits": route_incident_hits,
                "is_recommended": False,
                "recommendation_reason": "",
            }
        )

    # Assign Ordinary Route (fastest direct) vs Safe Air Route (cleanest / fewest hotspots)
    if len(routes_out) >= 2:
        ordinary = min(routes_out, key=lambda x: (x["duration_min"], x["distance_km"]))
        safe_air = next(r for r in routes_out if r is not ordinary)
        # Swap if the other candidate is strictly cleaner or avoids incidents when in escape mode
        cleanest = min(
            routes_out,
            key=lambda x: (
                x["incident_hits"],
                x["avg_aqi"] if x["avg_aqi"] is not None else 999,
                x["max_aqi"] if x["max_aqi"] is not None else 999,
                x["duration_min"],
            ),
        )
        if cleanest is ordinary and not escape_mode:
            # Keep direct fastest as Ordinary and secondary as Safe Air / Alternate, recommending the lower-AQI one
            ordinary["route_type"] = "ordinary"
            ordinary["label"] = "Ordinary Route"
            safe_air["route_type"] = "safe_air"
            safe_air["label"] = "Safe Air Route"
            ordinary["is_recommended"] = True
            ordinary["recommendation_reason"] = "Direct path currently matches lowest regional AQI and shortest time."
            safe_air["recommendation_reason"] = "Alternate corridor avoiding main arterial intersections."
        else:
            cleanest["route_type"] = "safe_air"
            cleanest["label"] = "Safe Air Route"
            cleanest["is_recommended"] = True
            other = next(r for r in routes_out if r is not cleanest)
            other["route_type"] = "ordinary"
            other["label"] = "Ordinary Route"
            other["is_recommended"] = False
            other["recommendation_reason"] = "Standard direct corridor."
            cleanest["recommendation_reason"] = (
                f"Lowest hotspot hits ({cleanest['incident_hits']}) and cleaner air corridor."
                if escape_mode or cleanest["incident_hits"] < other["incident_hits"]
                else "Cleaner corridor option with lower sampled exposure."
            )
        # Present Ordinary first, Safe Air second for clear side-by-side comparison
        routes_out = [
            next(r for r in routes_out if r["route_type"] == "ordinary"),
            next(r for r in routes_out if r["route_type"] == "safe_air"),
        ]
        ord_r, safe_r = routes_out[0], routes_out[1]
        ord_aqi_txt = ord_r["avg_aqi"] if ord_r["avg_aqi"] is not None else "N/A"
        safe_aqi_txt = safe_r["avg_aqi"] if safe_r["avg_aqi"] is not None else "N/A"
        recommendation_note = (
            f"Ordinary Route: {ord_r['duration_min']} min (AQI {ord_aqi_txt}) · "
            f"Safe Air Route: {safe_r['duration_min']} min (AQI {safe_aqi_txt})."
        )
    elif routes_out:
        routes_out[0]["route_type"] = "safe_air"
        routes_out[0]["label"] = "Safe Air Route"
        routes_out[0]["is_recommended"] = True
        routes_out[0]["recommendation_reason"] = "Only navigable corridor returned for this distance."
        recommendation_note = f"Route duration: {routes_out[0]['duration_min']} min ({routes_out[0]['distance_km']} km)."
    else:
        recommendation_note = "No routes available."

    best_window = None
    clean_air_windows: List[Dict[str, Any]] = []
    try:
        fc = get_forecast_data(lat=orig_loc["latitude"], lon=orig_loc["longitude"])
        fc_pts = fc.get("forecast_24h") or []
        if fc_pts:
            cleanest = min(fc_pts, key=lambda x: x["aqi"])
            best_window = {
                "time": cleanest["time"],
                "aqi": cleanest["aqi"],
                "category": cleanest["category"],
            }
            clean_air_windows = _build_clean_air_windows(fc_pts, standard=fc.get("aqi_standard", "NAQI"))
    except Exception:
        best_window = None

    destination_air = None
    try:
        dest_live = get_air_quality_data(lat=dest_loc["latitude"], lon=dest_loc["longitude"])
        destination_air = {
            "aqi": dest_live.get("aqi"),
            "category": (dest_live.get("classification") or {}).get("category"),
            "level": (dest_live.get("classification") or {}).get("level"),
            "temperature": (dest_live.get("weather") or {}).get("temperature"),
            "temp_unit": (dest_live.get("weather") or {}).get("temp_unit", "°C"),
            "condition": (dest_live.get("weather") or {}).get("condition"),
        }
    except Exception:
        destination_air = None

    all_hotspots = nearby_incidents + measured_hotspots

    return {
        "origin": orig_loc,
        "destination": dest_loc,
        "destination_air": destination_air,
        "mode": mode_clean,
        "aqi_standard": pref_std,
        "escape_mode": bool(escape_mode),
        "routes": routes_out,
        "hotspot_zones": all_hotspots,
        "incident_updates": incident_updates[:8],
        "emergency_escape": {
            "active": bool(escape_mode),
            "nearby_hotspot_count": len(all_hotspots),
            "verified_or_measured_count": sum(1 for h in all_hotspots if h.get("is_verified")),
            "unverified_report_count": sum(1 for h in all_hotspots if not h.get("is_verified")),
            "advice": (
                f"{len(all_hotspots)} active hotspot(s) near route."
                if all_hotspots
                else "No high-AQI hotspots or reported incidents along route."
            ),
        },
        "clean_air_windows": clean_air_windows,
        "recommendation_note": recommendation_note,
        "data_limitation_note": "Regional Open-Meteo grid + OSRM routing + local community incidents.",
        "best_travel_time": best_window,
        "source": "OSRM + Open-Meteo + SQLite",
    }


def get_alerts_data(city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
    live = get_air_quality_data(city=city, lat=lat, lon=lon)
    bundle = get_profile_bundle()

    init_db()
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM environmental_alerts ORDER BY id DESC LIMIT 40"
        ).fetchall()
        history = [dict(r) for r in rows]

        inc_rows = conn.execute(
            """
            SELECT id, report_code, title, category, location_name, status, latitude, longitude, created_at
            FROM community_reports
            WHERE status IN ('Verified', 'Under Review', 'Submitted')
            ORDER BY CASE WHEN status = 'Verified' THEN 0 ELSE 1 END, id DESC
            LIMIT 12
            """
        ).fetchall()
        hotspot_updates = [
            {
                **dict(r),
                "is_verified": r["status"] == "Verified",
                "verification_label": "Verified Hotspot" if r["status"] == "Verified" else f"Unverified Citizen Report ({r['status']})",
            }
            for r in inc_rows
        ]
    finally:
        conn.close()

    pol = live.get("pollutants") or {}
    wth = live.get("weather") or {}
    pm25_v = pol.get("pm2_5")
    pm10_v = pol.get("pm10")
    wind_v = wth.get("wind_speed")
    reason_parts = []
    if pm25_v is not None and pm25_v > 60:
        reason_parts.append(f"Elevated PM2.5 ({pm25_v:.1f} µg/m³)")
    elif pm10_v is not None and pm10_v > 100:
        reason_parts.append(f"High coarse dust PM10 ({pm10_v:.1f} µg/m³)")
    if wind_v is not None and wind_v < 8:
        reason_parts.append(f"low wind dispersion ({wind_v:.1f} km/h)")
    if not reason_parts:
        reason_parts.append(f"Regional traffic, urban dust & weather ({wth.get('condition') or 'Clear'})")

    cur_aqi_val = float(live.get("aqi") or 0)
    aqi_comp = min(70.0, (cur_aqi_val / 400.0) * 70.0)
    pm_comp = min(20.0, (float(pm25_v or 0) / 120.0) * 20.0)
    hs_comp = min(10.0, len(hotspot_updates) * 2.0)
    alert_risk_score = max(1, min(100, int(round(aqi_comp + pm_comp + hs_comp))))
    if alert_risk_score >= 76:
        alert_risk_level = "Very High Risk"
    elif alert_risk_score >= 51:
        alert_risk_level = "High Risk"
    elif alert_risk_score >= 26:
        alert_risk_level = "Moderate Risk"
    else:
        alert_risk_level = "Low Risk"
    alert_risk_explain = (
        f"Risk Score {alert_risk_score}/100 ({alert_risk_level}): Calculated from live AQI ({int(round(cur_aqi_val))}), "
        f"PM2.5 ({f'{pm25_v:.1f}' if pm25_v is not None else 'N/A'} µg/m³), and {len(hotspot_updates)} nearby citizen report(s). "
        "Scale: 0–25 Low · 26–50 Moderate · 51–75 High · 76–100 Very High."
    )

    return {
        "location": live["location"],
        "current_aqi": live["aqi"],
        "classification": live["classification"],
        "pollutants": live["pollutants"],
        "weather": wth,
        "alert_reason": " and ".join(reason_parts),
        "risk_score": alert_risk_score,
        "risk_level": alert_risk_level,
        "risk_explanation": alert_risk_explain,
        "live_alerts": live["active_alerts"],
        "hotspot_updates": hotspot_updates,
        "alert_history": history,
        "notification_preferences": bundle["notifications"],
        "recorded_at": live["recorded_at"],
        "source": live["source"],
    }


def _extract_history_series(
    location: Dict[str, Any],
    period_clean: str,
    start_date: Optional[str],
    end_date: Optional[str],
    std: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    past_days = {"daily": 1, "weekly": 7, "monthly": 30, "custom": 31}[period_clean]
    aq = fetch_air_quality_bundle(location["latitude"], location["longitude"], past_days=past_days, forecast_days=1)
    hourly = aq.get("hourly") or {}
    times: List[str] = hourly.get("time") or []
    cur_time = (aq.get("current") or {}).get("time") or utc_now_iso()

    us_aqi = hourly.get("us_aqi") or []
    eu_aqi = hourly.get("european_aqi") or []
    pm25 = hourly.get("pm2_5") or []
    pm10 = hourly.get("pm10") or []
    co = hourly.get("carbon_monoxide") or []
    no2 = hourly.get("nitrogen_dioxide") or []
    so2 = hourly.get("sulphur_dioxide") or []
    o3 = hourly.get("ozone") or []

    records = []
    for i, t in enumerate(times):
        if t > cur_time:
            continue
        d_str = t[:10]
        if start_date and d_str < start_date:
            continue
        if end_date and d_str > end_date:
            continue
        p_snap = {
            "pm2_5": pm25[i] if i < len(pm25) else None,
            "pm10": pm10[i] if i < len(pm10) else None,
            "co": co[i] if i < len(co) else None,
            "no2": no2[i] if i < len(no2) else None,
            "so2": so2[i] if i < len(so2) else None,
            "o3": o3[i] if i < len(o3) else None,
        }
        if std == "EU" and i < len(eu_aqi) and eu_aqi[i] is not None:
            val = eu_aqi[i]
        elif std == "NAQI":
            val = compute_indian_naqi(p_snap)
            if val is None:
                val = us_aqi[i] if i < len(us_aqi) else None
        else:
            val = us_aqi[i] if i < len(us_aqi) else None

        if val is None:
            continue
        records.append(
            {
                "time": t,
                "date": d_str,
                "aqi": int(round(val)),
                **p_snap,
            }
        )

    if period_clean == "daily" and not start_date and not end_date:
        records = records[-24:]

    daily_buckets: Dict[str, List[Dict[str, Any]]] = {}
    for rec in records:
        daily_buckets.setdefault(rec["date"], []).append(rec)

    series = []
    if period_clean == "daily" and not start_date and not end_date:
        series = records
    else:
        for d_key in sorted(daily_buckets.keys()):
            items = daily_buckets[d_key]

            def avg_col(k: str) -> Optional[float]:
                vals = [x[k] for x in items if x[k] is not None]
                return round(sum(vals) / len(vals), 2) if vals else None

            series.append(
                {
                    "time": d_key,
                    "date": d_key,
                    "aqi": round(sum(x["aqi"] for x in items) / len(items), 1),
                    "pm2_5": avg_col("pm2_5"),
                    "pm10": avg_col("pm10"),
                    "co": avg_col("co"),
                    "no2": avg_col("no2"),
                    "so2": avg_col("so2"),
                    "o3": avg_col("o3"),
                }
            )
    return records, series


def get_reports_data(
    city: Optional[str] = None,
    period: str = "daily",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    compare_city: Optional[str] = None,
) -> Dict[str, Any]:
    period_clean = period.lower().strip()
    if period_clean not in ("daily", "weekly", "monthly", "custom"):
        period_clean = "daily"

    location = resolve_location(city=city, lat=lat, lon=lon)
    if not location:
        raise LookupError(f"Location '{city}' was not found in India. VayuMitra supports Indian cities only.")

    std = str(get_profile_bundle()["preferences"].get("aqi_standard") or "NAQI").upper()
    records, series = _extract_history_series(location, period_clean, start_date, end_date, std)

    sufficient = len(records) >= 4
    if not sufficient:
        return {
            "location": location,
            "aqi_standard": std,
            "period": period_clean,
            "start_date": start_date,
            "end_date": end_date,
            "generated_at": utc_now_iso(),
            "sufficient_data": False,
            "message": "Insufficient historical records returned for the selected date range (Open-Meteo archive retains ~31 days).",
            "summary": None,
            "comparison": None,
            "series": [],
            "records": [],
            "hotspot_analysis": [],
            "evidence_records": [],
            "source": "Open-Meteo Air Quality Historical Archive",
        }

    aqi_vals = [r["aqi"] for r in records]
    avg_aqi = round(sum(aqi_vals) / len(aqi_vals), 1)
    max_rec = max(records, key=lambda r: r["aqi"])
    min_rec = min(records, key=lambda r: r["aqi"])
    net_change = records[-1]["aqi"] - records[0]["aqi"]

    def avg_metric(k: str) -> Optional[float]:
        vals = [r[k] for r in records if r[k] is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    pollutant_averages = {
        "pm2_5": avg_metric("pm2_5"),
        "pm10": avg_metric("pm10"),
        "co": avg_metric("co"),
        "no2": avg_metric("no2"),
        "so2": avg_metric("so2"),
        "o3": avg_metric("o3"),
    }

    avg_cls = classify_aqi(avg_aqi, standard=std)
    elevated_hours = sum(1 for v in aqi_vals if v > 100)
    observations = [
        f"Mean {std} AQI over the selected window was {avg_aqi} ({avg_cls['category']}) across {len(records)} hourly points.",
        f"Highest recorded AQI was {max_rec['aqi']} at {max_rec['time'].replace('T', ' ')}; lowest was {min_rec['aqi']} at {min_rec['time'].replace('T', ' ')}.",
        f"Net AQI change from start to end of window: {net_change:+d} points ({elevated_hours} hour(s) exceeded AQI 100).",
    ]

    comparison_payload = None
    cmp_query = (compare_city or "").strip()
    if cmp_query:
        cmp_loc = resolve_location(city=cmp_query)
        if not cmp_loc:
            raise LookupError(f"Comparison location '{cmp_query}' was not found in India.")
        cmp_records, cmp_series = _extract_history_series(cmp_loc, period_clean, start_date, end_date, std)
        if len(cmp_records) >= 4:
            cmp_vals = [r["aqi"] for r in cmp_records]
            cmp_avg = round(sum(cmp_vals) / len(cmp_vals), 1)
            cmp_pm25_vals = [r["pm2_5"] for r in cmp_records if r["pm2_5"] is not None]
            cmp_avg_pm25 = round(sum(cmp_pm25_vals) / len(cmp_pm25_vals), 1) if cmp_pm25_vals else None
            diff_avg = round(avg_aqi - cmp_avg, 1)
            comparison_payload = {
                "location": cmp_loc,
                "average_aqi": cmp_avg,
                "average_category": classify_aqi(cmp_avg, standard=std)["category"],
                "highest_aqi": max(cmp_vals),
                "lowest_aqi": min(cmp_vals),
                "average_pm25": cmp_avg_pm25,
                "delta_vs_primary": diff_avg,
                "comparison_note": (
                    f"{location['name']} averaged {abs(diff_avg)} AQI points "
                    f"{'higher' if diff_avg > 0 else 'lower'} than {cmp_loc['name']} during this period."
                    if diff_avg != 0
                    else f"{location['name']} and {cmp_loc['name']} had identical average AQI ({avg_aqi})."
                ),
                "series": cmp_series,
            }
            observations.append(comparison_payload["comparison_note"])

    # Top hotspot hours & community evidence records
    top_hotspot_hours = sorted(records, key=lambda r: r["aqi"], reverse=True)[:5]

    init_db()
    conn = get_db_connection()
    try:
        db_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM environmental_readings WHERE LOWER(city) = LOWER(?)",
            (location["name"],),
        ).fetchone()["cnt"]
        rep_rows = conn.execute(
            """
            SELECT r.id, r.report_code, r.title, r.category, r.location_name, r.status, r.created_at, u.stored_filename
            FROM community_reports r
            LEFT JOIN report_uploads u ON u.report_id = r.id
            ORDER BY r.id DESC LIMIT 20
            """
        ).fetchall()
        evidence_records = [
            {
                "id": rr["id"],
                "report_code": rr["report_code"],
                "title": rr["title"],
                "category": LEGACY_CATEGORY_MAP.get(rr["category"], rr["category"]),
                "location_name": rr["location_name"],
                "status": rr["status"],
                "is_verified": rr["status"] in ("Verified", "Resolved"),
                "photo_url": f"/uploads/{rr['stored_filename']}" if rr["stored_filename"] else None,
                "created_at": rr["created_at"],
                "classification_tag": "Reported (Citizen Evidence)",
            }
            for rr in rep_rows
        ]
    finally:
        conn.close()

    try:
        air_twin_preview = get_air_twin_data(include_live=False)
    except Exception:
        air_twin_preview = None

    top_polluted_cities: List[Dict[str, Any]] = []
    try:
        city_benchmarks = [
            {"name": "Delhi", "state": "Delhi NCR", "lat": 28.6139, "lon": 77.2090},
            {"name": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lon": 72.8777},
            {"name": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lon": 88.3639},
            {"name": "Patna", "state": "Bihar", "lat": 25.5941, "lon": 85.1376},
            {"name": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8467, "lon": 80.9462},
            {"name": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lon": 72.5714},
            {"name": "Pune", "state": "Maharashtra", "lat": 18.5204, "lon": 73.8567},
            {"name": "Bengaluru", "state": "Karnataka", "lat": 12.9716, "lon": 77.5946},
            {"name": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lon": 78.4867},
            {"name": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707},
        ]
        lats_q = ",".join(f"{c['lat']:.4f}" for c in city_benchmarks)
        lons_q = ",".join(f"{c['lon']:.4f}" for c in city_benchmarks)
        batch_url = (
            "https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lats_q}&longitude={lons_q}"
            "&current=us_aqi,european_aqi,pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,ozone"
        )
        batch_resp = _http_get_json(batch_url, cache_ttl=120)
        batch_items = batch_resp if isinstance(batch_resp, list) else [batch_resp]
        for idx_c, item_c in enumerate(batch_items):
            if idx_c >= len(city_benchmarks):
                break
            cur_c = item_c.get("current") or {}
            if std == "EU":
                c_aqi = cur_c.get("european_aqi")
            elif std == "US":
                c_aqi = cur_c.get("us_aqi")
            else:
                c_aqi = compute_indian_naqi(
                    {
                        "pm2_5": cur_c.get("pm2_5"),
                        "pm10": cur_c.get("pm10"),
                        "no2": cur_c.get("nitrogen_dioxide"),
                        "so2": cur_c.get("sulphur_dioxide"),
                        "co": cur_c.get("carbon_monoxide"),
                        "o3": cur_c.get("ozone"),
                    }
                )
                if c_aqi is None:
                    c_aqi = cur_c.get("us_aqi")
            if c_aqi is not None:
                c_aqi_int = int(round(c_aqi))
                c_cls = classify_aqi(c_aqi_int, standard=std)
                top_polluted_cities.append(
                    {
                        "city": city_benchmarks[idx_c]["name"],
                        "state": city_benchmarks[idx_c]["state"],
                        "aqi": c_aqi_int,
                        "category": c_cls["category"],
                        "pm2_5": round(cur_c["pm2_5"], 1) if cur_c.get("pm2_5") is not None else None,
                        "pm10": round(cur_c["pm10"], 1) if cur_c.get("pm10") is not None else None,
                    }
                )
        top_polluted_cities.sort(key=lambda x: x["aqi"], reverse=True)
    except Exception:
        top_polluted_cities = []

    return {
        "location": location,
        "aqi_standard": std,
        "period": period_clean,
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": utc_now_iso(),
        "sufficient_data": True,
        "record_count": len(records),
        "stored_db_snapshots": db_count,
        "data_classifications": {
            "historical_aqi_series": f"Measured / Regional Historical Archive ({std})",
            "community_evidence": "Reported (Citizen Evidence)",
            "period_averages_and_exposure": "Calculated",
        },
        "summary": {
            "average_aqi": avg_aqi,
            "average_category": avg_cls["category"],
            "highest_aqi": max_rec["aqi"],
            "highest_time": max_rec["time"],
            "lowest_aqi": min_rec["aqi"],
            "lowest_time": min_rec["time"],
            "net_change": net_change,
            "elevated_hours": elevated_hours,
            "risk_score": max(
                1,
                min(
                    100,
                    int(
                        round(
                            min(70.0, (avg_aqi / 400.0) * 70.0)
                            + ((elevated_hours / max(1, len(records))) * 20.0)
                            + min(10.0, (max_rec["aqi"] / 400.0) * 10.0)
                        )
                    ),
                ),
            ),
            "risk_level": (
                "Very High Risk"
                if (min(70.0, (avg_aqi / 400.0) * 70.0) + ((elevated_hours / max(1, len(records))) * 20.0) + min(10.0, (max_rec["aqi"] / 400.0) * 10.0)) >= 76
                else (
                    "High Risk"
                    if (min(70.0, (avg_aqi / 400.0) * 70.0) + ((elevated_hours / max(1, len(records))) * 20.0) + min(10.0, (max_rec["aqi"] / 400.0) * 10.0)) >= 51
                    else (
                        "Moderate Risk"
                        if (min(70.0, (avg_aqi / 400.0) * 70.0) + ((elevated_hours / max(1, len(records))) * 20.0) + min(10.0, (max_rec["aqi"] / 400.0) * 10.0)) >= 26
                        else "Low Risk"
                    )
                )
            ),
            "risk_explanation": (
                f"Computed from mean AQI ({avg_aqi}), peak AQI ({max_rec['aqi']}), and {elevated_hours}/{len(records)} hours exceeding AQI 100. "
                "Scale: 0–25 Low · 26–50 Moderate · 51–75 High · 76–100 Very High."
            ),
            "pollutant_averages": pollutant_averages,
            "observations": observations,
        },
        "comparison": comparison_payload,
        "hotspot_analysis": top_hotspot_hours,
        "top_polluted_cities": top_polluted_cities,
        "evidence_records": evidence_records,
        "personal_exposure_preview": air_twin_preview.get("daily_summary") if air_twin_preview else None,
        "series": series,
        "records": records[-120:],
        "source": "Open-Meteo Air Quality Historical Feed + SQLite Snapshots & Evidence",
    }


def export_reports_csv(
    city: Optional[str] = None,
    period: str = "daily",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[str, str]:
    report = get_reports_data(city=city, period=period, start_date=start_date, end_date=end_date)
    if not report["sufficient_data"]:
        raise ValueError(report.get("message", "Insufficient data to export CSV."))

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Timestamp", "City", "Data Type", "AQI (US)", "PM2.5 (ug/m3)", "PM10 (ug/m3)", "CO (ug/m3)", "NO2 (ug/m3)", "SO2 (ug/m3)", "O3 (ug/m3)", "Source"])
    city_name = report["location"]["name"]
    src = report["source"]
    for row in report["series"]:
        writer.writerow(
            [
                row["time"],
                city_name,
                "Measured / Regional Historical Feed",
                row["aqi"],
                row.get("pm2_5", ""),
                row.get("pm10", ""),
                row.get("co", ""),
                row.get("no2", ""),
                row.get("so2", ""),
                row.get("o3", ""),
                src,
            ]
        )
    filename = f"vayumitra_{city_name.lower().replace(' ', '_')}_{period}_report.csv"
    return filename, buf.getvalue()


def _detect_image_type(raw_bytes: bytes) -> Optional[str]:
    if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if raw_bytes.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WEBP":
        return "webp"
    return None


def create_community_report(
    title: str,
    description: str,
    category: str,
    location_name: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    file_bytes: Optional[bytes] = None,
    original_filename: Optional[str] = None,
) -> Dict[str, Any]:
    init_db()
    title = (title or "").strip()
    description = (description or "").strip()
    category = (category or "").strip()
    location_name = (location_name or "").strip()

    category = LEGACY_CATEGORY_MAP.get(category, category)
    if len(title) < 4:
        raise ValueError("Report title must be at least 4 characters.")
    if len(description) < 10:
        raise ValueError("Please provide a description of at least 10 characters.")
    if category not in COMMUNITY_CATEGORIES:
        raise ValueError("Invalid environmental issue category.")
    if len(location_name) < 2:
        raise ValueError("Please specify the location of the issue.")

    stored_filename = None
    mime_type = None
    file_size = 0

    if file_bytes:
        file_size = len(file_bytes)
        if file_size > Config.MAX_UPLOAD_BYTES:
            raise ValueError("Uploaded photo exceeds the 5 MB size limit.")
        img_type = _detect_image_type(file_bytes)
        if not img_type:
            raise ValueError("Invalid image file. Only PNG, JPG, JPEG, and WEBP images are allowed.")
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        stored_filename = f"{uuid.uuid4().hex}.{img_type}"
        mime_type = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}[img_type]
        with open(os.path.join(UPLOAD_FOLDER, stored_filename), "wb") as fh:
            fh.write(file_bytes)

    now = utc_now_iso()
    report_code = f"VM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"

    conn = get_db_connection()
    try:
        profile = conn.execute("SELECT id FROM user_profiles ORDER BY id ASC LIMIT 1").fetchone()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO community_reports (
                report_code, profile_id, title, description, category, location_name,
                latitude, longitude, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Submitted', ?, ?)
            """,
            (
                report_code,
                profile["id"],
                title,
                description,
                category,
                location_name,
                latitude,
                longitude,
                now,
                now,
            ),
        )
        report_id = cur.lastrowid
        if stored_filename:
            cur.execute(
                """
                INSERT INTO report_uploads (report_id, original_filename, stored_filename, mime_type, file_size, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    (original_filename or stored_filename)[:180],
                    stored_filename,
                    mime_type,
                    file_size,
                    now,
                ),
            )
        conn.commit()
    finally:
        conn.close()

    reports = list_community_reports()
    return next((r for r in reports if r["report_code"] == report_code), reports[0])


def list_community_reports(
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT r.*, u.stored_filename, u.original_filename, u.mime_type, u.file_size
            FROM community_reports r
            LEFT JOIN report_uploads u ON u.report_id = r.id
            ORDER BY r.id DESC
            """
        ).fetchall()
        items = []
        s_filter = (status or "").strip()
        c_filter = (category or "").strip()
        q_filter = (search or "").strip().lower()
        for row in rows:
            mapped_cat = LEGACY_CATEGORY_MAP.get(row["category"], row["category"])
            if s_filter and row["status"] != s_filter:
                continue
            if c_filter and mapped_cat != c_filter and row["category"] != c_filter:
                continue
            if q_filter:
                hay = f"{row['report_code']} {row['title']} {row['location_name']} {mapped_cat}".lower()
                if q_filter not in hay:
                    continue

            st = row["status"]
            if st == "Verified":
                v_label = "Verified Incident"
            elif st == "Resolved":
                v_label = "Verified & Resolved"
            elif st == "Rejected":
                v_label = "Rejected Report"
            else:
                v_label = "Unverified Citizen Report (Pending Review)"

            items.append(
                {
                    "id": row["id"],
                    "report_code": row["report_code"],
                    "title": row["title"],
                    "description": row["description"],
                    "category": mapped_cat,
                    "location_name": row["location_name"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "status": st,
                    "is_verified": st in ("Verified", "Resolved"),
                    "verification_label": v_label,
                    "photo_url": f"/uploads/{row['stored_filename']}" if row["stored_filename"] else None,
                    "original_filename": row["original_filename"],
                    "file_size": row["file_size"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
        return items
    finally:
        conn.close()


def get_community_contribution_summary() -> Dict[str, Any]:
    reports = list_community_reports()
    total = len(reports)
    verified = sum(1 for r in reports if r["status"] == "Verified")
    resolved = sum(1 for r in reports if r["status"] == "Resolved")
    rejected = sum(1 for r in reports if r["status"] == "Rejected")
    with_photo = sum(1 for r in reports if r["photo_url"])
    points = (total * 10) + (with_photo * 5) + (verified * 20) + (resolved * 25) - (rejected * 10)
    points = max(0, points)
    if points >= 200:
        tier = "Platinum Air Guardian"
    elif points >= 100:
        tier = "Gold Air Guardian"
    elif points >= 40:
        tier = "Silver Air Guardian"
    else:
        tier = "Bronze Air Guardian"

    return {
        "total_reports": total,
        "verified_count": verified,
        "resolved_count": resolved,
        "rejected_count": rejected,
        "pending_count": max(0, total - verified - resolved - rejected),
        "with_photo_count": with_photo,
        "guardian_points": points,
        "guardian_tier": tier,
        "scoring_note": "Calculated transparently in SQLite: +10 per report, +5 photo evidence, +20 Verified, +25 Resolved.",
    }


def update_community_report_status(report_id: int, status: str) -> Dict[str, Any]:
    if status not in REPORT_STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(REPORT_STATUSES)}.")
    init_db()
    conn = get_db_connection()
    now = utc_now_iso()
    try:
        cur = conn.execute(
            "UPDATE community_reports SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, report_id),
        )
        if cur.rowcount == 0:
            raise LookupError("Report not found.")
        conn.commit()
    finally:
        conn.close()
    reports = list_community_reports()
    return next(r for r in reports if r["id"] == report_id)


# =========================================================
# MODULE 7: PERSONAL AIR TWIN & EXPOSURE DIARY
# =========================================================

ACTIVITY_TYPES = [
    "Commuting",
    "Outdoor Exercise",
    "Office / Work",
    "Home / Indoor",
    "School / Campus",
    "Market / Errands",
]


def _fetch_brief_aqi(lat: float, lon: float, standard: str = "NAQI") -> Tuple[Optional[int], Optional[float]]:
    try:
        url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}&longitude={lon}&current=us_aqi,european_aqi,pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,ozone"
        )
        resp = _http_get_json(url, cache_ttl=120)
        cur = resp.get("current") or {}
        if standard == "EU" and cur.get("european_aqi") is not None:
            aqi_v = cur.get("european_aqi")
        elif standard == "NAQI":
            p_snap = {
                "pm2_5": cur.get("pm2_5"),
                "pm10": cur.get("pm10"),
                "no2": cur.get("nitrogen_dioxide"),
                "so2": cur.get("sulphur_dioxide"),
                "co": cur.get("carbon_monoxide"),
                "o3": cur.get("ozone"),
            }
            aqi_v = compute_indian_naqi(p_snap)
            if aqi_v is None:
                aqi_v = cur.get("us_aqi")
        else:
            aqi_v = cur.get("us_aqi")
        return (int(round(float(aqi_v))) if aqi_v is not None else None, cur.get("pm2_5"))
    except Exception:
        return None, None


def get_air_twin_data(include_live: bool = True, auth_token: Optional[str] = None) -> Dict[str, Any]:
    init_db()
    conn = get_db_connection()
    try:
        profile = _resolve_profile_row(conn, auth_token)
        pref_row = conn.execute("SELECT aqi_standard FROM user_preferences WHERE profile_id = ? LIMIT 1", (profile["id"],)).fetchone()
        std = str((pref_row["aqi_standard"] if pref_row else "NAQI") or "NAQI").upper()
        pid = profile["id"]
        loc_rows = conn.execute(
            "SELECT * FROM personal_locations WHERE profile_id = ? ORDER BY id DESC",
            (pid,),
        ).fetchall()
        act_rows = conn.execute(
            "SELECT * FROM personal_activities WHERE profile_id = ? ORDER BY id DESC",
            (pid,),
        ).fetchall()
        diary_rows = conn.execute(
            "SELECT * FROM exposure_diary WHERE profile_id = ? ORDER BY entry_date DESC, id DESC LIMIT 30",
            (pid,),
        ).fetchall()
    finally:
        conn.close()

    loc_list: List[Dict[str, Any]] = []
    loc_aqi_map: Dict[int, Tuple[Optional[int], Optional[float], str]] = {}

    for lr in loc_rows:
        live_aqi, live_pm25 = _fetch_brief_aqi(lr["latitude"], lr["longitude"], standard=std) if include_live else (None, None)
        loc_aqi_map[lr["id"]] = (live_aqi, live_pm25, lr["city"])
        hrs_loc = lr["hours_per_day"] if "hours_per_day" in lr.keys() and lr["hours_per_day"] is not None else 8.0
        loc_list.append(
            {
                "id": lr["id"],
                "label": lr["label"],
                "city": lr["city"],
                "hours_per_day": float(hrs_loc),
                "latitude": lr["latitude"],
                "longitude": lr["longitude"],
                "live_aqi": live_aqi,
                "live_pm25": live_pm25,
                "category": classify_aqi(live_aqi, standard=std)["category"] if live_aqi is not None else "Unavailable",
                "created_at": lr["created_at"],
            }
        )

    fallback_aqi, fallback_pm25 = (
        _fetch_brief_aqi(profile["preferred_lat"], profile["preferred_lon"], standard=std) if include_live else (None, None)
    )

    activities_out: List[Dict[str, Any]] = []
    weighted_sum = 0.0
    pm25_weighted_sum = 0.0
    total_hours = 0.0
    outdoor_hours = 0.0
    valid_weight_hours = 0.0

    intensity_factor_map = {"Low": 1.0, "Moderate": 1.2, "Vigorous": 1.45}

    for ar in act_rows:
        lid = ar["location_id"]
        if lid and lid in loc_aqi_map:
            ref_aqi, ref_pm25, ref_city = loc_aqi_map[lid]
        else:
            ref_aqi, ref_pm25, ref_city = fallback_aqi, fallback_pm25, profile["preferred_city"]

        hrs = float(ar["hours_per_day"])
        is_out = bool(ar["is_outdoor"])
        env_factor = 1.0 if is_out else 0.45
        if ar["activity_type"] == "Commuting":
            env_factor = 0.88 if is_out else 0.65
        int_factor = intensity_factor_map.get(ar["intensity"], 1.1)

        total_hours += hrs
        if is_out:
            outdoor_hours += hrs

        est_act_aqi = round(ref_aqi * env_factor * int_factor, 1) if ref_aqi is not None else None
        est_act_pm25 = round(ref_pm25 * env_factor * int_factor, 1) if ref_pm25 is not None else None

        if est_act_aqi is not None:
            weighted_sum += est_act_aqi * hrs
            valid_weight_hours += hrs
        if est_act_pm25 is not None:
            pm25_weighted_sum += est_act_pm25 * hrs

        activities_out.append(
            {
                "id": ar["id"],
                "activity_type": ar["activity_type"],
                "location_id": lid,
                "location_label": ar["location_label"] or ref_city,
                "hours_per_day": hrs,
                "intensity": ar["intensity"],
                "is_outdoor": is_out,
                "ambient_aqi": ref_aqi,
                "calculated_exposure_aqi": est_act_aqi,
                "calculated_exposure_pm25": est_act_pm25,
                "created_at": ar["created_at"],
            }
        )

    if valid_weight_hours > 0:
        daily_avg_exposure = round(weighted_sum / valid_weight_hours, 1)
        daily_pm25_exposure = round(pm25_weighted_sum / valid_weight_hours, 1)
    elif loc_list and any(l["live_aqi"] is not None for l in loc_list):
        valid_locs = [l for l in loc_list if l["live_aqi"] is not None]
        w_hrs = sum(l["hours_per_day"] for l in valid_locs) or 1.0
        daily_avg_exposure = round(sum(l["live_aqi"] * l["hours_per_day"] for l in valid_locs) / w_hrs, 1)
        valid_pm_locs = [l for l in valid_locs if l["live_pm25"] is not None]
        daily_pm25_exposure = (
            round(sum(l["live_pm25"] * l["hours_per_day"] for l in valid_pm_locs) / (sum(l["hours_per_day"] for l in valid_pm_locs) or 1.0), 1)
            if valid_pm_locs
            else None
        )
    elif fallback_aqi is not None:
        daily_avg_exposure = float(fallback_aqi)
        daily_pm25_exposure = fallback_pm25
    else:
        daily_avg_exposure = None
        daily_pm25_exposure = None

    exp_cls = classify_aqi(daily_avg_exposure, standard=std) if daily_avg_exposure is not None else {"category": "Unavailable", "level": "moderate"}

    # Location comparison list (adds default city if no saved locations yet)
    location_comparison = (
        [
            {
                "label": f"{l['label']} ({l['city']})",
                "city": l["city"],
                "hours_per_day": l["hours_per_day"],
                "live_aqi": l["live_aqi"],
                "live_pm25": l["live_pm25"],
                "category": l["category"],
            }
            for l in loc_list
        ]
        if loc_list
        else (
            [
                {
                    "label": f"Primary ({profile['preferred_city']})",
                    "city": profile["preferred_city"],
                    "hours_per_day": 24.0,
                    "live_aqi": fallback_aqi,
                    "live_pm25": fallback_pm25,
                    "category": classify_aqi(fallback_aqi, standard=std)["category"] if fallback_aqi is not None else "Unavailable",
                }
            ]
            if fallback_aqi is not None
            else []
        )
    )

    # Weekly Exposure Trend (combines real 7d Open-Meteo archive weighted by user's outdoor factor + diary snapshots)
    weekly_exposure_trend: List[Dict[str, Any]] = []
    if include_live:
        diary_by_date = {d["entry_date"]: d["estimated_aqi"] for d in diary_rows}
        exposure_ratio = (
            (daily_avg_exposure / fallback_aqi)
            if (daily_avg_exposure is not None and fallback_aqi and fallback_aqi > 0)
            else 0.72
        )
        try:
            ref_lat = loc_list[0]["latitude"] if loc_list else profile["preferred_lat"]
            ref_lon = loc_list[0]["longitude"] if loc_list else profile["preferred_lon"]
            _, week_series = _extract_history_series(
                {"latitude": ref_lat, "longitude": ref_lon, "name": profile["preferred_city"]},
                "weekly",
                None,
                None,
                std,
            )
            for ws in week_series[-7:]:
                d_key = ws["date"]
                if d_key in diary_by_date:
                    weekly_exposure_trend.append(
                        {"date": d_key, "exposure_aqi": round(float(diary_by_date[d_key]), 1), "source_tag": "Logged Diary"}
                    )
                else:
                    weekly_exposure_trend.append(
                        {"date": d_key, "exposure_aqi": round(float(ws["aqi"]) * exposure_ratio, 1), "source_tag": "7d Archive Est."}
                    )
        except Exception:
            for d in list(diary_rows)[:7][::-1]:
                weekly_exposure_trend.append(
                    {"date": d["entry_date"], "exposure_aqi": round(float(d["estimated_aqi"]), 1), "source_tag": "Logged Diary"}
                )

    recommendations = []
    if daily_avg_exposure is not None:
        if daily_avg_exposure > 200:
            recommendations.append("Calculated exposure is elevated: shift outdoor workouts indoors and use an N95 mask during commutes.")
        elif daily_avg_exposure > 100:
            recommendations.append("Moderate-to-high calculated exposure: wear a mask during commutes and limit vigorous outdoor activity.")
        else:
            recommendations.append("Calculated daily exposure is relatively low under current ambient conditions.")
    if len(location_comparison) >= 2:
        highest_loc = max((x for x in location_comparison if x["live_aqi"] is not None), key=lambda x: x["live_aqi"], default=None)
        lowest_loc = min((x for x in location_comparison if x["live_aqi"] is not None), key=lambda x: x["live_aqi"], default=None)
        if highest_loc and lowest_loc and highest_loc["label"] != lowest_loc["label"]:
            recommendations.append(
                f"Highest ambient AQI among your places: {highest_loc['label']} ({highest_loc['live_aqi']}) vs cleanest {lowest_loc['label']} ({lowest_loc['live_aqi']})."
            )
    if not loc_list:
        recommendations.append("Add your frequently visited Indian locations (Home, Office, College) to compare exposure across places.")
    if not activities_out:
        recommendations.append("Log daily activities with hours/day to refine outdoor vs indoor exposure weighting.")

    return {
        "profile_name": profile["name"],
        "preferred_city": profile["preferred_city"],
        "aqi_standard": std,
        "activity_types": ACTIVITY_TYPES,
        "locations": loc_list,
        "location_comparison": location_comparison,
        "weekly_exposure_trend": weekly_exposure_trend,
        "activities": activities_out,
        "diary": [dict(d) for d in diary_rows],
        "daily_summary": {
            "weighted_exposure_aqi": daily_avg_exposure,
            "estimated_pm25_exposure": daily_pm25_exposure,
            "exposure_category": exp_cls["category"],
            "total_logged_hours": round(total_hours, 1),
            "outdoor_hours": round(outdoor_hours, 1),
            "locations_tracked": len(loc_list),
            "activities_tracked": len(activities_out),
            "recommendations": recommendations,
            "data_classification": f"Calculated Estimate (Real Open-Meteo {std} Ambient Feed x Logged Routine Weighting)",
        },
        "medical_disclaimer": (
            "IMPORTANT: Personal Air Twin metrics are environmental exposure estimates computed from regional ambient air-quality feeds "
            "and your self-reported activity schedule. This is NOT a medical diagnosis and NOT a direct measurement of personal inhaled dose."
        ),
    }


def add_personal_location(label: str, city: str, hours_per_day: float = 8.0, auth_token: Optional[str] = None) -> Dict[str, Any]:
    label = (label or "").strip()
    city = (city or "").strip()
    hrs = max(0.5, min(24.0, float(hours_per_day or 8.0)))
    if len(label) < 2:
        raise ValueError("Location label must be at least 2 characters (e.g., Home, Office).")
    geo = resolve_location(city=city)
    if not geo:
        raise LookupError(f"Location '{city}' was not found in India.")
    init_db()
    conn = get_db_connection()
    now = utc_now_iso()
    try:
        profile = _resolve_profile_row(conn, auth_token)
        cur = conn.execute(
            """
            INSERT INTO personal_locations (profile_id, label, city, latitude, longitude, hours_per_day, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (profile["id"], label, geo["name"], geo["latitude"], geo["longitude"], hrs, now),
        )
        conn.commit()
        return {
            "id": cur.lastrowid,
            "label": label,
            "city": geo["name"],
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
            "hours_per_day": hrs,
        }
    finally:
        conn.close()


def delete_personal_location(loc_id: int) -> None:
    init_db()
    conn = get_db_connection()
    try:
        cur = conn.execute("DELETE FROM personal_locations WHERE id = ?", (loc_id,))
        if cur.rowcount == 0:
            raise LookupError("Saved location not found.")
        conn.commit()
    finally:
        conn.close()


def add_personal_activity(
    activity_type: str,
    location_id: Optional[int],
    hours_per_day: float,
    intensity: str = "Moderate",
    is_outdoor: bool = True,
    auth_token: Optional[str] = None,
) -> Dict[str, Any]:
    activity_type = (activity_type or "").strip()
    if activity_type not in ACTIVITY_TYPES:
        raise ValueError(f"Activity must be one of: {', '.join(ACTIVITY_TYPES)}.")
    hrs = float(hours_per_day)
    if hrs <= 0 or hrs > 24:
        raise ValueError("Hours per day must be between 0.5 and 24.")
    if intensity not in ("Low", "Moderate", "Vigorous"):
        intensity = "Moderate"

    init_db()
    conn = get_db_connection()
    now = utc_now_iso()
    try:
        profile = _resolve_profile_row(conn, auth_token)
        loc_label = profile["preferred_city"]
        if location_id is not None:
            lrow = conn.execute("SELECT label, city FROM personal_locations WHERE id = ?", (location_id,)).fetchone()
            if lrow:
                loc_label = f"{lrow['label']} ({lrow['city']})"
            else:
                location_id = None
        cur = conn.execute(
            """
            INSERT INTO personal_activities (
                profile_id, activity_type, location_id, location_label, hours_per_day, intensity, is_outdoor, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (profile["id"], activity_type, location_id, loc_label, hrs, intensity, int(bool(is_outdoor)), now),
        )
        conn.commit()
        return {"id": cur.lastrowid, "activity_type": activity_type, "location_label": loc_label, "hours_per_day": hrs}
    finally:
        conn.close()


def delete_personal_activity(act_id: int) -> None:
    init_db()
    conn = get_db_connection()
    try:
        cur = conn.execute("DELETE FROM personal_activities WHERE id = ?", (act_id,))
        if cur.rowcount == 0:
            raise LookupError("Activity entry not found.")
        conn.commit()
    finally:
        conn.close()


def add_exposure_diary_entry(notes: str = "", entry_date: Optional[str] = None, auth_token: Optional[str] = None) -> Dict[str, Any]:
    twin = get_air_twin_data(include_live=True, auth_token=auth_token)
    summary = twin["daily_summary"]
    est_aqi = summary.get("weighted_exposure_aqi")
    if est_aqi is None:
        raise RuntimeError("Live AQI data unavailable to log diary entry.")

    d_str = (entry_date or "").strip() or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    act_summary = (
        ", ".join(f"{a['activity_type']} ({a['hours_per_day']}h)" for a in twin["activities"][:4])
        or f"Default ambient profile ({twin['preferred_city']})"
    )
    city_label = twin["locations"][0]["city"] if twin["locations"] else twin["preferred_city"]

    init_db()
    conn = get_db_connection()
    now = utc_now_iso()
    try:
        profile = _resolve_profile_row(conn, auth_token)
        cur = conn.execute(
            """
            INSERT INTO exposure_diary (
                profile_id, entry_date, city, activity_summary, estimated_aqi, estimated_pm25, calculated_exposure_score, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile["id"],
                d_str,
                city_label,
                act_summary,
                float(est_aqi),
                summary.get("estimated_pm25_exposure"),
                float(est_aqi),
                (notes or "").strip()[:500],
                now,
            ),
        )
        conn.commit()
        return {"id": cur.lastrowid, "entry_date": d_str, "city": city_label, "estimated_aqi": est_aqi}
    finally:
        conn.close()


def export_air_twin_csv() -> Tuple[str, str]:
    twin = get_air_twin_data(include_live=True)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Section", "Date/Label", "Location/City", "Hours/Day", "Calculated Exposure AQI", "Estimated PM2.5 (ug/m3)", "Notes/Disclaimer"])
    for a in twin["activities"]:
        writer.writerow([
            "Activity Profile",
            a["activity_type"],
            a["location_label"],
            a["hours_per_day"],
            a.get("calculated_exposure_aqi", ""),
            a.get("calculated_exposure_pm25", ""),
            f"Intensity: {a['intensity']}",
        ])
    for d in twin["diary"]:
        writer.writerow([
            "Exposure Diary",
            d["entry_date"],
            d["city"],
            "",
            d["estimated_aqi"],
            d.get("estimated_pm25", ""),
            f"{d['activity_summary']} | {d['notes']}",
        ])
    writer.writerow(["Disclaimer", "", "", "", "", "", twin["medical_disclaimer"]])
    return "vayumitra_personal_air_twin_exposure.csv", buf.getvalue()


def create_contact_message(name: str, email: str, subject: str, message: str) -> Dict[str, Any]:
    name = (name or "").strip()
    email = (email or "").strip()
    subject = (subject or "General Feedback").strip()
    message = (message or "").strip()
    if len(name) < 2 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or len(message) < 5:
        raise ValueError("Please provide a valid name, email, and message.")
    init_db()
    conn = get_db_connection()
    now = utc_now_iso()
    try:
        cur = conn.execute(
            "INSERT INTO contact_messages (name, email, subject, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, email, subject, message, now),
        )
        conn.commit()
        return {"id": cur.lastrowid, "name": name, "email": email, "subject": subject, "created_at": now}
    finally:
        conn.close()


def get_dashboard_data(city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
    aq = get_air_quality_data(city=city, lat=lat, lon=lon)
    bundle = get_profile_bundle()
    reports_count = len(list_community_reports())
    return {
        **aq,
        "profile_summary": {
            "name": bundle["profile"]["name"],
            "default_city": bundle["preferences"]["default_city"],
            "community_reports_count": reports_count,
        },
    }

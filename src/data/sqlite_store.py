"""
SQLite Data Store for Atmosphere360
Handles dynamic data: complaints, buildings, rooms, user preferences.
"""
import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager

import numpy as np
import pandas as pd

from config import COMPLAINT_STATUSES, COMPLAINT_CATEGORIES, BUILDING_TYPES, ROOM_TYPES


DB_PATH = Path("data/atmosphere360.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class Complaint:
    """Pollution complaint record."""
    id: str
    reference_id: str  # Human-readable: CP-20261122-001
    category: str
    location: str
    latitude: Optional[float]
    longitude: Optional[float]
    description: str
    photo_path: Optional[str]
    status: str
    priority: int  # 1=high, 2=medium, 3=low
    created_at: str
    updated_at: str
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


@dataclass
class Building:
    """Enterprise building record."""
    id: str
    name: str
    building_type: str
    address: str
    latitude: Optional[float]
    longitude: Optional[float]
    contact_name: Optional[str]
    contact_email: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class Room:
    """Room within a building."""
    id: str
    building_id: str
    name: str
    room_type: str
    floor: Optional[int]
    area_sqft: Optional[float]
    ceiling_ft: Optional[float]
    has_purifier: bool
    purifier_model: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class IndoorReading:
    """Indoor air quality reading."""
    id: str
    room_id: str
    pm25: float
    pm10: Optional[float]
    co2: Optional[float]
    temperature: Optional[float]
    humidity: Optional[float]
    recorded_at: str
    recorded_by: Optional[str]


@dataclass
class InspectionTeam:
    """Inspection team record."""
    id: str
    name: str
    team_type: str
    ward_zone: Optional[str]
    contact_person: Optional[str]
    contact_phone: Optional[str]
    vehicle_number: Optional[str]
    active: int
    created_at: str
    updated_at: str


@dataclass
class Deployment:
    """Team deployment record."""
    id: str
    team_id: str
    zone_station: str
    zone_region: Optional[str]
    action_type: str
    priority: int
    status: str
    linked_complaint_ids: Optional[str]
    expected_aqi: Optional[str]
    dispatched_at: str
    arrived_at: Optional[str]
    completed_at: Optional[str]
    verified_at: Optional[str]
    action_notes: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class ExpectedAlert:
    """Expected alert record for officer dashboard."""
    id: str
    station: str
    region: Optional[str]
    alert_level: str
    trigger_reasons: str
    forecast_aqi: Optional[float]
    current_aqi: Optional[float]
    wind_stagnation: int
    persistence_days: int
    complaint_count: int
    valid_from: str
    valid_until: str
    acknowledged: int
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[str]
    created_at: str


@dataclass
class TierConfig:
    """Tier configuration for admin panel."""
    tier: str
    feature_flags: str
    rate_limits: str
    pricing_inr: int
    updated_at: str


@dataclass
class RevenueMetric:
    """Revenue metric record."""
    id: str
    metric_date: str
    tier: str
    metric_name: str
    value: float
    created_at: str


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database schema."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Complaints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id TEXT PRIMARY KEY,
                reference_id TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                description TEXT NOT NULL,
                photo_path TEXT,
                status TEXT NOT NULL DEFAULT 'Submitted',
                priority INTEGER NOT NULL DEFAULT 2,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                assigned_to TEXT,
                resolution_notes TEXT
            )
        """)
        
        # Buildings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS buildings (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                building_type TEXT NOT NULL,
                address TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                contact_name TEXT,
                contact_email TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Rooms table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id TEXT PRIMARY KEY,
                building_id TEXT NOT NULL,
                name TEXT NOT NULL,
                room_type TEXT NOT NULL,
                floor INTEGER,
                area_sqft REAL,
                ceiling_ft REAL,
                has_purifier INTEGER DEFAULT 0,
                purifier_model TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (building_id) REFERENCES buildings (id)
            )
        """)
        
        # Indoor readings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indoor_readings (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                pm25 REAL NOT NULL,
                pm10 REAL,
                co2 REAL,
                temperature REAL,
                humidity REAL,
                recorded_at TEXT NOT NULL,
                recorded_by TEXT,
                FOREIGN KEY (room_id) REFERENCES rooms (id)
            )
        """)
        
        # User preferences (for citizen mode)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Inspection Teams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inspection_teams (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                team_type TEXT NOT NULL,  -- 'BMC Ward', 'MPCB', 'Traffic', 'Fire Dept'
                ward_zone TEXT,
                contact_person TEXT,
                contact_phone TEXT,
                vehicle_number TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Deployments table (team deployments to zones)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deployments (
                id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                zone_station TEXT NOT NULL,
                zone_region TEXT,
                action_type TEXT NOT NULL,  -- 'Construction Dust Audit', 'Industrial Stack Check', 'Road Sprinkling', 'Waste Burning Stop', 'General Inspection'
                priority INTEGER NOT NULL DEFAULT 2,  -- 1=high, 2=medium, 3=low
                status TEXT NOT NULL DEFAULT 'Dispatched',  -- 'Dispatched', 'On-Site', 'Action Taken', 'Verified', 'Closed'
                linked_complaint_ids TEXT,  -- JSON array of complaint IDs
                expected_aqi TEXT,  -- JSON with forecast details
                dispatched_at TEXT NOT NULL,
                arrived_at TEXT,
                completed_at TEXT,
                verified_at TEXT,
                action_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (team_id) REFERENCES inspection_teams (id)
            )
        """)
        
        # Expected Alerts table (pre-computed alerts for officer dashboard)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expected_alerts (
                id TEXT PRIMARY KEY,
                station TEXT NOT NULL,
                region TEXT,
                alert_level TEXT NOT NULL,  -- 'High Alert', 'Watch', 'Advisory'
                trigger_reasons TEXT NOT NULL,  -- JSON array of reasons
                forecast_aqi REAL,
                current_aqi REAL,
                wind_stagnation INTEGER DEFAULT 0,
                persistence_days INTEGER DEFAULT 0,
                complaint_count INTEGER DEFAULT 0,
                valid_from TEXT NOT NULL,
                valid_until TEXT NOT NULL,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Tier Config table (for admin panel feature flags)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tier_config (
                tier TEXT PRIMARY KEY,  -- 'free', 'pro', 'enterprise', 'officer'
                feature_flags TEXT NOT NULL,  -- JSON
                rate_limits TEXT NOT NULL,  -- JSON
                pricing_inr INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Revenue Metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS revenue_metrics (
                id TEXT PRIMARY KEY,
                metric_date TEXT NOT NULL,
                tier TEXT NOT NULL,
                metric_name TEXT NOT NULL,  -- 'subscriptions', 'affiliate_commission', 'saas_revenue'
                value REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_complaints_location ON complaints(location)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rooms_building ON rooms(building_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_room ON indoor_readings(room_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_time ON indoor_readings(recorded_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deployments_team ON deployments(team_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deployments_zone ON deployments(zone_station)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deployments_status ON deployments(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_station ON expected_alerts(station)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_level ON expected_alerts(alert_level)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_valid ON expected_alerts(valid_until)")
        
        conn.commit()


def generate_reference_id(prefix: str = "CP") -> str:
    """Generate human-readable reference ID."""
    date_str = datetime.now().strftime("%Y%m%d")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM complaints WHERE reference_id LIKE ?",
            (f"{prefix}-{date_str}-%",)
        )
        count = cursor.fetchone()[0] + 1
    return f"{prefix}-{date_str}-{count:03d}"


# ==================== Complaints CRUD ====================

def create_complaint(
    category: str,
    location: str,
    description: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    photo_path: Optional[str] = None,
    priority: int = 2
) -> Complaint:
    """Create a new pollution complaint."""
    if category not in COMPLAINT_CATEGORIES:
        category = "Other"
    if priority not in (1, 2, 3):
        priority = 2
    
    now = datetime.now().isoformat()
    complaint_id = str(uuid.uuid4())
    reference_id = generate_reference_id()
    
    complaint = Complaint(
        id=complaint_id,
        reference_id=reference_id,
        category=category,
        location=location,
        latitude=latitude,
        longitude=longitude,
        description=description,
        photo_path=photo_path,
        status="Submitted",
        priority=priority,
        created_at=now,
        updated_at=now,
    )
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO complaints (id, reference_id, category, location, latitude, longitude,
                                    description, photo_path, status, priority, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            complaint.id, complaint.reference_id, complaint.category, complaint.location,
            complaint.latitude, complaint.longitude, complaint.description, complaint.photo_path,
            complaint.status, complaint.priority, complaint.created_at, complaint.updated_at
        ))
        conn.commit()
    
    return complaint


def get_complaint(reference_id: str) -> Optional[Complaint]:
    """Get complaint by reference ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE reference_id = ?", (reference_id,))
        row = cursor.fetchone()
        if row:
            return Complaint(**dict(row))
    return None


def get_complaints(
    status: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Complaint]:
    """Get complaints with optional filters."""
    query = "SELECT * FROM complaints WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    if category:
        query += " AND category = ?"
        params.append(category)
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [Complaint(**dict(row)) for row in cursor.fetchall()]


def update_complaint_status(reference_id: str, status: str, 
                            assigned_to: Optional[str] = None,
                            resolution_notes: Optional[str] = None) -> bool:
    """Update complaint status."""
    if status not in COMPLAINT_STATUSES:
        return False
    
    now = datetime.now().isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE complaints 
            SET status = ?, updated_at = ?, assigned_to = COALESCE(?, assigned_to),
                resolution_notes = COALESCE(?, resolution_notes)
            WHERE reference_id = ?
        """, (status, now, assigned_to, resolution_notes, reference_id))
        conn.commit()
        return cursor.rowcount > 0


def get_complaint_stats() -> Dict[str, Any]:
    """Get complaint statistics for dashboard."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total by status
        cursor.execute("SELECT status, COUNT(*) FROM complaints GROUP BY status")
        by_status = dict(cursor.fetchall())
        
        # Total by category
        cursor.execute("SELECT category, COUNT(*) FROM complaints GROUP BY category")
        by_category = dict(cursor.fetchall())
        
        # Recent (last 7 days)
        cursor.execute("""
            SELECT COUNT(*) FROM complaints 
            WHERE datetime(created_at) > datetime('now', '-7 days')
        """)
        recent = cursor.fetchone()[0]
        
        # High priority open
        cursor.execute("""
            SELECT COUNT(*) FROM complaints 
            WHERE priority = 1 AND status IN ('Submitted', 'Under Review', 'Assigned', 'In Progress')
        """)
        high_priority_open = cursor.fetchone()[0]
        
        return {
            "by_status": by_status,
            "by_category": by_category,
            "recent_7_days": recent,
            "high_priority_open": high_priority_open,
            "total": sum(by_status.values()),
        }


# ==================== Buildings CRUD ====================

def create_building(
    name: str,
    building_type: str,
    address: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    contact_name: Optional[str] = None,
    contact_email: Optional[str] = None
) -> Building:
    """Create a new building."""
    if building_type not in BUILDING_TYPES:
        building_type = "Other"
    
    now = datetime.now().isoformat()
    building_id = str(uuid.uuid4())
    
    building = Building(
        id=building_id,
        name=name,
        building_type=building_type,
        address=address,
        latitude=latitude,
        longitude=longitude,
        contact_name=contact_name,
        contact_email=contact_email,
        created_at=now,
        updated_at=now,
    )
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO buildings (id, name, building_type, address, latitude, longitude,
                                    contact_name, contact_email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            building.id, building.name, building.building_type, building.address,
            building.latitude, building.longitude, building.contact_name,
            building.contact_email, building.created_at, building.updated_at
        ))
        conn.commit()
    
    return building


def get_building(building_id: str) -> Optional[Building]:
    """Get building by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM buildings WHERE id = ?", (building_id,))
        row = cursor.fetchone()
        if row:
            return Building(**dict(row))
    return None


def get_buildings(limit: int = 100) -> List[Building]:
    """Get all buildings."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM buildings ORDER BY created_at DESC LIMIT ?", (limit,))
        return [Building(**dict(row)) for row in cursor.fetchall()]


def update_building(building_id: str, **kwargs) -> bool:
    """Update building fields."""
    allowed = {"name", "building_type", "address", "latitude", "longitude", 
               "contact_name", "contact_email"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    
    updates["updated_at"] = datetime.now().isoformat()
    
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [building_id]
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE buildings SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return cursor.rowcount > 0


# ==================== Rooms CRUD ====================

def create_room(
    building_id: str,
    name: str,
    room_type: str,
    floor: Optional[int] = None,
    area_sqft: Optional[float] = None,
    ceiling_ft: Optional[float] = None,
    has_purifier: bool = False,
    purifier_model: Optional[str] = None
) -> Room:
    """Create a new room."""
    if room_type not in ROOM_TYPES:
        room_type = "Other"
    
    # Verify building exists
    if not get_building(building_id):
        raise ValueError(f"Building {building_id} not found")
    
    now = datetime.now().isoformat()
    room_id = str(uuid.uuid4())
    
    room = Room(
        id=room_id,
        building_id=building_id,
        name=name,
        room_type=room_type,
        floor=floor,
        area_sqft=area_sqft,
        ceiling_ft=ceiling_ft,
        has_purifier=has_purifier,
        purifier_model=purifier_model,
        created_at=now,
        updated_at=now,
    )
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rooms (id, building_id, name, room_type, floor, area_sqft,
                                ceiling_ft, has_purifier, purifier_model, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            room.id, room.building_id, room.name, room.room_type, room.floor,
            room.area_sqft, room.ceiling_ft, int(room.has_purifier),
            room.purifier_model, room.created_at, room.updated_at
        ))
        conn.commit()
    
    return room


def get_room(room_id: str) -> Optional[Room]:
    """Get room by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rooms WHERE id = ?", (room_id,))
        row = cursor.fetchone()
        if row:
            return Room(**dict(row))
    return None


def get_rooms(building_id: str) -> List[Room]:
    """Get all rooms for a building."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rooms WHERE building_id = ? ORDER BY name", (building_id,))
        return [Room(**dict(row)) for row in cursor.fetchall()]


# ==================== Indoor Readings CRUD ====================

def add_indoor_reading(
    room_id: str,
    pm25: float,
    pm10: Optional[float] = None,
    co2: Optional[float] = None,
    temperature: Optional[float] = None,
    humidity: Optional[float] = None,
    recorded_by: Optional[str] = None
) -> IndoorReading:
    """Add an indoor air quality reading."""
    if not get_room(room_id):
        raise ValueError(f"Room {room_id} not found")
    
    reading_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    reading = IndoorReading(
        id=reading_id,
        room_id=room_id,
        pm25=pm25,
        pm10=pm10,
        co2=co2,
        temperature=temperature,
        humidity=humidity,
        recorded_at=now,
        recorded_by=recorded_by,
    )
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO indoor_readings (id, room_id, pm25, pm10, co2, temperature,
                                          humidity, recorded_at, recorded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reading.id, reading.room_id, reading.pm25, reading.pm10,
            reading.co2, reading.temperature, reading.humidity,
            reading.recorded_at, reading.recorded_by
        ))
        conn.commit()
    
    return reading


def get_latest_reading(room_id: str) -> Optional[IndoorReading]:
    """Get most recent reading for a room."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM indoor_readings 
            WHERE room_id = ? 
            ORDER BY recorded_at DESC 
            LIMIT 1
        """, (room_id,))
        row = cursor.fetchone()
        if row:
            return IndoorReading(**dict(row))
    return None


def get_readings_history(room_id: str, days: int = 7) -> List[IndoorReading]:
    """Get reading history for a room."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM indoor_readings 
            WHERE room_id = ? AND datetime(recorded_at) > datetime('now', ?)
            ORDER BY recorded_at
        """, (room_id, f"-{days} days"))
        return [IndoorReading(**dict(row)) for row in cursor.fetchall()]


# ==================== User Preferences ====================

def set_preference(key: str, value: Any) -> None:
    """Set a user preference."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, json.dumps(value), datetime.now().isoformat()))
        conn.commit()


def get_preference(key: str, default: Any = None) -> Any:
    """Get a user preference."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
    return default


# ==================== Inspection Teams CRUD ====================

def create_inspection_team(
    name: str,
    team_type: str,
    ward_zone: Optional[str] = None,
    contact_person: Optional[str] = None,
    contact_phone: Optional[str] = None,
    vehicle_number: Optional[str] = None
) -> InspectionTeam:
    """Create a new inspection team."""
    now = datetime.now().isoformat()
    team_id = str(uuid.uuid4())
    
    team = InspectionTeam(
        id=team_id,
        name=name,
        team_type=team_type,
        ward_zone=ward_zone,
        contact_person=contact_person,
        contact_phone=contact_phone,
        vehicle_number=vehicle_number,
        active=1,
        created_at=now,
        updated_at=now,
    )
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inspection_teams (id, name, team_type, ward_zone, contact_person,
                                           contact_phone, vehicle_number, active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (team.id, team.name, team.team_type, team.ward_zone, team.contact_person,
              team.contact_phone, team.vehicle_number, team.active, team.created_at, team.updated_at))
        conn.commit()
    
    return team


def get_inspection_team(team_id: str) -> Optional[InspectionTeam]:
    """Get inspection team by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inspection_teams WHERE id = ?", (team_id,))
        row = cursor.fetchone()
        if row:
            return InspectionTeam(**dict(row))
    return None


def get_inspection_teams(active_only: bool = True) -> List[InspectionTeam]:
    """Get all inspection teams."""
    with get_db() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM inspection_teams WHERE active = 1 ORDER BY name")
        else:
            cursor.execute("SELECT * FROM inspection_teams ORDER BY name")
        return [InspectionTeam(**dict(row)) for row in cursor.fetchall()]


def seed_default_teams():
    """Seed default inspection teams if none exist."""
    teams = get_inspection_teams(active_only=False)
    if not teams:
        default_teams = [
            ("BMC Ward A Squad", "BMC Ward", "Ward A", "Inspector Sharma", "9876543210", "MH01AB1234"),
            ("BMC Ward B Squad", "BMC Ward", "Ward B", "Inspector Patel", "9876543211", "MH01AB1235"),
            ("MPCB Industrial Unit", "MPCB", "Industrial Zones", "Officer Singh", "9876543212", "MH01AB1236"),
            ("Traffic Dept Sprinkling", "Traffic", "Major Roads", "Officer Kumar", "9876543213", "MH01AB1237"),
            ("Fire Dept Emergency", "Fire Dept", "All Zones", "Officer Yadav", "9876543214", "MH01AB1238"),
        ]
        for name, ttype, ward, contact, phone, vehicle in default_teams:
            create_inspection_team(name, ttype, ward, contact, phone, vehicle)


# ==================== Deployments CRUD ====================

DEPLOYMENT_STATUSES = ["Dispatched", "On-Site", "Action Taken", "Verified", "Closed"]
ACTION_TYPES = [
    "Construction Dust Audit",
    "Industrial Stack Check", 
    "Road Sprinkling",
    "Waste Burning Stop",
    "General Inspection",
    "Vehicle Emission Check",
    "DG Set Inspection"
]

def create_deployment(
    team_id: str,
    zone_station: str,
    zone_region: str,
    action_type: str,
    priority: int = 2,
    linked_complaint_ids: Optional[List[str]] = None,
    expected_aqi: Optional[Dict] = None,
    action_notes: Optional[str] = None
) -> Deployment:
    """Create a new team deployment."""
    if action_type not in ACTION_TYPES:
        action_type = "General Inspection"
    if priority not in (1, 2, 3):
        priority = 2
    
    now = datetime.now().isoformat()
    dep_id = str(uuid.uuid4())
    
    import json
    dep = Deployment(
        id=dep_id,
        team_id=team_id,
        zone_station=zone_station,
        zone_region=zone_region,
        action_type=action_type,
        priority=priority,
        status="Dispatched",
        linked_complaint_ids=json.dumps(linked_complaint_ids) if linked_complaint_ids else None,
        expected_aqi=json.dumps(expected_aqi) if expected_aqi else None,
        dispatched_at=now,
        arrived_at=None,
        completed_at=None,
        verified_at=None,
        action_notes=action_notes,
        created_at=now,
        updated_at=now,
    )
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO deployments (id, team_id, zone_station, zone_region, action_type,
                                      priority, status, linked_complaint_ids, expected_aqi,
                                      dispatched_at, arrived_at, completed_at, verified_at,
                                      action_notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (dep.id, dep.team_id, dep.zone_station, dep.zone_region, dep.action_type,
              dep.priority, dep.status, dep.linked_complaint_ids, dep.expected_aqi,
              dep.dispatched_at, dep.arrived_at, dep.completed_at, dep.verified_at,
              dep.action_notes, dep.created_at, dep.updated_at))
        conn.commit()
    
    # Update linked complaints status to "In Progress"
    if linked_complaint_ids:
        for cid in linked_complaint_ids:
            # Find complaint by ID and update status
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT reference_id FROM complaints WHERE id = ?", (cid,))
                row = cursor.fetchone()
                if row:
                    update_complaint_status(row[0], "In Progress", assigned_to=team_id)
    
    return dep


def get_deployment(dep_id: str) -> Optional[Deployment]:
    """Get deployment by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM deployments WHERE id = ?", (dep_id,))
        row = cursor.fetchone()
        if row:
            return Deployment(**dict(row))
    return None


def get_deployments(
    team_id: Optional[str] = None,
    zone_station: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Deployment]:
    """Get deployments with filters."""
    query = "SELECT * FROM deployments WHERE 1=1"
    params = []
    
    if team_id:
        query += " AND team_id = ?"
        params.append(team_id)
    if zone_station:
        query += " AND zone_station = ?"
        params.append(zone_station)
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY dispatched_at DESC LIMIT ?"
    params.append(limit)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [Deployment(**dict(row)) for row in cursor.fetchall()]


def update_deployment_status(dep_id: str, status: str, action_notes: Optional[str] = None) -> bool:
    """Update deployment status with timestamp."""
    if status not in DEPLOYMENT_STATUSES:
        return False
    
    now = datetime.now().isoformat()
    timestamp_field = {
        "On-Site": "arrived_at",
        "Action Taken": "completed_at", 
        "Verified": "verified_at",
        "Closed": "verified_at"
    }.get(status)
    
    with get_db() as conn:
        cursor = conn.cursor()
        if timestamp_field:
            cursor.execute(f"""
                UPDATE deployments 
                SET status = ?, updated_at = ?, {timestamp_field} = ?, action_notes = COALESCE(?, action_notes)
                WHERE id = ?
            """, (status, now, now, action_notes, dep_id))
        else:
            cursor.execute("""
                UPDATE deployments 
                SET status = ?, updated_at = ?, action_notes = COALESCE(?, action_notes)
                WHERE id = ?
            """, (status, now, action_notes, dep_id))
        conn.commit()
        return cursor.rowcount > 0
    return False


# ==================== Expected Alerts CRUD ====================

ALERT_LEVELS = ["High Alert", "Watch", "Advisory"]

def create_expected_alert(
    station: str,
    region: str,
    alert_level: str,
    trigger_reasons: List[str],
    forecast_aqi: Optional[float] = None,
    current_aqi: Optional[float] = None,
    wind_stagnation: int = 0,
    persistence_days: int = 0,
    complaint_count: int = 0,
    valid_hours: int = 24
) -> ExpectedAlert:
    """Create an expected alert."""
    if alert_level not in ALERT_LEVELS:
        alert_level = "Advisory"
    
    now = datetime.now()
    valid_from = now.isoformat()
    valid_until = (now + timedelta(hours=valid_hours)).isoformat()
    
    import json
    alert_id = str(uuid.uuid4())
    
    alert = ExpectedAlert(
        id=alert_id,
        station=station,
        region=region,
        alert_level=alert_level,
        trigger_reasons=json.dumps(trigger_reasons),
        forecast_aqi=forecast_aqi,
        current_aqi=current_aqi,
        wind_stagnation=wind_stagnation,
        persistence_days=persistence_days,
        complaint_count=complaint_count,
        valid_from=valid_from,
        valid_until=valid_until,
        acknowledged=0,
        acknowledged_by=None,
        acknowledged_at=None,
        created_at=valid_from,
    )
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO expected_alerts (id, station, region, alert_level, trigger_reasons,
                                          forecast_aqi, current_aqi, wind_stagnation, persistence_days,
                                          complaint_count, valid_from, valid_until, acknowledged,
                                          acknowledged_by, acknowledged_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (alert.id, alert.station, alert.region, alert.alert_level, alert.trigger_reasons,
              alert.forecast_aqi, alert.current_aqi, alert.wind_stagnation, alert.persistence_days,
              alert.complaint_count, alert.valid_from, alert.valid_until, alert.acknowledged,
              alert.acknowledged_by, alert.acknowledged_at, alert.created_at))
        conn.commit()
    
    return alert


def get_active_alerts(station: Optional[str] = None) -> List[ExpectedAlert]:
    """Get active (not expired, not acknowledged) alerts."""
    now = datetime.now().isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        if station:
            cursor.execute("""
                SELECT * FROM expected_alerts 
                WHERE station = ? AND valid_until > ? AND acknowledged = 0
                ORDER BY 
                    CASE alert_level WHEN 'High Alert' THEN 1 WHEN 'Watch' THEN 2 ELSE 3 END,
                    valid_from
            """, (station, now))
        else:
            cursor.execute("""
                SELECT * FROM expected_alerts 
                WHERE valid_until > ? AND acknowledged = 0
                ORDER BY 
                    CASE alert_level WHEN 'High Alert' THEN 1 WHEN 'Watch' THEN 2 ELSE 3 END,
                    valid_from
            """, (now,))
        return [ExpectedAlert(**dict(row)) for row in cursor.fetchall()]


def acknowledge_alert(alert_id: str, acknowledged_by: str) -> bool:
    """Mark alert as acknowledged."""
    now = datetime.now().isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE expected_alerts 
            SET acknowledged = 1, acknowledged_by = ?, acknowledged_at = ?
            WHERE id = ?
        """, (acknowledged_by, now, alert_id))
        conn.commit()
        return cursor.rowcount > 0


def generate_expected_alerts_from_data(
    dyn_priority: pd.DataFrame,
    daily_df: pd.DataFrame,
    complaints: List,
    weather_fc: Optional[Dict] = None,
    aqi_fc: Optional[Dict] = None
) -> List[ExpectedAlert]:
    """Generate expected alerts from current data (called from Command Center)."""
    alerts = []
    seed_default_teams()
    
    # Get active alerts to avoid duplicates
    existing = get_active_alerts()
    existing_stations = {a.station for a in existing}
    
    for _, row in dyn_priority.iterrows():
        station = row["station"]
        if station in existing_stations:
            continue
        
        # Get current AQI
        current_aqi = row.get("latest_aqi", 0)
        
        # Get forecast AQI
        forecast_aqi = None
        if aqi_fc and "daily" in aqi_fc:
            daily_fc = aqi_fc["daily"]
            if "us_aqi_max" in daily_fc and daily_fc["us_aqi_max"]:
                forecast_aqi = daily_fc["us_aqi_max"][0]
            elif "european_aqi_max" in daily_fc and daily_fc["european_aqi_max"]:
                forecast_aqi = daily_fc["european_aqi_max"][0]
        
        # Get wind data
        wind_stagnation = 0
        if weather_fc and "hourly" in weather_fc:
            hourly = weather_fc["hourly"]
            if "wind_speed_10m" in hourly:
                avg_wind = np.mean(hourly["wind_speed_10m"][:24]) if hourly["wind_speed_10m"] else 10
                wind_stagnation = 1 if avg_wind < 8 else 0
        
        # Get persistence (days > 150 AQI in last 7 days)
        station_data = daily_df[daily_df["canonical_station"] == station].sort_values("date")
        if not station_data.empty:
            recent = station_data.tail(7)
            persistence_days = (recent["aqi_mean"] > 150).sum()
        else:
            persistence_days = 0
        
        # Get complaint count for this zone
        zone_complaints = [c for c in complaints if station.lower() in c.location.lower()]
        complaint_count = len(zone_complaints)
        
        # Determine alert level
        trigger_reasons = []
        alert_level = None
        
        if current_aqi > 200 or (forecast_aqi and forecast_aqi > 200):
            alert_level = "High Alert"
            trigger_reasons.append(f"Severe AQI: current={current_aqi:.0f}" + (f", forecast={forecast_aqi:.0f}" if forecast_aqi else ""))
        elif current_aqi > 150 or (forecast_aqi and forecast_aqi > 150):
            alert_level = "Watch"
            trigger_reasons.append(f"Elevated AQI: current={current_aqi:.0f}" + (f", forecast={forecast_aqi:.0f}" if forecast_aqi else ""))
        elif wind_stagnation and persistence_days >= 3:
            alert_level = "Watch"
            trigger_reasons.append(f"Wind stagnation + {persistence_days} days persistence")
        elif complaint_count >= 2:
            alert_level = "Advisory"
            trigger_reasons.append(f"{complaint_count} citizen complaints in zone")
        
        if alert_level:
            alert = create_expected_alert(
                station=station,
                region=row.get("zone", ""),
                alert_level=alert_level,
                trigger_reasons=trigger_reasons,
                forecast_aqi=forecast_aqi,
                current_aqi=current_aqi,
                wind_stagnation=wind_stagnation,
                persistence_days=persistence_days,
                complaint_count=complaint_count,
                valid_hours=24
            )
            alerts.append(alert)
    
    return alerts


# ==================== Tier Config CRUD ====================

DEFAULT_TIER_CONFIGS = {
    "free": {
        "feature_flags": {
            "my_air": True,
            "aircare_chat": True,
            "aircare_chat_limit": 5,
            "purifier_match": True,
            "purifier_match_live_prices": False,
            "civic_pulse": True,
            "airsense_indoor": False,
            "command_center": False,
            "team_deploy": False,
        },
        "rate_limits": {
            "aircare_messages_per_day": 5,
            "purifier_searches_per_day": 10,
        },
        "pricing_inr": 0,
    },
    "pro": {
        "feature_flags": {
            "my_air": True,
            "aircare_chat": True,
            "aircare_chat_limit": -1,  # unlimited
            "purifier_match": True,
            "purifier_match_live_prices": True,
            "civic_pulse": True,
            "civic_pulse_priority": True,
            "airsense_indoor": False,
            "command_center": False,
            "team_deploy": False,
        },
        "rate_limits": {
            "aircare_messages_per_day": -1,
            "purifier_searches_per_day": -1,
        },
        "pricing_inr": 199,  # monthly
    },
    "enterprise": {
        "feature_flags": {
            "my_air": True,
            "aircare_chat": True,
            "aircare_chat_limit": -1,
            "purifier_match": True,
            "purifier_match_live_prices": True,
            "purifier_match_multi_room": True,
            "civic_pulse": True,
            "airsense_indoor": True,
            "airsense_unlimited_buildings": True,
            "airsense_pdf_reports": True,
            "command_center": False,
            "team_deploy": False,
        },
        "rate_limits": {
            "aircare_messages_per_day": -1,
            "purifier_searches_per_day": -1,
            "buildings": -1,
        },
        "pricing_inr": 4999,  # per building per month
    },
    "officer": {
        "feature_flags": {
            "my_air": True,
            "aircare_chat": True,
            "aircare_chat_limit": -1,
            "purifier_match": True,
            "purifier_match_live_prices": True,
            "civic_pulse": True,
            "civic_pulse_full_queue": True,
            "command_center": True,
            "team_deploy": True,
            "expected_alerts": True,
            "priority_rankings": True,
            "route_planner": True,
        },
        "rate_limits": {},
        "pricing_inr": 0,  # Institutional SaaS
    },
}

def seed_tier_configs():
    """Seed default tier configurations."""
    with get_db() as conn:
        cursor = conn.cursor()
        for tier, config in DEFAULT_TIER_CONFIGS.items():
            cursor.execute("""
                INSERT OR REPLACE INTO tier_config (tier, feature_flags, rate_limits, pricing_inr, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (tier, json.dumps(config["feature_flags"]), json.dumps(config["rate_limits"]), 
                  config["pricing_inr"], datetime.now().isoformat()))
        conn.commit()


def get_tier_config(tier: str) -> Optional[TierConfig]:
    """Get tier configuration."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tier_config WHERE tier = ?", (tier,))
        row = cursor.fetchone()
        if row:
            return TierConfig(**dict(row))
    return None


def get_all_tier_configs() -> Dict[str, TierConfig]:
    """Get all tier configurations."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tier_config")
        return {row["tier"]: TierConfig(**dict(row)) for row in cursor.fetchall()}


def update_tier_config(tier: str, feature_flags: Optional[Dict] = None, 
                       rate_limits: Optional[Dict] = None, pricing_inr: Optional[int] = None) -> bool:
    """Update tier configuration."""
    import json
    current = get_tier_config(tier)
    if not current:
        return False
    
    ff = json.loads(current.feature_flags) if current.feature_flags else {}
    rl = json.loads(current.rate_limits) if current.rate_limits else {}
    
    if feature_flags:
        ff.update(feature_flags)
    if rate_limits:
        rl.update(rate_limits)
    
    pricing = pricing_inr if pricing_inr is not None else current.pricing_inr
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tier_config 
            SET feature_flags = ?, rate_limits = ?, pricing_inr = ?, updated_at = ?
            WHERE tier = ?
        """, (json.dumps(ff), json.dumps(rl), pricing, datetime.now().isoformat(), tier))
        conn.commit()
        return cursor.rowcount > 0


# ==================== Revenue Metrics CRUD ====================

def record_revenue_metric(tier: str, metric_name: str, value: float) -> RevenueMetric:
    """Record a revenue metric."""
    now = datetime.now().isoformat()
    metric_id = str(uuid.uuid4())
    
    metric = RevenueMetric(
        id=metric_id,
        metric_date=now[:10],  # YYYY-MM-DD
        tier=tier,
        metric_name=metric_name,
        value=value,
        created_at=now,
    )
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO revenue_metrics (id, metric_date, tier, metric_name, value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (metric.id, metric.metric_date, metric.tier, metric.metric_name, metric.value, metric.created_at))
        conn.commit()
    
    return metric


def get_revenue_metrics(tier: Optional[str] = None, days: int = 30) -> List[RevenueMetric]:
    """Get revenue metrics."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    with get_db() as conn:
        cursor = conn.cursor()
        if tier:
            cursor.execute("""
                SELECT * FROM revenue_metrics 
                WHERE tier = ? AND metric_date >= ?
                ORDER BY metric_date DESC
            """, (tier, cutoff))
        else:
            cursor.execute("""
                SELECT * FROM revenue_metrics 
                WHERE metric_date >= ?
                ORDER BY metric_date DESC
            """, (cutoff,))
        return [RevenueMetric(**dict(row)) for row in cursor.fetchall()]


def get_revenue_summary() -> Dict[str, Any]:
    """Get revenue summary for admin dashboard."""
    metrics = get_revenue_metrics(days=30)
    
    summary = {
        "by_tier": {},
        "by_metric": {},
        "total_30d": 0,
        "mrr_estimate": 0,
    }
    
    for m in metrics:
        # By tier
        if m.tier not in summary["by_tier"]:
            summary["by_tier"][m.tier] = 0
        summary["by_tier"][m.tier] += m.value
        
        # By metric
        if m.metric_name not in summary["by_metric"]:
            summary["by_metric"][m.metric_name] = 0
        summary["by_metric"][m.metric_name] += m.value
        
        summary["total_30d"] += m.value
    
    # Estimate MRR from subscriptions
    tier_configs = get_all_tier_configs()
    for tier, config in tier_configs.items():
        pricing = json.loads(config.pricing_inr) if isinstance(config.pricing_inr, str) else config.pricing_inr
        # This is simplified - real MRR would need subscription counts
        if tier in ["pro", "enterprise"]:
            summary["mrr_estimate"] += pricing  # placeholder
    
    return summary


# Initialize on import
init_db()
seed_default_teams()
seed_tier_configs()


if __name__ == "__main__":
    # Test the database
    print("Testing SQLite Store...")
    
    # Test complaint
    c = create_complaint(
        category="Construction Dust",
        location="Bandra Kurla Complex, Mumbai",
        description="Heavy dust from construction site near station",
        latitude=19.0596, longitude=72.8656
    )
    print(f"Created complaint: {c.reference_id}")
    
    # Test building
    b = create_building(
        name="TechCorp Office",
        building_type="Office",
        address="Andheri East, Mumbai",
        latitude=19.1197, longitude=72.8464
    )
    print(f"Created building: {b.name}")
    
    # Test room
    r = create_room(
        building_id=b.id,
        name="Conference Room A",
        room_type="Conference Room",
        floor=3,
        area_sqft=400,
        ceiling_ft=10,
        has_purifier=True,
        purifier_model="Philips AC1215"
    )
    print(f"Created room: {r.name}")
    
    # Test reading
    reading = add_indoor_reading(r.id, pm25=35.2, pm10=58.1, co2=850, temperature=24.5, humidity=55)
    print(f"Added reading: PM2.5={reading.pm25} µg/m³")
    
    # Stats
    stats = get_complaint_stats()
    print(f"Complaint stats: {stats}")
    
    print("\n✅ All database tests passed")
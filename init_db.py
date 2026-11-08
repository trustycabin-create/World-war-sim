import json
import requests

TURSO_DB_URL = "https://war-sim-db-trustycabin-create.aws-ap-south-1.turso.io"
TURSO_AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTQxNTIyNDgsImlkIjoiMDFhMWJiY2ItN2EwMS03MGFjLWJhNjgtMjRhZmRhYzU5MWUwIiwia2lkIjoiMzUzN2hMbnhCR0trV2hnbXdCN1Y4MnA2YTJrZ1JRN041eUk5TTRVc0NYUSIsInJpZCI6IjI3Njg3MGJhLTBiNWItNGQ4Mi1hYmEyLWYzNmFmYzQwNTkxNSJ9.2iDgRALderyIM_IcVFV7cAPF4zF9sJP5ijfBp9wtKkHmk7skMMKyNgY-0ppOwjz1kK73wMH_HgmNWfPCNz2vCw"


def execute_turso_sql(statements: list):
    url = f"{TURSO_DB_URL}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
        "Content-Type": "application/json",
    }
    requests_payload = [
        {"type": "execute", "stmt": {"sql": stmt}} for stmt in statements
    ]
    requests_payload.append({"type": "close"})

    response = requests.post(
        url, headers=headers, json={"requests": requests_payload}
    )
    if response.status_code != 200:
        raise Exception(f"Turso Error {response.status_code}: {response.text}")
    return response.json()


def initialize_1933_world():
    schema_queries = [
        """
        CREATE TABLE IF NOT EXISTS campaigns (
            campaign_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            time_multiplier REAL NOT NULL,
            game_timestamp TEXT NOT NULL,
            last_real_timestamp TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE'
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS regions (
            region_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            owner_nation TEXT NOT NULL,
            terrain_type TEXT NOT NULL,
            rail_gauge TEXT DEFAULT 'STANDARD',
            soil_moisture REAL DEFAULT 0.20,
            temperature_c REAL DEFAULT 1.0,
            population INTEGER NOT NULL,
            caloric_intake REAL DEFAULT 2400.0,
            terror_index REAL DEFAULT 5.0,
            resistance_network REAL DEFAULT 0.0,
            infrastructure_hp REAL DEFAULT 100.0,
            is_demilitarized INTEGER DEFAULT 0
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS national_stockpiles (
            nation TEXT PRIMARY KEY,
            crude_oil REAL NOT NULL,
            synthetic_fuel REAL NOT NULL,
            lignite_coal REAL NOT NULL,
            high_grade_steel REAL NOT NULL,
            manganese REAL NOT NULL,
            chromium REAL NOT NULL,
            rubber REAL NOT NULL,
            tungsten REAL NOT NULL,
            tool_hours REAL NOT NULL,
            munitions_tonnage REAL NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS military_hierarchy (
            officer_id TEXT PRIMARY KEY,
            nation TEXT NOT NULL,
            name TEXT NOT NULL,
            rank TEXT NOT NULL,
            parent_officer_id TEXT,
            assigned_sector TEXT,
            competence REAL NOT NULL,
            paranoia REAL DEFAULT 10.0,
            covert_dissent REAL DEFAULT 0.0,
            standing_orders TEXT,
            is_alive INTEGER DEFAULT 1
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS equipment_modifiers (
            modifier_id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            target_unit_type TEXT NOT NULL,
            cost_materials JSON NOT NULL,
            physics_impact JSON NOT NULL,
            retooling_hours_remaining REAL NOT NULL,
            status TEXT DEFAULT 'ACTIVE'
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS state_anomalies (
            anomaly_id TEXT PRIMARY KEY,
            region_or_unit_id TEXT NOT NULL,
            initiating_decree TEXT NOT NULL,
            material_deltas JSON NOT NULL,
            environmental_deltas JSON NOT NULL,
            psychological_deltas JSON NOT NULL,
            sim_hours_remaining REAL NOT NULL,
            timestamp TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS intelligence_dispatches (
            dispatch_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            origin TEXT NOT NULL,
            classification TEXT NOT NULL,
            headline TEXT NOT NULL,
            body TEXT NOT NULL
        );
        """,
    ]

    seed_queries = [
        """
        INSERT OR REPLACE INTO campaigns (campaign_id, name, time_multiplier, game_timestamp, last_real_timestamp, status)
        VALUES ('CMP-1933', 'The Long Struggle: 1933-1945', 1.0, '1933-01-30 12:00:00', datetime('now'), 'ACTIVE');
        """,
        """
        INSERT OR REPLACE INTO regions (region_id, name, owner_nation, terrain_type, rail_gauge, soil_moisture, temperature_c, population, caloric_intake, terror_index, resistance_network, infrastructure_hp, is_demilitarized)
        VALUES 
        ('REG-BERLIN', 'Berlin-Brandenburg', 'GERMANY', 'URBAN', 'STANDARD', 0.25, 0.5, 4300000, 2350.0, 8.0, 1.2, 100.0, 0),
        ('REG-RUHR', 'Ruhr Industrial Valley', 'GERMANY', 'URBAN', 'STANDARD', 0.30, 2.0, 3800000, 2400.0, 6.0, 2.5, 100.0, 0),
        ('REG-RHINELAND', 'The Rhineland', 'GERMANY', 'PLAINS', 'STANDARD', 0.28, 3.0, 2900000, 2400.0, 4.0, 1.0, 100.0, 1),
        ('REG-EASTPRUSSIA', 'East Prussia (Königsberg)', 'GERMANY', 'PLAINS', 'STANDARD', 0.35, -2.5, 2300000, 2200.0, 5.0, 0.5, 95.0, 0),
        ('REG-PARIS', 'Paris & Île-de-France', 'FRANCE', 'URBAN', 'STANDARD', 0.25, 4.0, 4500000, 2600.0, 2.0, 0.0, 100.0, 0),
        ('REG-WARSAW', 'Warsaw Province', 'POLAND', 'PLAINS', 'STANDARD', 0.40, -1.0, 3100000, 2100.0, 4.0, 0.0, 90.0, 0),
        ('REG-MOSCOW', 'Moscow Oblast', 'USSR', 'URBAN', 'BROAD', 0.50, -12.0, 4000000, 2050.0, 45.0, 0.0, 85.0, 0);
        """,
        """
        INSERT OR REPLACE INTO national_stockpiles (nation, crude_oil, synthetic_fuel, lignite_coal, high_grade_steel, manganese, chromium, rubber, tungsten, tool_hours, munitions_tonnage)
        VALUES 
        ('GERMANY', 180000.0, 25000.0, 4500000.0, 120000.0, 420.0, 210.0, 350.0, 65.0, 1500000.0, 12000.0),
        ('FRANCE', 450000.0, 0.0, 2800000.0, 180000.0, 1200.0, 850.0, 950.0, 220.0, 1100000.0, 28000.0),
        ('USSR', 1200000.0, 0.0, 6200000.0, 210000.0, 3400.0, 1900.0, 400.0, 540.0, 1800000.0, 35000.0);
        """,
        """
        INSERT OR REPLACE INTO military_hierarchy (officer_id, nation, name, rank, parent_officer_id, assigned_sector, competence, paranoia, covert_dissent, standing_orders, is_alive)
        VALUES 
        ('OFF-BLOMBERG', 'GERMANY', 'Werner von Blomberg', 'Minister of Defence', NULL, 'REG-BERLIN', 0.78, 12.0, 0.0, 'Strict Versailles adherence; covert expansion studies', 1),
        ('OFF-FRITSCH', 'GERMANY', 'Werner von Fritsch', 'Chief of Army Command', 'OFF-BLOMBERG', 'REG-BERLIN', 0.88, 15.0, 0.0, 'Maintain 100,000 cadre ready for mass mobilisation', 1);
        """,
        """
        INSERT OR REPLACE INTO intelligence_dispatches (dispatch_id, timestamp, origin, classification, headline, body)
        VALUES ('DISP-001', '1933-01-30 12:00:00', 'Reich Chancellery, Berlin', 'URGENT', 
                'CHANCELLOR APPOINTMENT CONFIRMED', 
                'Field Marshal von Hindenburg has sworn in the new Cabinet. Reichswehr restricted to 100,000 personnel. Strategic chromium reserves critical. Rhineland remilitarisation strictly prohibited.');
        """,
    ]

    print("[*] Creating Relational Schema on Turso Cloud...")
    execute_turso_sql(schema_queries)
    print("[+] Schema successfully created.")

    print("[*] Seeding 1933 Baseline Geopolitical State...")
    execute_turso_sql(seed_queries)
    print("[+] 1933 European Database Initialized Successfully!")


if __name__ == "__main__":
    initialize_1933_world()
  

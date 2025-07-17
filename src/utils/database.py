"""
Database module for WhisperKey transcription history
"""
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class TranscriptionRecord:
    """Data class for transcription records"""
    id: Optional[int] = None
    timestamp: str = ""
    text: str = ""
    duration_seconds: float = 0.0
    engine: str = ""  # 'openai' or 'vosk'
    model: str = ""
    confidence_score: Optional[float] = None
    audio_device: str = ""
    hotkey_used: str = ""
    text_length: int = 0
    language: Optional[str] = None
    processing_time_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0


@dataclass
class CostRecord:
    """Data class for OpenAI cost tracking records"""
    id: Optional[int] = None
    date: str = ""  # YYYY-MM-DD format
    cost_usd: float = 0.0
    raw_json: str = ""  # Raw API response for auditing
    last_updated: str = ""  # ISO timestamp
    api_key_hash: str = ""  # Hash of API key for multi-key support


class TranscriptionDatabase:
    """Handles SQLite database operations for transcription history"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            app_data_dir = Path(os.getenv('LOCALAPPDATA')) / 'WhisperKey'
            app_data_dir.mkdir(parents=True, exist_ok=True)
            db_path = app_data_dir / 'transcriptions.db'

        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # Ensure we can access columns by name
            conn.execute('''
                         CREATE TABLE IF NOT EXISTS transcriptions
                         (
                             id INTEGER PRIMARY KEY AUTOINCREMENT,
                             timestamp TEXT NOT NULL,
                             text TEXT NOT NULL,
                             duration_seconds REAL NOT NULL,
                             engine TEXT NOT NULL,
                             model TEXT NOT NULL,
                             confidence_score REAL,
                             audio_device TEXT NOT NULL,
                             hotkey_used TEXT NOT NULL,
                             text_length INTEGER NOT NULL,
                             language TEXT,
                             processing_time_ms INTEGER NOT NULL,
                             created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                             input_tokens INTEGER DEFAULT 0,
                             output_tokens INTEGER DEFAULT 0,
                             cost REAL DEFAULT 0.0
                         )
                         ''')

            # Add new columns for token and cost tracking if they don't exist
            self._add_column_if_not_exists(conn, 'transcriptions', 'input_tokens', 'INTEGER DEFAULT 0')
            self._add_column_if_not_exists(conn, 'transcriptions', 'output_tokens', 'INTEGER DEFAULT 0')
            self._add_column_if_not_exists(conn, 'transcriptions', 'cost', 'REAL DEFAULT 0.0')

            # Create cost_history table for OpenAI billing tracking
            conn.execute('''
                         CREATE TABLE IF NOT EXISTS cost_history
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             date
                             TEXT
                             NOT
                             NULL
                             UNIQUE,
                             cost_usd
                             REAL
                             NOT
                             NULL,
                             raw_json
                             TEXT
                             NOT
                             NULL,
                             last_updated
                             TEXT
                             NOT
                             NULL,
                             api_key_hash
                             TEXT
                             NOT
                             NULL,
                             created_at
                             DATETIME
                             DEFAULT
                             CURRENT_TIMESTAMP
                         )
                         ''')

            # Create index for faster searches
            conn.execute('''
                         CREATE INDEX IF NOT EXISTS idx_timestamp
                             ON transcriptions(timestamp)
                         ''')

            conn.execute('''
                         CREATE INDEX IF NOT EXISTS idx_text_search
                             ON transcriptions(text)
                         ''')

            conn.execute('''
                         CREATE INDEX IF NOT EXISTS idx_cost_date
                             ON cost_history(date)
                         ''')

    def _add_column_if_not_exists(self, conn, table_name, column_name, column_type):
        """Utility to add a column to a table if it doesn't exist."""
        try:
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = [row['name'] for row in cursor.fetchall()]
            if column_name not in columns:
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                print(f"Added column '{column_name}' to table '{table_name}'.")
        except sqlite3.Error as e:
            print(f"Database error while adding column: {e}")

    def _row_to_record(self, row) -> TranscriptionRecord:
        """Convert a database row to a TranscriptionRecord object with proper type casting."""
        try:
            # Use column names for robustness, requires conn.row_factory = sqlite3.Row
            return TranscriptionRecord(
                id=int(row['id']),
                timestamp=str(row['timestamp']),
                text=str(row['text']),
                duration_seconds=float(row['duration_seconds']) if row['duration_seconds'] is not None else 0.0,
                engine=str(row['engine']),
                model=str(row['model']),
                confidence_score=float(row['confidence_score']) if row['confidence_score'] is not None else None,
                audio_device=str(row['audio_device']),
                hotkey_used=str(row['hotkey_used']),
                text_length=int(row['text_length']) if row['text_length'] is not None else 0,
                language=str(row['language']) if row['language'] is not None else None,
                processing_time_ms=int(row['processing_time_ms']) if row['processing_time_ms'] is not None else 0,
                input_tokens=int(row['input_tokens']) if 'input_tokens' in row.keys() and row['input_tokens'] is not None else 0,
                output_tokens=int(row['output_tokens']) if 'output_tokens' in row.keys() and row['output_tokens'] is not None else 0,
                cost=float(row['cost']) if 'cost' in row.keys() and row['cost'] is not None else 0.0
            )
        except (ValueError, TypeError, KeyError) as e:
            # Log error and return a default record to prevent crashes
            print(f"[ERROR] Could not parse database record: {row}. Error: {e}")
            return TranscriptionRecord()

    def add_transcription(self, record: TranscriptionRecord) -> int:
        """Add a new transcription record to the database"""
        if not record.timestamp:
            record.timestamp = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                                      INSERT INTO transcriptions
                                      (timestamp, text, duration_seconds, engine, model, confidence_score, audio_device, hotkey_used, text_length, language, processing_time_ms, input_tokens, output_tokens, cost)
                                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                      ''', (
                    record.timestamp,
                    record.text,
                    record.duration_seconds,
                    record.engine,
                    record.model,
                    record.confidence_score,
                    record.audio_device,
                    record.hotkey_used,
                    record.text_length,
                    record.language,
                    record.processing_time_ms,
                    record.input_tokens,
                    record.output_tokens,
                    record.cost
                ))
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Database error in add_transcription: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_recent_transcriptions(self, limit: int = 3) -> List[TranscriptionRecord]:
        """Get the most recent transcriptions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                                       SELECT * FROM transcriptions
                                       ORDER BY timestamp DESC
                                       LIMIT ?
                                       ''', (limit,))

                records = [self._row_to_record(row) for row in cursor.fetchall()]
                return records
        except sqlite3.Error as e:
            print(f"Database error in get_recent_transcriptions: {e}")
            return []

    def get_all_transcriptions(self, limit: int = 1000) -> List[TranscriptionRecord]:
        """Get all transcriptions with optional limit"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM transcriptions ORDER BY created_at DESC LIMIT ?", (limit,))

                records = [self._row_to_record(row) for row in cursor.fetchall()]
                return records

        except sqlite3.Error as e:
            print(f"Database error in get_all_transcriptions: {e}")
            return []

    def search_transcriptions(self, query: str, limit: int = 100) -> List[TranscriptionRecord]:
        """Search transcriptions by text content"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                search_term = f"%{query}%"
                cursor.execute('''
                                   SELECT *
                                   FROM transcriptions
                                   WHERE text LIKE ?
                                   ORDER BY timestamp DESC LIMIT ?
                                   ''', (search_term, limit))

                records = [self._row_to_record(row) for row in cursor.fetchall()]
                return records
        except sqlite3.Error as e:
            print(f"Database error in search_transcriptions: {e}")
            return []

    def delete_transcription(self, transcription_id: int) -> bool:
        """Delete a transcription by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                                  DELETE
                                  FROM transcriptions
                                  WHERE id = ?
                                  ''', (transcription_id,))

            return cursor.rowcount > 0

    def get_statistics(self) -> dict:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                                  SELECT COUNT(*)                as total_transcriptions,
                                         SUM(duration_seconds)   as total_duration,
                                         AVG(duration_seconds)   as avg_duration,
                                         SUM(text_length)        as total_characters,
                                         AVG(text_length)        as avg_characters,
                                         AVG(processing_time_ms) as avg_processing_time
                                  FROM transcriptions
                                  ''')

            row = cursor.fetchone()
            return {
                'total_transcriptions': row[0] or 0,
                'total_duration_seconds': row[1] or 0.0,
                'average_duration_seconds': row[2] or 0.0,
                'total_characters': row[3] or 0,
                'average_characters': row[4] or 0.0,
                'average_processing_time_ms': row[5] or 0.0
            }

    # Cost tracking methods
    def add_cost_record(self, record: CostRecord) -> int:
        """Add a new cost record to the database"""
        if not record.last_updated:
            record.last_updated = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.execute('''
                    INSERT OR REPLACE INTO cost_history 
                    (date, cost_usd, raw_json, last_updated, api_key_hash)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    record.date, record.cost_usd, record.raw_json,
                    record.last_updated, record.api_key_hash
                ))

                conn.commit()
                return cursor.lastrowid

        except sqlite3.Error as e:
            print(f"Database error in add_cost_record: {e}")
            return None

    def get_cost_history(self, limit: int = 30) -> List[CostRecord]:
        """Get cost history records"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                                      SELECT *
                                      FROM cost_history
                                      ORDER BY date DESC
                                          LIMIT ?
                                      ''', (limit,))

                records = []
                for row in cursor.fetchall():
                    record = CostRecord(
                        id=row['id'],
                        date=row['date'],
                        cost_usd=row['cost_usd'],
                        raw_json=row['raw_json'],
                        last_updated=row['last_updated'],
                        api_key_hash=row['api_key_hash']
                    )
                    records.append(record)

                return records

        except sqlite3.Error as e:
            print(f"Database error in get_cost_history: {e}")
            return []

    def get_monthly_cost(self, year: int, month: int) -> float:
        """Get total cost for a specific month"""
        try:
            # Format date strings for the month
            start_date = f"{year:04d}-{month:02d}-01"
            if month == 12:
                end_date = f"{year + 1:04d}-01-01"
            else:
                end_date = f"{year:04d}-{month + 1:02d}-01"

            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.execute('''
                                      SELECT COALESCE(SUM(cost_usd), 0.0)
                                      FROM cost_history
                                      WHERE date >= ? AND date < ?
                                      ''', (start_date, end_date))

                result = cursor.fetchone()
                return result[0] if result else 0.0

        except sqlite3.Error as e:
            print(f"Database error in get_monthly_cost: {e}")
            return 0.0

    def get_all_costs(self, days_limit: int = 365) -> List[CostRecord]:
        """Get all cost records with optional days limit"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                
                # If days_limit is provided, calculate the cutoff date
                if days_limit:
                    from datetime import datetime, timedelta
                    cutoff_date = (datetime.now() - timedelta(days=days_limit)).strftime('%Y-%m-%d')
                    query = '''
                        SELECT *
                        FROM cost_history
                        WHERE date >= ?
                        ORDER BY date DESC
                    '''
                    cursor = conn.execute(query, (cutoff_date,))
                else:
                    # Get all records if no limit
                    cursor = conn.execute('''
                        SELECT *
                        FROM cost_history
                        ORDER BY date DESC
                    ''')

                records = []
                for row in cursor.fetchall():
                    record = CostRecord(
                        id=row['id'],
                        date=row['date'],
                        cost_usd=row['cost_usd'],
                        raw_json=row['raw_json'],
                        last_updated=row['last_updated'],
                        api_key_hash=row['api_key_hash']
                    )
                    records.append(record)

                return records

        except sqlite3.Error as e:
            print(f"Database error in get_all_costs: {e}")
            return []

    def get_last_cost_sync(self) -> Optional[str]:
        """Get the timestamp of the last cost sync"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.execute('''
                                      SELECT MAX(last_updated)
                                      FROM cost_history
                                      ''')

                result = cursor.fetchone()
                return result[0] if result and result[0] else None

        except sqlite3.Error as e:
            print(f"Database error in get_last_cost_sync: {e}")
            return None

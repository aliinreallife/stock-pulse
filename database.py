"""
Database models and operations for market watch data storage.
Uses SQLite for fast local storage when market is closed.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from schemas import MarketWatchItem, MarketWatchResponse, MarketWatchBestLimit
from config import DATABASE_PATH


class MarketWatchDB:
    """SQLite database manager for market watch data."""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.ensure_db_directory()
        self.init_database()
    
    def ensure_db_directory(self):
        """Ensure the database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create only instruments table for all data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS instruments (
                    insCode TEXT PRIMARY KEY,
                    lva TEXT,
                    lvc TEXT,
                    eps REAL,
                    pe TEXT,
                    pmd REAL,
                    pmo REAL,
                    qtj REAL,
                    pdv REAL,
                    ztt REAL,
                    qtc REAL,
                    bv REAL,
                    pc REAL,
                    pcpc REAL,
                    pmn REAL,
                    pmx REAL,
                    py REAL,
                    pf REAL,
                    pcl REAL,
                    vc INTEGER,
                    csv TEXT,
                    insID TEXT,
                    pMax REAL,
                    pMin REAL,
                    ztd REAL,
                    dEven INTEGER,
                    hEven INTEGER,
                    pClosing REAL,
                    iClose BOOLEAN,
                    yClose BOOLEAN,
                    pDrCotVal REAL,
                    zTotTran REAL,
                    qTotTran5J REAL,
                    qTotCap REAL,
                    best_limits_json TEXT,
                    market_type TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create additional_data table for client type data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS additional_data (
                    insCode TEXT PRIMARY KEY,
                    buy_I_Volume INTEGER,
                    buy_N_Volume INTEGER,
                    buy_DDD_Volume INTEGER,
                    buy_CountI INTEGER,
                    buy_CountN INTEGER,
                    buy_CountDDD INTEGER,
                    sell_I_Volume INTEGER,
                    sell_N_Volume INTEGER,
                    sell_CountI INTEGER,
                    sell_CountN INTEGER,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            
            conn.commit()
    
    def save_market_watch_data(self, data: MarketWatchResponse) -> int:
        """
        Save market watch data to instruments table.
        
        Args:
            data: MarketWatchResponse object containing market data
            
        Returns:
            Number of instruments updated
        """
        new_count = len(data.marketwatch) if data and data.marketwatch is not None else 0
        if new_count == 0:
            # Invalid snapshot; keep existing data
            return 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                # Begin transactional replace: delete only after validation
                cursor.execute("BEGIN")
                cursor.execute("DELETE FROM instruments")

                # Insert instruments for fast access
                self._upsert_instruments_batch(cursor, data.marketwatch)

                conn.commit()
                return new_count
            except Exception:
                conn.rollback()
                return 0

    def _upsert_instruments_batch(self, cursor, instruments: List[MarketWatchItem]) -> None:
        """Upsert instruments in batch for fast lookup by insCode."""
        if not instruments:
            return
        rows = []
        for inst in instruments:
            best_limits_json = json.dumps([bl.model_dump() for bl in inst.blDs])
            rows.append((
                inst.insCode,
                inst.lva,
                inst.lvc,
                inst.eps,
                str(inst.pe) if inst.pe is not None else None,
                inst.pmd,
                inst.pmo,
                inst.qtj,
                inst.pdv,
                inst.ztt,
                inst.qtc,
                inst.bv,
                inst.pc,
                inst.pcpc,
                inst.pmn,
                inst.pmx,
                inst.py,
                inst.pf,
                inst.pcl,
                inst.vc,
                inst.csv,
                inst.insID,
                inst.pMax,
                inst.pMin,
                inst.ztd,
                inst.dEven,
                inst.hEven,
                inst.pClosing,
                inst.iClose,
                inst.yClose,
                inst.pDrCotVal,
                inst.zTotTran,
                inst.qTotTran5J,
                inst.qTotCap,
                best_limits_json,
                getattr(inst, 'market_type', None),  # Get market_type if it exists
                datetime.now().isoformat()
            ))
        cursor.executemany(
            """
            INSERT INTO instruments (
                insCode, lva, lvc, eps, pe, pmd, pmo, qtj, pdv, ztt, qtc, bv, pc, pcpc,
                pmn, pmx, py, pf, pcl, vc, csv, insID, pMax, pMin, ztd, dEven, hEven,
                pClosing, iClose, yClose, pDrCotVal, zTotTran, qTotTran5J, qTotCap,
                best_limits_json, market_type, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(insCode) DO UPDATE SET
                lva=excluded.lva,
                lvc=excluded.lvc,
                eps=excluded.eps,
                pe=excluded.pe,
                pmd=excluded.pmd,
                pmo=excluded.pmo,
                qtj=excluded.qtj,
                pdv=excluded.pdv,
                ztt=excluded.ztt,
                qtc=excluded.qtc,
                bv=excluded.bv,
                pc=excluded.pc,
                pcpc=excluded.pcpc,
                pmn=excluded.pmn,
                pmx=excluded.pmx,
                py=excluded.py,
                pf=excluded.pf,
                pcl=excluded.pcl,
                vc=excluded.vc,
                csv=excluded.csv,
                insID=excluded.insID,
                pMax=excluded.pMax,
                pMin=excluded.pMin,
                ztd=excluded.ztd,
                dEven=excluded.dEven,
                hEven=excluded.hEven,
                pClosing=excluded.pClosing,
                iClose=excluded.iClose,
                yClose=excluded.yClose,
                pDrCotVal=excluded.pDrCotVal,
                zTotTran=excluded.zTotTran,
                qTotTran5J=excluded.qTotTran5J,
                qTotCap=excluded.qTotCap,
                best_limits_json=excluded.best_limits_json,
                market_type=excluded.market_type,
                updated_at=excluded.updated_at
            """,
            rows,
        )

    def get_market_watch_from_db(self) -> MarketWatchResponse:
        """Build a MarketWatchResponse from the instruments table (latest state)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT lva, lvc, eps, pe, pmd, pmo, qtj, pdv, ztt, qtc, bv, pc, pcpc,
                       pmn, pmx, py, pf, pcl, vc, csv, insID, pMax, pMin, ztd,
                       dEven, hEven, pClosing, iClose, yClose, pDrCotVal, zTotTran,
                       qTotTran5J, qTotCap, best_limits_json, market_type, insCode
                FROM instruments
                """
            )
            rows = cursor.fetchall()
            items: List[MarketWatchItem] = []
            
            # Define column order once - matches SELECT order exactly
            COLUMNS = [
                'lva', 'lvc', 'eps', 'pe', 'pmd', 'pmo', 'qtj', 'pdv', 'ztt', 'qtc', 'bv', 'pc', 'pcpc',
                'pmn', 'pmx', 'py', 'pf', 'pcl', 'vc', 'csv', 'insID', 'pMax', 'pMin', 'ztd',
                'dEven', 'hEven', 'pClosing', 'iClose', 'yClose', 'pDrCotVal', 'zTotTran',
                'qTotTran5J', 'qTotCap', 'best_limits_json', 'market_type', 'insCode'
            ]
            
            for row in rows:
                # Create dict for clear field access
                data = dict(zip(COLUMNS, row))
                
                # Parse best limits
                best_limits_data = json.loads(data['best_limits_json'] or '[]')
                best_limits = [MarketWatchBestLimit(**b) for b in best_limits_data]
                
                items.append(MarketWatchItem(
                    lva=data['lva'], lvc=data['lvc'], eps=data['eps'], pe=data['pe'],
                    pmd=data['pmd'], pmo=data['pmo'], qtj=data['qtj'], pdv=data['pdv'],
                    ztt=data['ztt'], qtc=data['qtc'], bv=data['bv'], pc=data['pc'], pcpc=data['pcpc'],
                    pmn=data['pmn'], pmx=data['pmx'], py=data['py'], pf=data['pf'], pcl=data['pcl'],
                    vc=data['vc'], csv=data['csv'], insID=data['insID'], pMax=data['pMax'], pMin=data['pMin'],
                    ztd=data['ztd'], blDs=best_limits, id=0, insCode=data['insCode'],
                    dEven=data['dEven'], hEven=data['hEven'], pClosing=data['pClosing'],
                    iClose=data['iClose'], yClose=data['yClose'], pDrCotVal=data['pDrCotVal'],
                    zTotTran=data['zTotTran'], qTotTran5J=data['qTotTran5J'], qTotCap=data['qTotCap'],
                    market_type=data['market_type']
                ))
            return MarketWatchResponse(marketwatch=items)
    
    # cleanup_old_data intentionally removed: daily full replace makes cleanup unnecessary
    
    def get_pdv_by_ins_code(self, ins_code: str) -> Optional[float]:
        """
        Get pdv (last price) by insCode - fast lookup using PRIMARY KEY.
        
        Args:
            ins_code: Instrument code to look up
            
        Returns:
            pdv value or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pdv FROM instruments WHERE insCode = ?
            """, (ins_code,))
            
            result = cursor.fetchone()
            return result[0] if result else None
    
    def save_additional_data(self, additional_data: List[Dict[str, Any]]) -> int:
        """
        Save additional data (client type) to additional_data table.
        
        Args:
            additional_data: List of additional data items
            
        Returns:
            Number of records saved
        """
        if not additional_data:
            return 0
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Transactional delete-then-insert for full replacement
            try:
                # Delete all existing additional data
                cursor.execute("DELETE FROM additional_data")
                
                # Insert new data
                rows = []
                for item in additional_data:
                    rows.append((
                        item.get('insCode'),
                        item.get('buy_I_Volume', 0),
                        item.get('buy_N_Volume', 0),
                        item.get('buy_DDD_Volume', 0),
                        item.get('buy_CountI', 0),
                        item.get('buy_CountN', 0),
                        item.get('buy_CountDDD', 0),
                        item.get('sell_I_Volume', 0),
                        item.get('sell_N_Volume', 0),
                        item.get('sell_CountI', 0),
                        item.get('sell_CountN', 0),
                        datetime.now().isoformat()
                    ))
                
                cursor.executemany("""
                    INSERT INTO additional_data (
                        insCode, buy_I_Volume, buy_N_Volume, buy_DDD_Volume,
                        buy_CountI, buy_CountN, buy_CountDDD,
                        sell_I_Volume, sell_N_Volume, sell_CountI, sell_CountN,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, rows)
                
                conn.commit()
                print(f"Additional data saved to database: {len(rows)} records")
                return len(rows)
                
            except Exception as e:
                conn.rollback()
                print(f"Error saving additional data: {e}")
                raise
    
    def get_additional_data_from_db(self) -> List[Dict[str, Any]]:
        """
        Get all additional data from database.
        
        Returns:
            List of additional data items
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT insCode, buy_I_Volume, buy_N_Volume, buy_DDD_Volume,
                       buy_CountI, buy_CountN, buy_CountDDD,
                       sell_I_Volume, sell_N_Volume, sell_CountI, sell_CountN
                FROM additional_data
            """)
            
            rows = cursor.fetchall()
            columns = [
                'insCode', 'buy_I_Volume', 'buy_N_Volume', 'buy_DDD_Volume',
                'buy_CountI', 'buy_CountN', 'buy_CountDDD',
                'sell_I_Volume', 'sell_N_Volume', 'sell_CountI', 'sell_CountN'
            ]
            
            return [dict(zip(columns, row)) for row in rows]
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get total records count
            cursor.execute("SELECT COUNT(*) FROM instruments")
            total_records = cursor.fetchone()[0]
            
            # Get latest record timestamp
            cursor.execute("""
                SELECT updated_at 
                FROM instruments 
                ORDER BY updated_at DESC 
                LIMIT 1
            """)
            latest_record = cursor.fetchone()
            
            # Get database file size
            db_file = Path(self.db_path)
            file_size = db_file.stat().st_size if db_file.exists() else 0
            
            return {
                "total_records": total_records,
                "latest_updated_at": latest_record[0] if latest_record else None,
                "database_size_bytes": file_size,
                "database_size_mb": round(file_size / (1024 * 1024), 2)
            }

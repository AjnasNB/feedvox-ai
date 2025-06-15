"""
Database setup and initialization for FeedVox AI
"""

import os
import pandas as pd
import sqlite3
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import logging
from typing import Generator, AsyncGenerator

from .models import Base, ICDCode, CPTCode, SNOMEDCode

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "sqlite:///./feedvox.db"
ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./feedvox.db"

# Create engines
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
async_engine = create_async_engine(ASYNC_DATABASE_URL)

# Create session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session"""
    async with AsyncSessionLocal() as session:
        yield session

async def initialize_database():
    """Initialize database and import medical codes"""
    logger.info("Initializing database...")
    
    # Create all tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")
    
    # Import medical codes if not already imported
    await import_medical_codes()
    
    logger.info("Database initialization completed")

async def import_medical_codes():
    """Import medical codes from CSV files"""
    logger.info("Importing medical codes...")
    
    # Check if data already exists
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            icd_count = await session.execute(text("SELECT COUNT(*) FROM icd_codes"))
            if icd_count.scalar() > 0:
                logger.info("Medical codes already imported, skipping...")
                return
    except Exception as e:
        logger.info("Tables not yet populated or don't exist, proceeding with import...")
    
    try:
        # Import ICD-10 codes
        await import_icd_codes()
        
        # Import CPT codes
        await import_cpt_codes()
        
        # Import SNOMED codes
        await import_snomed_codes()
        
        logger.info("Medical codes imported successfully")
        
    except Exception as e:
        logger.error(f"Error importing medical codes: {e}")
        raise

async def import_icd_codes():
    """Import ICD-10 codes from CSV"""
    logger.info("Importing ICD-10 codes...")
    
    csv_path = "../../mecial codes/ICD-10.csv"
    abs_path = os.path.abspath(csv_path)
    logger.info(f"Looking for ICD-10 CSV at: {csv_path}")
    logger.info(f"Absolute path: {abs_path}")
    logger.info(f"Current working directory: {os.getcwd()}")
    
    if not os.path.exists(csv_path):
        logger.warning(f"ICD-10 CSV not found at {csv_path}")
        return
    
    try:
        # Read CSV file
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} ICD-10 codes from CSV")
        
        # Map CSV columns to our model (adjust based on actual CSV structure)
        if 'Code' in df.columns and 'Description' in df.columns:
            code_col = 'Code'
            desc_col = 'Description'
        elif 'code' in df.columns and 'description' in df.columns:
            code_col = 'code'
            desc_col = 'description'
        else:
            # Try to detect columns automatically
            code_col = df.columns[0]
            desc_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
            logger.info(f"Auto-detected columns: {code_col}, {desc_col}")
        
        # Import in batches
        batch_size = 1000
        async with AsyncSessionLocal() as session:
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                
                icd_codes = []
                for _, row in batch.iterrows():
                    try:
                        code = str(row[code_col]).strip()
                        description = str(row[desc_col]).strip()
                        
                        if code and description and code != 'nan':
                            icd_code = ICDCode(
                                code=code,
                                description=description,
                                category=str(row.get('Category', '')).strip() if 'Category' in row else None,
                                chapter=str(row.get('Chapter', '')).strip() if 'Chapter' in row else None
                            )
                            icd_codes.append(icd_code)
                    except Exception as e:
                        logger.warning(f"Error processing ICD row {i}: {e}")
                        continue
                
                # Bulk insert
                session.add_all(icd_codes)
                await session.commit()
                
                logger.info(f"Imported {len(icd_codes)} ICD-10 codes (batch {i//batch_size + 1})")
        
        logger.info("ICD-10 codes imported successfully")
        
    except Exception as e:
        logger.error(f"Error importing ICD-10 codes: {e}")
        raise

async def import_cpt_codes():
    """Import CPT codes from CSV"""
    logger.info("Importing CPT codes...")
    
    csv_path = "../../mecial codes/CPT.csv"
    if not os.path.exists(csv_path):
        logger.warning(f"CPT CSV not found at {csv_path}")
        return
    
    try:
        # Read CSV file - CPT.csv has no headers, format is: code,description
        # Try different encodings to handle non-UTF-8 characters
        for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                df = pd.read_csv(csv_path, header=None, names=['code', 'description'], encoding=encoding)
                logger.info(f"Successfully read CPT CSV with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
        else:
            logger.error("Could not read CPT CSV with any encoding")
            return
        logger.info(f"Loaded {len(df)} CPT codes from CSV")
        
        # Import in batches
        batch_size = 1000
        async with AsyncSessionLocal() as session:
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                
                cpt_codes = []
                for _, row in batch.iterrows():
                    try:
                        code = str(row['code']).strip()
                        description = str(row['description']).strip()
                        
                        if code and description and code != 'nan' and description != 'nan':
                            # Check if code already exists in current batch
                            existing_codes = [c.code for c in cpt_codes]
                            if code not in existing_codes:
                                cpt_code = CPTCode(
                                    code=code,
                                    description=description,
                                    category=None,  # Not provided in CSV
                                    section=None    # Not provided in CSV
                                )
                                cpt_codes.append(cpt_code)
                    except Exception as e:
                        logger.warning(f"Error processing CPT row {i}: {e}")
                        continue
                
                # Bulk insert
                session.add_all(cpt_codes)
                await session.commit()
                
                logger.info(f"Imported {len(cpt_codes)} CPT codes (batch {i//batch_size + 1})")
        
        logger.info("CPT codes imported successfully")
        
    except Exception as e:
        logger.error(f"Error importing CPT codes: {e}")
        raise

async def import_snomed_codes():
    """Import SNOMED-CT codes from CSV"""
    logger.info("Importing SNOMED-CT codes...")
    
    csv_path = "../../mecial codes/SNOMED-CT.csv"
    if not os.path.exists(csv_path):
        logger.warning(f"SNOMED-CT CSV not found at {csv_path}")
        return
    
    try:
        # Read CSV file - SNOMED-CT.csv has headers: id,text,parent
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} SNOMED-CT codes from CSV")
        
        # Import in batches
        batch_size = 1000
        async with AsyncSessionLocal() as session:
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                
                snomed_codes = []
                for _, row in batch.iterrows():
                    try:
                        concept_id = str(row['id']).strip()
                        fsn = str(row['text']).strip()
                        parent_id = str(row.get('parent', '')).strip() if pd.notna(row.get('parent')) else None
                        
                        if concept_id and concept_id != 'nan' and fsn and fsn != 'nan':
                            # Check if concept_id already exists in current batch
                            existing_concepts = [c.concept_id for c in snomed_codes]
                            if concept_id not in existing_concepts:
                                snomed_code = SNOMEDCode(
                                    concept_id=concept_id,
                                    fsn=fsn,
                                    pt=fsn,  # Using fsn as pt since pt is not in our CSV
                                    semantic_tag=None  # Not provided in our CSV format
                                )
                                snomed_codes.append(snomed_code)
                    except Exception as e:
                        logger.warning(f"Error processing SNOMED row {i}: {e}")
                        continue
                
                # Bulk insert
                session.add_all(snomed_codes)
                await session.commit()
                
                logger.info(f"Imported {len(snomed_codes)} SNOMED-CT codes (batch {i//batch_size + 1})")
        
        logger.info("SNOMED-CT codes imported successfully")
        
    except Exception as e:
        logger.error(f"Error importing SNOMED-CT codes: {e}")
        raise 
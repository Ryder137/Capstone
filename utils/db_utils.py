from typing import Dict, Any, Optional
from supabase import Client
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_missing_columns(supabase: Client, table_name: str, columns: Dict[str, str]) -> None:
    """
    Ensure all specified columns exist in the table with the given data types.
    
    Args:
        supabase: Supabase client instance
        table_name: Name of the table to check/update
        columns: Dictionary of column names to their SQL type definitions
    """
    try:
        # Get existing columns
        query = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = %s
        """
        
        result = supabase.rpc('execute_sql', {
            'query': query,
            'params': [table_name]
        }).execute()
        
        existing_columns = {col['column_name']: col['data_type'] for col in result.data} if hasattr(result, 'data') else {}
        
        # Check and add missing columns
        for col_name, col_type in columns.items():
            if col_name not in existing_columns:
                alter_sql = f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}'
                logger.info(f"Adding column {col_name} to {table_name}")
                
                supabase.rpc('execute_sql', {
                    'query': alter_sql
                }).execute()
                
    except Exception as e:
        logger.error(f"Error in create_missing_columns for table {table_name}: {str(e)}")
        raise

def ensure_table_exists(supabase: Client, table_name: str, schema: str) -> None:
    """
    Ensure a table exists with the given schema.
    
    Args:
        supabase: Supabase client instance
        table_name: Name of the table to check/create
        schema: SQL CREATE TABLE statement (without CREATE TABLE part)
    """
    try:
        # Check if table exists
        result = supabase.rpc('execute_sql', {
            'query': "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s)",
            'params': [table_name]
        }).execute()
        
        table_exists = result.data[0]['exists'] if hasattr(result, 'data') and result.data else False
        
        if not table_exists:
            logger.info(f"Creating table {table_name}")
            supabase.rpc('execute_sql', {
                'query': f'CREATE TABLE {table_name} {schema}'
            }).execute()
            
    except Exception as e:
        logger.error(f"Error ensuring table {table_name} exists: {str(e)}")
        raise

def get_table_columns(supabase: Client, table_name: str) -> Dict[str, str]:
    """
    Get column information for a table.
    
    Args:
        supabase: Supabase client instance
        table_name: Name of the table
        
    Returns:
        Dict mapping column names to their data types
    """
    try:
        query = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = %s
        """
        
        result = supabase.rpc('execute_sql', {
            'query': query,
            'params': [table_name]
        }).execute()
        
        return {
            col['column_name']: {
                'data_type': col['data_type'],
                'is_nullable': col['is_nullable'] == 'YES'
            }
            for col in (result.data if hasattr(result, 'data') else [])
        }
        
    except Exception as e:
        logger.error(f"Error getting columns for table {table_name}: {str(e)}")
        return {}

def add_missing_foreign_keys(supabase: Client, table_name: str, foreign_keys: Dict[str, str]) -> None:
    """
    Add missing foreign key constraints to a table.
    
    Args:
        supabase: Supabase client instance
        table_name: Name of the table to modify
        foreign_keys: Dict of column_name -> referenced_table(referenced_column)
    """
    try:
        # Get existing foreign keys
        query = """
        SELECT
            tc.constraint_name,
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' 
        AND tc.table_name = %s;
        """
        
        result = supabase.rpc('execute_sql', {
            'query': query,
            'params': [table_name]
        }).execute()
        
        existing_fks = {
            fk['column_name']: f"{fk['foreign_table_name']}({fk['foreign_column_name']})"
            for fk in (result.data if hasattr(result, 'data') else [])
        }
        
        # Add missing foreign keys
        for column, reference in foreign_keys.items():
            if column not in existing_fks or existing_fks[column] != reference:
                fk_name = f"fk_{table_name}_{column}_to_{reference.replace('(', '_').replace(')', '')}"
                alter_sql = f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = '{fk_name}'
                    ) THEN
                        ALTER TABLE {table_name} 
                        ADD CONSTRAINT {fk_name} 
                        FOREIGN KEY ({column}) 
                        REFERENCES {reference} 
                        ON DELETE CASCADE;
                    END IF;
                END $$;
                """
                
                logger.info(f"Adding foreign key {fk_name} to {table_name}.{column}")
                supabase.rpc('execute_sql', {
                    'query': alter_sql
                }).execute()
                
    except Exception as e:
        logger.error(f"Error adding foreign keys to {table_name}: {str(e)}")
        raise

#!/usr/bin/env python3
"""
Script pour renommer les colonnes 'metadata' en 'session_data' et 'event_data' dans la base de données.

Ce script est nécessaire car SQLAlchemy réserve le nom 'metadata' pour son usage interne,
ce qui provoque l'erreur 'sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API'.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Chemin vers la base de données
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'ba_copilot.db')

def check_db_exists():
    """Vérifie si la base de données existe."""
    if not os.path.exists(DB_PATH):
        print(f"Base de données non trouvée: {DB_PATH}")
        sys.exit(1)
    print(f"Base de données trouvée: {DB_PATH}")

def backup_database():
    """Crée une sauvegarde de la base de données actuelle."""
    backup_path = DB_PATH + '.backup'
    with open(DB_PATH, 'rb') as src:
        with open(backup_path, 'wb') as dst:
            dst.write(src.read())
    print(f"Sauvegarde créée: {backup_path}")

def migrate_columns():
    """Renomme les colonnes metadata."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Vérifier l'existence des tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        if 'ai_activity_sessions' in tables:
            # Vérifie si la colonne metadata existe dans la table ai_activity_sessions
            cursor.execute("PRAGMA table_info(ai_activity_sessions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'metadata' in columns and 'session_data' not in columns:
                print("Migration de la table ai_activity_sessions...")
                # SQLite ne supporte pas directement ALTER TABLE RENAME COLUMN
                # Créer une nouvelle table avec la structure désirée
                cursor.execute("""
                CREATE TABLE ai_activity_sessions_new (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    session_data JSON,
                    created_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    project_id INTEGER,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
                """)
                
                # Copier les données
                cursor.execute("""
                INSERT INTO ai_activity_sessions_new
                SELECT id, title, action_type, status, metadata, created_at, completed_at, project_id
                FROM ai_activity_sessions
                """)
                
                # Supprimer l'ancienne table et renommer la nouvelle
                cursor.execute("DROP TABLE ai_activity_sessions")
                cursor.execute("ALTER TABLE ai_activity_sessions_new RENAME TO ai_activity_sessions")
                
                # Recréer les index
                cursor.execute("CREATE INDEX idx_ai_activity_sessions_action_type ON ai_activity_sessions(action_type)")
                cursor.execute("CREATE INDEX idx_ai_activity_sessions_status ON ai_activity_sessions(status)")
                
                print("Table ai_activity_sessions migrée avec succès.")
            else:
                print("La colonne metadata n'existe pas ou a déjà été renommée dans ai_activity_sessions.")
        else:
            print("La table ai_activity_sessions n'existe pas, rien à migrer.")
        
        if 'ai_events' in tables:
            # Vérifie si la colonne metadata existe dans la table ai_events
            cursor.execute("PRAGMA table_info(ai_events)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'metadata' in columns and 'event_data' not in columns:
                print("Migration de la table ai_events...")
                # Créer une nouvelle table avec la structure désirée
                cursor.execute("""
                CREATE TABLE ai_events_new (
                    id INTEGER PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    event_data JSON,
                    created_at TIMESTAMP,
                    session_id INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES ai_activity_sessions (id)
                )
                """)
                
                # Copier les données
                cursor.execute("""
                INSERT INTO ai_events_new
                SELECT id, agent_name, event_type, content, metadata, created_at, session_id
                FROM ai_events
                """)
                
                # Supprimer l'ancienne table et renommer la nouvelle
                cursor.execute("DROP TABLE ai_events")
                cursor.execute("ALTER TABLE ai_events_new RENAME TO ai_events")
                
                # Recréer les index
                cursor.execute("CREATE INDEX idx_ai_events_agent_name ON ai_events(agent_name)")
                cursor.execute("CREATE INDEX idx_ai_events_event_type ON ai_events(event_type)")
                cursor.execute("CREATE INDEX idx_ai_events_created_at ON ai_events(created_at)")
                
                print("Table ai_events migrée avec succès.")
            else:
                print("La colonne metadata n'existe pas ou a déjà été renommée dans ai_events.")
        else:
            print("La table ai_events n'existe pas, rien à migrer.")
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de la migration: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()

def main():
    """Fonction principale."""
    print("Migration de la base de données BA-Copilot...")
    
    check_db_exists()
    backup_database()
    migrate_columns()
    
    print("Migration terminée avec succès.")
    print("Pour appliquer ces changements, redémarrez l'application.")

if __name__ == "__main__":
    main()
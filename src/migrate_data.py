#!/usr/bin/env python3
"""
Script de migration pour transférer les données des buffers en mémoire vers la base de données SQLite.
Ce script doit être exécuté une seule fois lors de la transition vers le nouveau système.
"""

import sys
from sqlalchemy.orm import Session
import json
from datetime import datetime
import uuid
import os

# Importer nos modèles et fonctions de BD
from models import init_db, get_db, engine, Base, Project, Element, Diagram
import database

def migrate_projects(old_data, db: Session):
    """
    Migre les projets depuis les anciennes données vers la nouvelle BD.
    """
    print("Migration des projets...")
    projects_map = {}  # Map pour suivre la correspondance ancien ID -> nouvel ID
    
    # Extraire et migrer les projets
    projects = old_data.get("projects", [])
    for old_project in projects:
        old_id = old_project.get("id")
        name = old_project.get("name", "Projet sans nom")
        
        # Créer le projet dans la nouvelle BD
        new_project = database.create_project(db, name)
        projects_map[old_id] = new_project.id
        
        print(f"Migré projet {old_id} -> {new_project.id}: {name}")
    
    return projects_map

def migrate_project_buffers(old_data, projects_map, db: Session):
    """
    Migre les données des buffers de projet vers la nouvelle BD.
    """
    print("Migration des buffers de projet...")
    
    # Extraire et migrer les buffers de projet
    project_buffers = old_data.get("project_buffers", {})
    
    for old_project_id, buffer in project_buffers.items():
        old_project_id = int(old_project_id)  # Convertir en int si c'est une chaîne
        if old_project_id not in projects_map:
            print(f"Projet {old_project_id} introuvable dans les projets migrés, ignoré")
            continue
        
        new_project_id = projects_map[old_project_id]
        print(f"Migration du buffer pour le projet {old_project_id} -> {new_project_id}")
        
        # 1. Migrer les nœuds
        nodes = buffer.get("nodes", {})
        for node_id, node_data in nodes.items():
            node_type = node_data.get("type", "epic")
            title = node_data.get("title", f"Nœud {node_id}")
            description = node_data.get("description", "")
            status = node_data.get("status", "pending")
            
            # Créer l'élément dans la BD
            try:
                new_element = database.create_element(
                    db,
                    project_id=new_project_id,
                    custom_id=node_id,
                    element_type=node_type,
                    title=title,
                    description=description,
                    status=status
                )
                print(f"  Migré nœud {node_id} -> {new_element.id}: {title}")
            except Exception as e:
                print(f"  Erreur lors de la migration du nœud {node_id}: {e}")
        
        # 2. Migrer les diagrammes Mermaid
        diagrams = buffer.get("mermaid_diagrams", [])
        for diagram in diagrams:
            objective = diagram.get("objective", "")
            mermaid_code = diagram.get("diagram", "")
            
            if mermaid_code:
                try:
                    new_diagram = database.create_diagram(
                        db,
                        project_id=new_project_id,
                        mermaid_code=mermaid_code,
                        objective=objective
                    )
                    print(f"  Migré diagramme: {objective[:30]}...")
                except Exception as e:
                    print(f"  Erreur lors de la migration du diagramme: {e}")
        
        # 3. Mise à jour des relations parent-enfant
        # Cette partie est plus complexe et nécessite une seconde passe après la création des éléments
        # Pour l'instant, on garde la structure plate

def main():
    # Vérifier si le fichier de données est spécifié
    if len(sys.argv) < 2:
        print("Usage: python migrate_data.py <chemin_vers_fichier_json_old_data>")
        sys.exit(1)
    
    # Charger les anciennes données
    data_file = sys.argv[1]
    try:
        with open(data_file, 'r') as f:
            old_data = json.load(f)
    except Exception as e:
        print(f"Erreur lors du chargement des données: {e}")
        sys.exit(1)
    
    # Initialiser la BD si elle n'existe pas
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'ba_copilot.db')):
        print("Initialisation de la base de données...")
        init_db()
    
    # Obtenir une session de BD
    db = next(get_db())
    
    try:
        # Migration des projets
        projects_map = migrate_projects(old_data, db)
        
        # Migration des buffers de projet
        migrate_project_buffers(old_data, projects_map, db)
        
        print("Migration terminée avec succès!")
    except Exception as e:
        print(f"Erreur lors de la migration: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
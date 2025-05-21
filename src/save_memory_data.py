#!/usr/bin/env python3
"""
Script pour sauvegarder les données en mémoire (projets et buffers) dans un fichier JSON.
Ce fichier sera ensuite utilisé par migrate_data.py pour migrer les données vers la BD SQLite.
"""

import json
from datetime import datetime
import os
from api import projects, project_buffers

class DateTimeEncoder(json.JSONEncoder):
    """Encodeur JSON personnalisé pour gérer les objets datetime."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def save_memory_data():
    """
    Sauvegarde les données en mémoire dans un fichier JSON.
    """
    print("Sauvegarde des données en mémoire...")
    
    # Préparer les données à sauvegarder
    data = {
        "projects": projects,
        "project_buffers": project_buffers
    }
    
    # Définir le chemin du fichier de sortie
    output_file = os.path.join(os.path.dirname(__file__), 'memory_data.json')
    
    # Sauvegarder les données dans un fichier JSON
    try:
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, cls=DateTimeEncoder)
        print(f"Données sauvegardées avec succès dans {output_file}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des données: {e}")
        return False
    
    return True

if __name__ == "__main__":
    save_memory_data()
from typing import Dict, Any

# Temporary store for conversation contexts
# In a real app, use Redis, a DB table, or a more robust cache
conversation_store: Dict[str, Dict[str, Any]] = {}

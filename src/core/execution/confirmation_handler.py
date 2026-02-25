"""
confirmation_handler.py
=======================
Handles user confirmations for dangerous operations like delete.
Integrates with your frontend to show confirmation dialogs.
"""

from typing import Dict, Any, Optional
import time
import uuid

class ConfirmationManager:
    """
    Manages pending confirmations for dangerous operations.
    Works with frontend to show confirmation dialogs.
    """
    
    def __init__(self):
        self.pending_confirmations: Dict[str, Dict] = {}
    
    def create_confirmation(
        self,
        user_id: str,
        confirmation_type: str,
        message: str,
        action_params: Dict[str, Any]
    ) -> str:
        """
        Creates a pending confirmation request.
        Returns confirmation_id that frontend can use to approve/deny.
        """
        confirmation_id = str(uuid.uuid4())[:8]
        
        self.pending_confirmations[confirmation_id] = {
            "user_id": user_id,
            "type": confirmation_type,
            "message": message,
            "action_params": action_params,
            "created_at": time.time()
        }
        
        return confirmation_id
    
    def get_confirmation(self, confirmation_id: str) -> Optional[Dict]:
        """Retrieves a pending confirmation."""
        return self.pending_confirmations.get(confirmation_id)
    
    def approve_confirmation(self, confirmation_id: str) -> Optional[Dict]:
        """
        Approves and removes a confirmation.
        Returns the action_params if found, None otherwise.
        """
        confirmation = self.pending_confirmations.pop(confirmation_id, None)
        if confirmation:
            return confirmation["action_params"]
        return None
    
    def deny_confirmation(self, confirmation_id: str) -> bool:
        """Denies and removes a confirmation."""
        return self.pending_confirmations.pop(confirmation_id, None) is not None
    
    def cleanup_expired(self, max_age_seconds: int = 300):
        """Removes confirmations older than max_age_seconds (default 5 min)."""
        current_time = time.time()
        expired = [
            cid for cid, conf in self.pending_confirmations.items()
            if current_time - conf["created_at"] > max_age_seconds
        ]
        for cid in expired:
            del self.pending_confirmations[cid]
        return len(expired)


# Global instance
confirmation_manager = ConfirmationManager()

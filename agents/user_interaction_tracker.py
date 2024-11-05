import json
import os
from datetime import datetime

class UserInteractionTracker:
    def __init__(self):
        self.storage_path = "data/user_interactions/"
        os.makedirs(self.storage_path, exist_ok=True)
        
    def get_user_key(self, email=None, phone=None):
        if email:
            return f"email_{email}"
        elif phone:
            return f"phone_{phone}"
        return None
        
    def load_user_interactions(self, user_key):
        try:
            file_path = os.path.join(self.storage_path, f"{user_key}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            return {"agents": {}, "last_interaction": None}
        except Exception as e:
            print(f"Error loading user interactions: {str(e)}")
            return {"agents": {}, "last_interaction": None}
            
    def save_user_interaction(self, user_key, agent_name):
        try:
            interactions = self.load_user_interactions(user_key)
            interactions["agents"][agent_name] = {
                "first_interaction": interactions["agents"].get(agent_name, {}).get("first_interaction", datetime.now().isoformat()),
                "last_interaction": datetime.now().isoformat()
            }
            interactions["last_interaction"] = datetime.now().isoformat()
            
            file_path = os.path.join(self.storage_path, f"{user_key}.json")
            with open(file_path, 'w') as f:
                json.dump(interactions, f, indent=2)
                
        except Exception as e:
            print(f"Error saving user interaction: {str(e)}")
            
    def is_first_interaction(self, user_key, agent_name):
        interactions = self.load_user_interactions(user_key)
        return agent_name not in interactions["agents"]
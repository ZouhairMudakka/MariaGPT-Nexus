from .base_agent import BaseAgent
from services.openai_service import OpenAIService
from .google_docs_manager import GoogleDocsManager
import datetime
from typing import List, Dict, Any

class SchedulerAgent(BaseAgent):
    def __init__(self, openai_service: OpenAIService, google_docs_manager: GoogleDocsManager):
        context = """You are Mike, a scheduling specialist.
        When first joining a conversation:
        1. Thank Maria for the introduction
        2. Briefly introduce yourself in a friendly, professional way
        3. Then address the user's scheduling needs
        For subsequent interactions, respond directly to queries.
        Help users schedule meetings, appointments, and manage calendar-related requests.
        Available appointment slots are 30 minutes each."""
        
        specialties = {
            'meetings': 'Meeting and appointment scheduling',
            'calendar': 'Calendar management',
            'availability': 'Checking and confirming availability',
            'rescheduling': 'Modifying existing appointments'
        }
        
        self.google_docs_manager = google_docs_manager
        super().__init__("Mike", context, openai_service, specialties=specialties)

    def handle_scheduling_request(self, query: str, contact_info: Dict[str, Any]) -> str:
        """Handle the complete scheduling flow."""
        try:
            available_slots = self.google_docs_manager.get_available_slots()
            if not available_slots:
                return "I apologize, but there are no available slots in the next 7 days. Would you like to check for later dates?"

            formatted_slots = self.format_available_slots(available_slots)
            meeting_details = self.validate_meeting_details(query, available_slots)
            
            # Check if slot was selected and has purpose
            if meeting_details.get("slot_number") and meeting_details.get("purpose"):
                slot_index = int(meeting_details["slot_number"]) - 1
                if 0 <= slot_index < len(available_slots):
                    success = self.google_docs_manager.book_appointment_slot(
                        event_id=available_slots[slot_index]['id'],
                        attendee_email=contact_info['email'],
                        meeting_purpose=meeting_details['purpose']
                    )
                    
                    if success:
                        slot = available_slots[slot_index]
                        return f"Great! I've booked your appointment for {slot['start']}. You'll receive a calendar invitation shortly. The meeting is scheduled for {meeting_details['purpose']}."
                    
                return "I apologize, but there was an error booking your appointment. Please try again or select a different time slot."

            # If no valid slot selection, show available slots
            return f"Here are the available 30-minute slots:\n{formatted_slots}\nPlease let me know which slot you'd prefer by indicating the slot number (e.g., 'Slot 1')."
            
        except Exception as e:
            self.logger.logger.error(f"Error in scheduling flow: {str(e)}")
            return "I apologize, but there was an error processing your scheduling request. Please try again."

    def format_available_slots(self, slots: List[Dict[str, Any]]) -> str:
        """Format available slots for user display."""
        formatted_slots = []
        for i, slot in enumerate(slots, 1):
            try:
                start_time = datetime.datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
                formatted_slots.append(
                    f"Slot {i}: {start_time.strftime('%A, %B %d at %I:%M %p %Z')} (30 minutes)"
                )
            except (ValueError, AttributeError) as e:
                self.logger.logger.error(f"Error formatting slot {i}: {str(e)}")
                formatted_slots.append(f"Slot {i}: Time format error")
        return "\n".join(formatted_slots)

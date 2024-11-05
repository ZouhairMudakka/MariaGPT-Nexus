from typing import Optional

class DocumentManager:
    def __init__(self):
        self.knowledge_base = {
            'sales': {
                'products': 'Product information and pricing details',
                'services': 'Available service packages',
                'pricing': 'Current pricing structure'
            },
            'technical': {
                'faq': 'Common technical issues and solutions',
                'guides': 'Technical documentation and guides'
            },
            'support': {
                'policies': 'Support policies and procedures',
                'contact': 'Support contact information'
            }
        }

    def query_knowledge_base(self, query: str, category: str) -> str:
        """Query the knowledge base for relevant information.
        
        Args:
            query: User's query string
            category: Category to search within
            
        Returns:
            str: Relevant information from knowledge base
        """
        try:
            if category in self.knowledge_base:
                return str(self.knowledge_base[category])
            return "No relevant information found."
        except Exception as e:
            print(f"Error querying knowledge base: {str(e)}")
            return "Error accessing knowledge base."

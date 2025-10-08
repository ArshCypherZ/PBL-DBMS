# NLP to SQL Mapping Logic
# Implemented by: Amaan Khan

import re

class NLPParser:
    def __init__(self):
        self.patterns = {
            'select': r'(show|get|list|display|find|select)',
            'insert': r'(add|insert|create|new)',
            'update': r'(update|change|modify|edit)',
            'delete': r'(delete|remove)'
        }
    
    def parse(self, text):
        text = text.lower().strip()
        
        # Detect operation
        operation = self._detect_operation(text)
        
        if operation == 'select':
            return self._parse_select(text)
        elif operation == 'insert':
            return self._parse_insert(text)
        elif operation == 'update':
            return self._parse_update(text)
        
        return None
    
    def _detect_operation(self, text):
        for op, pattern in self.patterns.items():
            if re.search(pattern, text):
                return op
        return 'select'
    
    def _parse_select(self, text):
        return {
            'operation': 'select',
            'query': 'SELECT * FROM users',
            'params': []
        }
    
    def _parse_insert(self, text):
        # Extract name and email using simple patterns
        name_match = re.search(r'name[:\s]+([a-zA-Z\s]+?)(?:email|$)', text, re.IGNORECASE)
        email_match = re.search(r'email[:\s]+([^\s]+)', text, re.IGNORECASE)
        
        if name_match and email_match:
            name = name_match.group(1).strip()
            email = email_match.group(1).strip()
            return {
                'operation': 'insert',
                'procedure': 'safe_insert_user',
                'params': [name, email, 'system']
            }
        return None
    
    def _parse_update(self, text):
        # Extract id, name, and email
        id_match = re.search(r'id[:\s]+(\d+)', text, re.IGNORECASE)
        name_match = re.search(r'name[:\s]+([a-zA-Z\s]+?)(?:email|$)', text, re.IGNORECASE)
        email_match = re.search(r'email[:\s]+([^\s]+)', text, re.IGNORECASE)
        
        if id_match and (name_match or email_match):
            user_id = int(id_match.group(1))
            name = name_match.group(1).strip() if name_match else None
            email = email_match.group(1).strip() if email_match else None
            return {
                'operation': 'update',
                'procedure': 'safe_update_user',
                'params': [user_id, name, email, 'system']
            }
        return None

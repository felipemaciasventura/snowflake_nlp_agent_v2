"""
Input validation utilities for user queries
"""

import re

# Input validation regex - Allow letters, numbers, spaces, and basic punctuation
ALLOWED_INPUT_PATTERN = r"^[a-zA-Z0-9\s\.,\?\!''-]+$"


def validate_user_input(user_input):
    """Validate user input to allow only safe characters.
    
    Allows:
    - Letters (a-z, A-Z)
    - Numbers (0-9) 
    - Spaces
    - Basic punctuation: . , ? ! ' " -
    
    Returns:
        tuple: (is_valid: bool, cleaned_input: str, error_message: str)
    """
    if not user_input or not user_input.strip():
        return False, "", "❌ Please enter a valid query."
    
    # Remove leading/trailing whitespace
    cleaned_input = user_input.strip()
    
    # Check length
    if len(cleaned_input) < 3:
        return False, cleaned_input, "❌ Query too short. Please enter at least 3 characters."
    
    if len(cleaned_input) > 500:
        return False, cleaned_input, "❌ Query too long. Please limit your query to 500 characters."
    
    # Check for allowed characters
    if not re.match(ALLOWED_INPUT_PATTERN, cleaned_input):
        # Find the first disallowed character for better error message
        disallowed_chars = set()
        for char in cleaned_input:
            if not re.match(r"[a-zA-Z0-9\s\.,\?\!''-]", char):
                disallowed_chars.add(char)
        
        if disallowed_chars:
            chars_str = "', '".join(sorted(disallowed_chars))
            return False, cleaned_input, f"❌ Invalid characters detected: '{chars_str}'. Please use only letters, numbers, spaces, and basic punctuation (.,?!'-)"
    
    # Check for potential SQL injection patterns (basic detection)
    dangerous_patterns = [
        r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b', 
        r'\bALTER\b', r'\bCREATE\b', r'\bTRUNCATE\b', r'--', r'/\*', r'\*/',
        r';.*$', r'\bunion\b.*\bselect\b'
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, cleaned_input, re.IGNORECASE):
            return False, cleaned_input, "❌ Query contains potentially unsafe content. Please use natural language queries only."
    
    return True, cleaned_input, ""















import snowflake.connector
from .SnowflakeConfig import ACCOUNT, USER, PASSWORD
from typing import Optional


class SnowflakeLLMClient:
    """
    Client for interacting with Snowflake Cortex LLM.
    """
    
    def __init__(self):
        """Initialize Snowflake connection."""
        self.conn = None
        self.connect()
    
    def connect(self):
        """Establish connection to Snowflake."""
        try:
            self.conn = snowflake.connector.connect(
                user=USER,
                password=PASSWORD,
                account=ACCOUNT
            )
            print("✅ Connected to Snowflake")
        except Exception as e:
            print(f"❌ Failed to connect to Snowflake: {e}")
            raise
    
    def get_response(self, user_message: str, model: str = 'mistral-7b') -> Optional[str]:
        """
        Get a response from the Snowflake Cortex LLM.
        
        Args:
            user_message (str): The user's input message
            model (str): The model to use (default: 'mistral-7b')
            
        Returns:
            str: The LLM's response, or None if failed
        """
        if not self.conn:
            print("❌ No Snowflake connection available")
            return None
        
        try:
            cur = self.conn.cursor()
            
            # Escape single quotes in the message
            escaped_message = user_message.replace("'", "''")
            
            query = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                '{model}',
                '{escaped_message}'
            ) AS response;
            """
            
            cur.execute(query)
            row = cur.fetchone()
            cur.close()
            
            if row and row[0]:
                return row[0]
            else:
                return None
                
        except Exception as e:
            print(f"❌ Error getting LLM response: {e}")
            return None
    
    def get_contextual_response(self, user_message: str, context: str = "", model: str = 'mistral-7b') -> Optional[str]:
        """
        Get a contextual response from the LLM with a system prompt for navigation assistance.
        
        Args:
            user_message (str): The user's input message
            context (str): Additional context (e.g., conversation history)
            model (str): The model to use
            
        Returns:
            str: The LLM's response
        """
        # Build a prompt with context for navigation assistance
        system_prompt = """You are a helpful navigation assistant. Provide clear, concise, and friendly responses. 
Keep your answers brief and conversational, suitable for voice interaction."""
        
        full_prompt = f"{system_prompt}\n\n"
        if context:
            full_prompt += f"Context: {context}\n\n"
        full_prompt += f"User: {user_message}\nAssistant:"
        
        return self.get_response(full_prompt, model)
    
    def close(self):
        """Close the Snowflake connection."""
        if self.conn:
            self.conn.close()
            print("✅ Snowflake connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

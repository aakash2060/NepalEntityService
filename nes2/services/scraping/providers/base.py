"""Base LLM Provider interface for the Scraping Service.

This module defines the abstract base class that all LLM providers must implement.
It ensures a consistent interface across different provider implementations.

Provider Responsibilities:
    - Text generation with configurable parameters
    - Structured data extraction from unstructured text
    - Translation between languages
    - Token usage tracking (optional but recommended)

Design Principles:
    - Async-first API for non-blocking operations
    - Consistent error handling across providers
    - Flexible configuration via provider-specific kwargs
    - Optional features (like token tracking) gracefully degrade
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.
    
    All LLM providers must inherit from this class and implement the required
    abstract methods. This ensures a consistent interface across different
    provider implementations (AWS, OpenAI, Google, etc.).
    
    Attributes:
        provider_name: Human-readable name of the provider
        model_id: Identifier of the specific model being used
        max_tokens: Default maximum tokens for generation
        temperature: Default sampling temperature
    """
    
    def __init__(
        self,
        provider_name: str,
        model_id: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs
    ):
        """Initialize the base provider.
        
        Args:
            provider_name: Human-readable name of the provider
            model_id: Identifier of the specific model
            max_tokens: Default maximum tokens for generation
            temperature: Default sampling temperature (0.0-1.0)
            **kwargs: Provider-specific configuration options
        """
        self.provider_name = provider_name
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.config = kwargs
        
        logger.info(
            f"Initialized {provider_name} provider with model={model_id}"
        )
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate text using the LLM.
        
        This is the core method that all providers must implement. It takes
        a prompt and returns generated text.
        
        Args:
            prompt: The input prompt for text generation
            system_prompt: Optional system prompt for context/instructions
            max_tokens: Override default max_tokens for this request
            temperature: Override default temperature for this request
            
        Returns:
            Generated text as a string
            
        Raises:
            Exception: Provider-specific exceptions for API failures
            
        Examples:
            >>> provider = SomeProvider()
            >>> text = await provider.generate_text(
            ...     prompt="Translate: राम चन्द्र पौडेल",
            ...     system_prompt="You are a translator"
            ... )
        """
        pass
    
    @abstractmethod
    async def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        instructions: str,
    ) -> Dict[str, Any]:
        """Extract structured data from text using the LLM.
        
        Providers must implement this method to extract structured information
        from unstructured text according to a provided schema.
        
        Args:
            text: The text to extract data from
            schema: JSON schema describing the expected output structure
            instructions: Instructions for the extraction task
            
        Returns:
            Extracted structured data as a dictionary conforming to the schema
            
        Raises:
            Exception: Provider-specific exceptions for API failures
            
        Examples:
            >>> schema = {
            ...     "type": "object",
            ...     "properties": {
            ...         "name": {"type": "string"},
            ...         "position": {"type": "string"}
            ...     }
            ... }
            >>> data = await provider.extract_structured_data(
            ...     text="Ram Chandra Poudel is the President.",
            ...     schema=schema,
            ...     instructions="Extract person name and position"
            ... )
        """
        pass
    
    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Translate text between languages.
        
        Providers must implement this method to translate text from one
        language to another.
        
        Args:
            text: Text to translate
            source_lang: Source language code (e.g., "en", "ne")
            target_lang: Target language code (e.g., "en", "ne")
            
        Returns:
            Translated text as a string
            
        Raises:
            Exception: Provider-specific exceptions for API failures
            
        Examples:
            >>> translation = await provider.translate(
            ...     text="राम चन्द्र पौडेल",
            ...     source_lang="ne",
            ...     target_lang="en"
            ... )
        """
        pass
    
    def get_token_usage(self) -> Dict[str, int]:
        """Get token usage statistics.
        
        Optional method that providers can override to track token usage.
        Default implementation returns zeros.
        
        Returns:
            Dictionary with input_tokens, output_tokens, and total_tokens
            
        Examples:
            >>> usage = provider.get_token_usage()
            >>> print(f"Total tokens: {usage['total_tokens']}")
        """
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
    
    def reset_token_usage(self) -> None:
        """Reset token usage counters.
        
        Optional method that providers can override to reset usage tracking.
        Default implementation does nothing.
        """
        pass
    
    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"{self.__class__.__name__}(provider={self.provider_name}, model={self.model_id})"

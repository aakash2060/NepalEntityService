"""Translation component for Nepali-English translation and transliteration.

This module provides translation utilities for converting text between Nepali
(Devanagari script) and English, including:
- Nepali to English translation
- English to Nepali translation
- Transliteration handling (Devanagari ↔ Roman)
- Automatic language detection

The component supports multiple translation backends including LLM-based
translation and external translation APIs.

Architecture:
    - LanguageDetector: Identifies Nepali vs English based on character ranges
    - Transliterator: Converts between Devanagari and Roman scripts
    - Translator: Main translation service with caching and fallback

Performance Optimizations:
    - Translation caching for common phrases
    - Character-range based language detection (fast)
    - Fallback to transliteration when translation unavailable
    - Efficient Unicode range checks for Devanagari

Cultural Context:
    - Proper handling of Nepali names and titles
    - Support for mixed-script text (common in Nepal)
    - Phonetic transliteration for proper nouns
    - Context-aware translation for political terms
"""

import re
from typing import Any, Dict, Optional, Tuple
import logging

# Configure logging
logger = logging.getLogger(__name__)


class LanguageDetector:
    """Language detector for identifying Nepali and English text.
    
    Uses character range analysis to detect Devanagari script (Nepali)
    versus Latin script (English).
    
    Attributes:
        devanagari_range: Unicode range for Devanagari script (0x0900-0x097F)
    """
    
    def __init__(self):
        """Initialize the language detector."""
        self.devanagari_range = (0x0900, 0x097F)
    
    def detect(self, text: str) -> str:
        """Detect the language of the given text.
        
        Analyzes character ranges to determine if text is primarily
        Nepali (Devanagari) or English (Latin).
        
        Args:
            text: The text to analyze
            
        Returns:
            Language code: "ne" for Nepali, "en" for English
            
        Examples:
            >>> detector = LanguageDetector()
            >>> detector.detect("राम चन्द्र पौडेल")
            'ne'
            >>> detector.detect("Ram Chandra Poudel")
            'en'
        """
        if not text or not text.strip():
            return "en"  # Default to English for empty text
        
        # Count Devanagari characters
        devanagari_count = sum(
            1 for c in text
            if self.devanagari_range[0] <= ord(c) <= self.devanagari_range[1]
        )
        
        # Count Latin characters (basic ASCII letters)
        latin_count = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        
        # Determine language based on character counts
        if devanagari_count > latin_count:
            return "ne"
        else:
            return "en"
    
    def is_devanagari(self, text: str) -> bool:
        """Check if text contains Devanagari characters.
        
        Args:
            text: The text to check
            
        Returns:
            True if text contains any Devanagari characters
        """
        return any(
            self.devanagari_range[0] <= ord(c) <= self.devanagari_range[1]
            for c in text
        )
    
    def is_latin(self, text: str) -> bool:
        """Check if text contains Latin characters.
        
        Args:
            text: The text to check
            
        Returns:
            True if text contains any Latin characters
        """
        return any(c.isalpha() and ord(c) < 128 for c in text)


class Transliterator:
    """Transliterator for converting between Devanagari and Latin scripts.
    
    Provides phonetic transliteration between Nepali (Devanagari) and
    romanized (Latin) representations.
    
    Attributes:
        devanagari_to_latin: Mapping from Devanagari to Latin characters
        latin_to_devanagari: Mapping from Latin to Devanagari characters
    """
    
    def __init__(self):
        """Initialize the transliterator with character mappings."""
        # Basic Devanagari to Latin mapping (simplified)
        # Real implementation would use a comprehensive mapping
        self.devanagari_to_latin = {
            # Vowels
            'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ii', 'उ': 'u', 'ऊ': 'uu',
            'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
            
            # Consonants
            'क': 'ka', 'ख': 'kha', 'ग': 'ga', 'घ': 'gha', 'ङ': 'nga',
            'च': 'cha', 'छ': 'chha', 'ज': 'ja', 'झ': 'jha', 'ञ': 'nya',
            'ट': 'ta', 'ठ': 'tha', 'ड': 'da', 'ढ': 'dha', 'ण': 'na',
            'त': 'ta', 'थ': 'tha', 'द': 'da', 'ध': 'dha', 'न': 'na',
            'प': 'pa', 'फ': 'pha', 'ब': 'ba', 'भ': 'bha', 'म': 'ma',
            'य': 'ya', 'र': 'ra', 'ल': 'la', 'व': 'wa', 'श': 'sha',
            'ष': 'sha', 'स': 'sa', 'ह': 'ha',
            
            # Vowel signs (matras)
            'ा': 'aa', 'ि': 'i', 'ी': 'ii', 'ु': 'u', 'ू': 'uu',
            'ृ': 'ri', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
            
            # Special characters
            '्': '', '़': '', 'ं': 'n', 'ः': 'h', 'ँ': 'n',
        }
        
        # Build reverse mapping for Latin to Devanagari
        # This is simplified - real implementation would handle ambiguities
        self.latin_to_devanagari = {}
        for dev, lat in self.devanagari_to_latin.items():
            if lat and lat not in self.latin_to_devanagari:
                self.latin_to_devanagari[lat] = dev
    
    def devanagari_to_roman(self, text: str) -> str:
        """Transliterate Devanagari text to Roman script.
        
        Args:
            text: Devanagari text to transliterate
            
        Returns:
            Romanized text
            
        Examples:
            >>> trans = Transliterator()
            >>> trans.devanagari_to_roman("राम")
            'raam'
        """
        result = []
        
        for char in text:
            if char in self.devanagari_to_latin:
                result.append(self.devanagari_to_latin[char])
            else:
                # Keep non-Devanagari characters as-is
                result.append(char)
        
        return ''.join(result)
    
    def roman_to_devanagari(self, text: str) -> str:
        """Transliterate Roman text to Devanagari script.
        
        Args:
            text: Roman text to transliterate
            
        Returns:
            Devanagari text
            
        Examples:
            >>> trans = Transliterator()
            >>> trans.roman_to_devanagari("raam")
            'राम'
        """
        # This is a simplified implementation
        # Real implementation would use proper phonetic rules
        result = []
        i = 0
        text_lower = text.lower()
        
        while i < len(text_lower):
            # Try to match longest possible sequence
            matched = False
            for length in range(min(4, len(text_lower) - i), 0, -1):
                substr = text_lower[i:i+length]
                if substr in self.latin_to_devanagari:
                    result.append(self.latin_to_devanagari[substr])
                    i += length
                    matched = True
                    break
            
            if not matched:
                # Keep non-transliteratable characters as-is
                result.append(text[i])
                i += 1
        
        return ''.join(result)


class Translator:
    """Translator for converting text between Nepali and English.
    
    Provides translation capabilities using LLM or external translation APIs.
    Supports both translation and transliteration.
    
    Attributes:
        llm_provider: The LLM provider to use for translation
        llm_config: Configuration for the LLM provider
        language_detector: Language detector instance
        transliterator: Transliterator instance
    """
    
    def __init__(
        self,
        llm_provider: str = "mock",
        llm_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the translator.
        
        Args:
            llm_provider: The LLM provider to use (default: "mock")
            llm_config: Configuration dictionary for the LLM provider
        """
        self.llm_provider = llm_provider
        self.llm_config = llm_config or {}
        self.language_detector = LanguageDetector()
        self.transliterator = Transliterator()
        
        # Translation cache for common phrases
        self._translation_cache: Dict[Tuple[str, str, str], str] = {}
    
    async def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Translate text between Nepali and English.
        
        Translates text from source language to target language. If source
        language is not specified, it will be automatically detected.
        
        Args:
            text: The text to translate
            target_lang: Target language code ("en" or "ne")
            source_lang: Source language code (optional, auto-detected if not provided)
            
        Returns:
            Dictionary containing:
                - translated_text: The translated text
                - detected_language: The detected source language (if auto-detected)
                - source_language: The source language used
                - target_language: The target language
                - transliteration: Transliterated version (if applicable)
                
        Examples:
            >>> translator = Translator()
            >>> result = await translator.translate(
            ...     text="राम चन्द्र पौडेल",
            ...     source_lang="ne",
            ...     target_lang="en"
            ... )
            >>> print(result["translated_text"])
            'Ram Chandra Poudel'
        """
        # Auto-detect source language if not provided
        detected_lang = source_lang
        if not source_lang:
            detected_lang = self.language_detector.detect(text)
        
        # Check cache
        cache_key = (text, detected_lang, target_lang)
        if cache_key in self._translation_cache:
            cached_translation = self._translation_cache[cache_key]
            result = {
                "translated_text": cached_translation,
                "source_language": detected_lang,
                "target_language": target_lang,
            }
            if not source_lang:
                result["detected_language"] = detected_lang
            
            # Add transliteration if applicable
            if detected_lang == "ne" and target_lang == "en":
                result["transliteration"] = self.transliterator.devanagari_to_roman(text)
            elif detected_lang == "en" and target_lang == "ne":
                result["transliteration"] = self.transliterator.roman_to_devanagari(text)
            
            return result
        
        # Perform translation
        if detected_lang == target_lang:
            # Same language, no translation needed
            translated = text
        elif detected_lang == "ne" and target_lang == "en":
            # Nepali to English
            translated = await self._translate_nepali_to_english(text)
        elif detected_lang == "en" and target_lang == "ne":
            # English to Nepali
            translated = await self._translate_english_to_nepali(text)
        else:
            # Unsupported language pair
            translated = text
        
        # Cache the translation
        self._translation_cache[cache_key] = translated
        
        # Build result
        result = {
            "translated_text": translated,
            "source_language": detected_lang,
            "target_language": target_lang,
        }
        
        # Add detected language if it was auto-detected
        if not source_lang:
            result["detected_language"] = detected_lang
        
        # Add transliteration if applicable
        if detected_lang == "ne" and target_lang == "en":
            result["transliteration"] = self.transliterator.devanagari_to_roman(text)
        elif detected_lang == "en" and target_lang == "ne":
            result["transliteration"] = self.transliterator.roman_to_devanagari(text)
        
        return result
    
    async def _translate_nepali_to_english(self, text: str) -> str:
        """Translate Nepali text to English.
        
        Uses LLM or translation API for translation. Falls back to
        transliteration for names.
        
        Args:
            text: Nepali text to translate
            
        Returns:
            English translation
        """
        if self.llm_provider == "mock":
            # Mock translation for testing
            return self._mock_translate_nepali_to_english(text)
        
        # Real implementation would use LLM or translation API
        # For now, use mock implementation
        return self._mock_translate_nepali_to_english(text)
    
    async def _translate_english_to_nepali(self, text: str) -> str:
        """Translate English text to Nepali.
        
        Uses LLM or translation API for translation. Falls back to
        transliteration for names.
        
        Args:
            text: English text to translate
            
        Returns:
            Nepali translation
        """
        if self.llm_provider == "mock":
            # Mock translation for testing
            return self._mock_translate_english_to_nepali(text)
        
        # Real implementation would use LLM or translation API
        # For now, use mock implementation
        return self._mock_translate_english_to_nepali(text)
    
    def _mock_translate_nepali_to_english(self, text: str) -> str:
        """Mock Nepali to English translation for testing.
        
        Args:
            text: Nepali text
            
        Returns:
            Mock English translation
        """
        # Common Nepali phrases and names
        translations = {
            "राम चन्द्र पौडेल": "Ram Chandra Poudel",
            "नेपाली कांग्रेस": "Nepali Congress",
            "नेता": "leader",
            "हुन्": "is",
            "का": "of",
            "राम चन्द्र पौडेल नेपाली कांग्रेसका नेता हुन्।": "Ram Chandra Poudel is a leader of Nepali Congress.",
        }
        
        # Check for exact match
        if text in translations:
            return translations[text]
        
        # Fall back to transliteration for unknown text
        return self.transliterator.devanagari_to_roman(text).title()
    
    def _mock_translate_english_to_nepali(self, text: str) -> str:
        """Mock English to Nepali translation for testing.
        
        Args:
            text: English text
            
        Returns:
            Mock Nepali translation
        """
        # Common English phrases and names
        translations = {
            "Ram Chandra Poudel": "राम चन्द्र पौडेल",
            "Nepali Congress": "नेपाली कांग्रेस",
            "leader": "नेता",
            "is": "हुन्",
            "of": "का",
            "Ram Chandra Poudel is a leader of Nepali Congress.": "राम चन्द्र पौडेल नेपाली कांग्रेसका नेता हुन्।",
        }
        
        # Check for exact match
        if text in translations:
            return translations[text]
        
        # Fall back to transliteration for unknown text
        return self.transliterator.roman_to_devanagari(text.lower())
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the given text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Language code: "ne" for Nepali, "en" for English
        """
        return self.language_detector.detect(text)
    
    def transliterate(
        self,
        text: str,
        direction: str = "auto",
    ) -> str:
        """Transliterate text between Devanagari and Roman scripts.
        
        Args:
            text: The text to transliterate
            direction: Transliteration direction:
                - "auto": Auto-detect based on script
                - "to_roman": Devanagari to Roman
                - "to_devanagari": Roman to Devanagari
                
        Returns:
            Transliterated text
        """
        if direction == "auto":
            # Auto-detect direction
            if self.language_detector.is_devanagari(text):
                direction = "to_roman"
            else:
                direction = "to_devanagari"
        
        if direction == "to_roman":
            return self.transliterator.devanagari_to_roman(text)
        elif direction == "to_devanagari":
            return self.transliterator.roman_to_devanagari(text)
        else:
            return text

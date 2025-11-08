"""Tests for AWS Bedrock Provider.

These tests verify the AWS Bedrock provider implementation for LLM-powered
data extraction and normalization tasks.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import sys

# Mock boto3 before importing the provider
sys.modules['boto3'] = MagicMock()


class TestAWSBedrockProviderInitialization:
    """Test AWS Bedrock provider initialization."""
    
    def test_provider_initialization_default(self):
        """Test provider initialization with default settings."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider()
            
            assert provider is not None
            assert provider.region_name == "us-east-1"
            assert provider.model_id == "anthropic.claude-3-sonnet-20240229-v1:0"
            assert provider.model_family == "claude"
    
    def test_provider_initialization_custom_region(self):
        """Test provider initialization with custom region."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider(region_name="us-west-2")
            
            assert provider.region_name == "us-west-2"
    
    def test_provider_initialization_custom_model(self):
        """Test provider initialization with custom model."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider(
                model_id="anthropic.claude-3-haiku-20240307-v1:0"
            )
            
            assert provider.model_id == "anthropic.claude-3-haiku-20240307-v1:0"
            assert provider.model_family == "claude"
    
    def test_provider_initialization_invalid_model(self):
        """Test that invalid model raises ValueError."""
        with patch("boto3.Session"):
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            with pytest.raises(ValueError, match="Unsupported model"):
                AWSBedrockProvider(model_id="invalid-model-id")
    
    def test_provider_initialization_with_credentials(self):
        """Test provider initialization with explicit credentials."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider(
                aws_access_key_id="AKIA...",
                aws_secret_access_key="secret...",
            )
            
            assert provider is not None
            # Verify Session was called with credentials
            mock_session.assert_called_once()


class TestAWSBedrockProviderTextGeneration:
    """Test text generation capabilities."""
    
    @pytest.mark.asyncio
    async def test_generate_text_claude(self):
        """Test text generation with Claude model."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            # Mock Bedrock response
            mock_response = {
                "body": Mock(read=lambda: json.dumps({
                    "content": [{"text": "Generated text response"}],
                    "usage": {"input_tokens": 10, "output_tokens": 5}
                }).encode())
            }
            mock_client.invoke_model.return_value = mock_response
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider()
            result = await provider.generate_text(prompt="Test prompt")
            
            assert result == "Generated text response"
            assert provider.total_input_tokens == 10
            assert provider.total_output_tokens == 5
    
    @pytest.mark.asyncio
    async def test_generate_text_with_system_prompt(self):
        """Test text generation with system prompt."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            mock_response = {
                "body": Mock(read=lambda: json.dumps({
                    "content": [{"text": "Response with system context"}],
                    "usage": {"input_tokens": 15, "output_tokens": 8}
                }).encode())
            }
            mock_client.invoke_model.return_value = mock_response
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider()
            result = await provider.generate_text(
                prompt="User prompt",
                system_prompt="You are a helpful assistant"
            )
            
            assert result == "Response with system context"
    
    @pytest.mark.asyncio
    async def test_generate_text_titan(self):
        """Test text generation with Titan model."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            # Mock Titan response format
            mock_response = {
                "body": Mock(read=lambda: json.dumps({
                    "results": [{"outputText": "Titan generated text"}],
                    "usage": {}
                }).encode())
            }
            mock_client.invoke_model.return_value = mock_response
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider(
                model_id="amazon.titan-text-express-v1"
            )
            result = await provider.generate_text(prompt="Test prompt")
            
            assert result == "Titan generated text"


class TestAWSBedrockProviderStructuredExtraction:
    """Test structured data extraction."""
    
    @pytest.mark.asyncio
    async def test_extract_structured_data(self):
        """Test extracting structured data from text."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            # Mock response with JSON
            json_response = {"name": "Ram Chandra Poudel", "position": "President"}
            mock_response = {
                "body": Mock(read=lambda: json.dumps({
                    "content": [{"text": json.dumps(json_response)}],
                    "usage": {"input_tokens": 20, "output_tokens": 10}
                }).encode())
            }
            mock_client.invoke_model.return_value = mock_response
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider()
            schema = {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "position": {"type": "string"}
                }
            }
            
            result = await provider.extract_structured_data(
                text="Ram Chandra Poudel is the President of Nepal.",
                schema=schema,
                instructions="Extract person name and position"
            )
            
            assert result["name"] == "Ram Chandra Poudel"
            assert result["position"] == "President"
    
    @pytest.mark.asyncio
    async def test_extract_structured_data_with_markdown(self):
        """Test extracting JSON from markdown-formatted response."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            # Mock response with markdown formatting
            json_data = {"name": "Test Person", "role": "Politician"}
            markdown_response = f"```json\n{json.dumps(json_data)}\n```"
            mock_response = {
                "body": Mock(read=lambda: json.dumps({
                    "content": [{"text": markdown_response}],
                    "usage": {"input_tokens": 15, "output_tokens": 8}
                }).encode())
            }
            mock_client.invoke_model.return_value = mock_response
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider()
            result = await provider.extract_structured_data(
                text="Test text",
                schema={},
                instructions="Extract data"
            )
            
            assert result["name"] == "Test Person"
            assert result["role"] == "Politician"


class TestAWSBedrockProviderTranslation:
    """Test translation capabilities."""
    
    @pytest.mark.asyncio
    async def test_translate_nepali_to_english(self):
        """Test translating Nepali to English."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            mock_response = {
                "body": Mock(read=lambda: json.dumps({
                    "content": [{"text": "Ram Chandra Poudel"}],
                    "usage": {"input_tokens": 10, "output_tokens": 5}
                }).encode())
            }
            mock_client.invoke_model.return_value = mock_response
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider()
            result = await provider.translate(
                text="राम चन्द्र पौडेल",
                source_lang="ne",
                target_lang="en"
            )
            
            assert result == "Ram Chandra Poudel"
    
    @pytest.mark.asyncio
    async def test_translate_english_to_nepali(self):
        """Test translating English to Nepali."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            mock_response = {
                "body": Mock(read=lambda: json.dumps({
                    "content": [{"text": "राम चन्द्र पौडेल"}],
                    "usage": {"input_tokens": 10, "output_tokens": 5}
                }).encode())
            }
            mock_client.invoke_model.return_value = mock_response
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider()
            result = await provider.translate(
                text="Ram Chandra Poudel",
                source_lang="en",
                target_lang="ne"
            )
            
            assert result == "राम चन्द्र पौडेल"


class TestAWSBedrockProviderTokenTracking:
    """Test token usage tracking."""
    
    @pytest.mark.asyncio
    async def test_token_usage_tracking(self):
        """Test that token usage is tracked correctly."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            mock_response = {
                "body": Mock(read=lambda: json.dumps({
                    "content": [{"text": "Response"}],
                    "usage": {"input_tokens": 100, "output_tokens": 50}
                }).encode())
            }
            mock_client.invoke_model.return_value = mock_response
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider()
            
            # Make multiple calls
            await provider.generate_text(prompt="Test 1")
            await provider.generate_text(prompt="Test 2")
            
            usage = provider.get_token_usage()
            
            assert usage["input_tokens"] == 200
            assert usage["output_tokens"] == 100
            assert usage["total_tokens"] == 300
    
    def test_reset_token_usage(self):
        """Test resetting token usage counters."""
        with patch("boto3.Session") as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            from nes2.services.scraping.providers import AWSBedrockProvider
            
            provider = AWSBedrockProvider()
            provider.total_input_tokens = 100
            provider.total_output_tokens = 50
            
            provider.reset_token_usage()
            
            usage = provider.get_token_usage()
            assert usage["total_tokens"] == 0

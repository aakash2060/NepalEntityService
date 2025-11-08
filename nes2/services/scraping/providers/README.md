# LLM Providers for Scraping Service

This directory contains LLM provider implementations for the Nepal Entity Service scraping functionality.

## Overview

The scraping service uses LLM providers for intelligent data extraction, normalization, and translation tasks. Providers implement a common interface for text generation, structured data extraction, and translation.

## Provider Architecture

All providers implement the `BaseLLMProvider` abstract interface, ensuring consistent behavior across different LLM backends. This allows you to:

- Switch providers without changing application code
- Use provider instances directly for fine-grained control
- Create custom providers by extending `BaseLLMProvider`
- Test with mock providers without API costs

### Base Provider Interface

```python
from nes2.services.scraping.providers import BaseLLMProvider

class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate text from a prompt."""
        pass
    
    @abstractmethod
    async def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        instructions: str,
    ) -> Dict[str, Any]:
        """Extract structured data from text."""
        pass
    
    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Translate text between languages."""
        pass
```

## Supported Providers

### Mock Provider

The mock provider simulates LLM behavior without making API calls. Perfect for testing and development.

**Features:**
- No API costs or credentials required
- Deterministic responses for common tasks
- Fast execution without network latency
- Pattern-based translation and extraction

**Usage:**

```python
from nes2.services.scraping.providers import MockLLMProvider
from nes2.services.scraping import ScrapingService

# Create mock provider and service
provider = MockLLMProvider()
service = ScrapingService(llm_provider=provider)

# With custom configuration
provider = MockLLMProvider(max_tokens=4096, temperature=0.5)
service = ScrapingService(llm_provider=provider)
```

**Supported Translations:**
- राम चन्द्र पौडेल ↔ Ram Chandra Poudel
- नेपाली कांग्रेस ↔ Nepali Congress
- Common political terms

### AWS Bedrock Provider

The AWS Bedrock provider integrates with Amazon's managed LLM service, supporting multiple foundation models.

#### Supported Models

- **Anthropic Claude 3**
  - `anthropic.claude-3-sonnet-20240229-v1:0` (Balanced performance/cost)
  - `anthropic.claude-3-haiku-20240307-v1:0` (Fast, cost-effective)
  - `anthropic.claude-3-opus-20240229-v1:0` (Most capable)

- **Amazon Titan**
  - `amazon.titan-text-express-v1` (Fast, cost-effective)

#### Installation

```bash
# Install boto3 for AWS integration
pip install boto3

# Or with poetry
poetry add boto3
```

#### Configuration

AWS credentials can be configured in several ways:

1. **Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

2. **AWS Credentials File** (`~/.aws/credentials`)
```ini
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
```

3. **IAM Role** (when running on AWS infrastructure)
   - EC2 instance profile
   - ECS task role
   - Lambda execution role

#### Usage Examples

##### Basic Usage

```python
from nes2.services.scraping.providers import AWSBedrockProvider
from nes2.services.scraping import ScrapingService

# Initialize provider with default settings (Claude 3 Sonnet, us-east-1)
provider = AWSBedrockProvider()

# Use with scraping service
service = ScrapingService(llm_provider=provider)

# Or use provider directly
response = await provider.generate_text(
    prompt="Translate to English: राम चन्द्र पौडेल"
)
print(response)  # "Ram Chandra Poudel"
```

##### Custom Configuration

```python
from nes2.services.scraping.providers import AWSBedrockProvider
from nes2.services.scraping import ScrapingService

# Use specific model and region
provider = AWSBedrockProvider(
    region_name="us-west-2",
    model_id="anthropic.claude-3-opus-20240229-v1:0",
    max_tokens=4096,
    temperature=0.7
)

# Use with service
service = ScrapingService(llm_provider=provider)

# Use explicit credentials
provider = AWSBedrockProvider(
    aws_access_key_id="AKIA...",
    aws_secret_access_key="...",
    region_name="us-east-1"
)
service = ScrapingService(llm_provider=provider)
```

##### Structured Data Extraction

```python
# Extract structured data from text
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "position": {"type": "string"},
        "party": {"type": "string"}
    }
}

data = await provider.extract_structured_data(
    text="Ram Chandra Poudel is the President of Nepal and a member of Nepali Congress.",
    schema=schema,
    instructions="Extract person information including name, position, and political party"
)

print(data)
# {
#     "name": "Ram Chandra Poudel",
#     "position": "President",
#     "party": "Nepali Congress"
# }
```

##### Translation

```python
# Translate Nepali to English
translation = await provider.translate(
    text="राम चन्द्र पौडेल नेपाली कांग्रेसका नेता हुन्।",
    source_lang="ne",
    target_lang="en"
)
print(translation)
# "Ram Chandra Poudel is a leader of Nepali Congress."
```

##### Token Usage Tracking

```python
# Track token usage for cost estimation
provider = AWSBedrockProvider()

# Make several API calls
await provider.generate_text("First prompt")
await provider.generate_text("Second prompt")

# Get usage statistics
usage = provider.get_token_usage()
print(f"Total tokens: {usage['total_tokens']}")
print(f"Input tokens: {usage['input_tokens']}")
print(f"Output tokens: {usage['output_tokens']}")

# Reset counters
provider.reset_token_usage()
```

#### Integration with Scraping Service

```python
from nes2.services.scraping import ScrapingService
from nes2.services.scraping.providers import AWSBedrockProvider

# Create AWS provider
aws_provider = AWSBedrockProvider(
    region_name="us-east-1",
    model_id="anthropic.claude-3-sonnet-20240229-v1:0"
)

# Initialize scraping service with AWS provider
service = ScrapingService(llm_provider=aws_provider)

# Use service for data extraction
result = await service.extract_from_wikipedia(
    page_title="Ram_Chandra_Poudel",
    language="en"
)

# Normalize with LLM-powered extraction
normalized = await service.normalize_person_data(
    raw_data=result,
    source="wikipedia"
)
```

#### Cost Optimization

1. **Choose the right model**
   - Use Haiku for simple tasks (most cost-effective)
   - Use Sonnet for balanced performance
   - Use Opus only for complex reasoning tasks

2. **Optimize prompts**
   - Be concise and specific
   - Use lower temperature (0.3) for deterministic tasks
   - Reduce max_tokens when possible

3. **Cache responses**
   - The provider includes basic caching
   - Consider implementing application-level caching for repeated queries

4. **Monitor usage**
   - Use `get_token_usage()` to track consumption
   - Set up AWS CloudWatch alarms for cost monitoring

#### Error Handling

```python
try:
    provider = AWSBedrockProvider()
    result = await provider.generate_text("Your prompt")
except ImportError:
    print("boto3 not installed. Install with: pip install boto3")
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"API error: {e}")
```

#### Security Best Practices

1. **Never hardcode credentials** in source code
2. **Use IAM roles** when running on AWS infrastructure
3. **Apply least privilege** IAM policies
4. **Enable CloudTrail** for API call auditing
5. **Use VPC endpoints** for private connectivity
6. **Rotate credentials** regularly

#### Required IAM Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-*",
                "arn:aws:bedrock:*::foundation-model/amazon.titan-*"
            ]
        }
    ]
}
```

## Future Providers

Additional providers planned for future implementation:

- **OpenAI Provider** - GPT-4, GPT-3.5 Turbo
- **Google Provider** - Gemini Pro, Gemini Ultra
- **Anthropic Provider** - Direct Claude API
- **Cohere Provider** - Command models
- **Local Provider** - Ollama, LM Studio

## Testing

Tests use mocked boto3 clients to avoid requiring AWS credentials:

```bash
# Run provider tests
poetry run pytest tests2/services/scraping/test_aws_provider.py -v

# Run all scraping service tests
poetry run pytest tests2/services/ -v
```

## Contributing

When adding new providers:

1. Implement the common provider interface
2. Add comprehensive tests with mocked dependencies
3. Document configuration and usage
4. Include error handling and logging
5. Update this README with provider details

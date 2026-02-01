import os
from typing import Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from services.utils.logger import logger

# Optional imports with fallbacks
try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    ChatGoogleGenerativeAI = None

try:
    from langchain_community.llms import Ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    Ollama = None


class ModelType(Enum):
    """Enum for different model types"""
    GENERAL = "general"
    MINI = "mini"
    REASONING = "reasoning"
    CHAT = "chat"
    EMBEDDING = "embedding"


class UserLevel(Enum):
    """Enum for different user levels"""
    JUNIOR = "junior"
    SENIOR = "senior"
    SCIENTIST = "scientist"


class ModelProvider(Enum):
    """Enum for different model providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    AZURE = "azure"


@dataclass
class ModelConfig:
    """Configuration class for model settings"""
    model_name: str
    provider: ModelProvider
    temperature: float = 0.0
    seed: Optional[int] = None
    max_tokens: Optional[int] = None
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    additional_params: Optional[Dict[str, Any]] = None


class LLMOrchestrator:
    """
    LLM Orchestrator class to manage different language models based on environment variables.
    Supports multiple providers and model types with flexible configuration.
    """
    
    # Level-based model configurations
    LEVEL_CONFIGS = {
        UserLevel.JUNIOR: {
            ModelType.GENERAL: ModelConfig(
                model_name="gpt-4.1-mini",
                provider=ModelProvider.OPENAI,
                temperature=0.0,
                seed=101
            ),
            ModelType.MINI: ModelConfig(
                model_name="gpt-4o-mini", 
                provider=ModelProvider.OPENAI,
                temperature=0.0,
                seed=101
            ),
            ModelType.REASONING: ModelConfig(
                model_name="o3-mini",
                provider=ModelProvider.OPENAI,
                temperature=0.0,  
                seed=101
            ),
            ModelType.CHAT: ModelConfig(
                model_name="o3-mini",
                provider=ModelProvider.OPENAI,
                temperature=0.0,
                seed=101
            ),
            ModelType.EMBEDDING: ModelConfig(
                model_name="text-embedding-3-small",
                provider=ModelProvider.OPENAI,
                temperature=0.0
            )
        },
        UserLevel.SENIOR: {
            ModelType.GENERAL: ModelConfig(
                model_name="gpt-4.1",
                provider=ModelProvider.OPENAI,
                temperature=0.0,
                seed=101
            ),
            ModelType.MINI: ModelConfig(
                model_name="gpt-4.1-mini", 
                provider=ModelProvider.OPENAI,
                temperature=0.0,
                seed=101
            ),
            ModelType.REASONING: ModelConfig(
                model_name="o3",
                provider=ModelProvider.OPENAI,
                temperature=0.0,  
                seed=101
            ),
            ModelType.CHAT: ModelConfig(
                model_name="o3",
                provider=ModelProvider.OPENAI,
                temperature=0.0,
                seed=101
            ),
            ModelType.EMBEDDING: ModelConfig(
                model_name="text-embedding-3-small",
                provider=ModelProvider.OPENAI,
                temperature=0.0
            )
        },
        UserLevel.SCIENTIST: {
            ModelType.GENERAL: ModelConfig(
                model_name="gpt-4.1",
                provider=ModelProvider.OPENAI,
                temperature=0.0,
                seed=101
            ),
            ModelType.MINI: ModelConfig(
                model_name="gpt-4.1-mini", 
                provider=ModelProvider.OPENAI,
                temperature=0.0,
                seed=101
            ),
            ModelType.REASONING: ModelConfig(
                model_name="claude-sonnet-4",
                provider=ModelProvider.ANTHROPIC,
                temperature=0.0,  
                seed=101
            ),
            ModelType.CHAT: ModelConfig(
                model_name="o3",
                provider=ModelProvider.OPENAI,
                temperature=0.0,
                seed=101
            ),
            ModelType.EMBEDDING: ModelConfig(
                model_name="text-embedding-3-small",
                provider=ModelProvider.OPENAI,
                temperature=0.0
            )
        }
    }
    
    # Fallback default configs (Senior level)
    DEFAULT_CONFIGS = LEVEL_CONFIGS[UserLevel.SENIOR]
    
    # Environment variable mappings
    ENV_MAPPINGS = {
        ModelType.GENERAL: "MODEL",
        ModelType.MINI: "MINI_MODEL", 
        ModelType.REASONING: "REASONING_MODEL",
        ModelType.CHAT: "CHAT_MODEL",
        ModelType.EMBEDDING: "EMBEDDING_MODEL"
    }
    
    def __init__(self, project: Optional[str] = None, global_seed: Optional[int] = None, user_level: Optional[str] = None):
        """
        Initialize the LLM Orchestrator
        
        Args:
            project: Project name for project-specific environment variables
            global_seed: Global seed value to use for all models
            user_level: User level (junior, senior, scientist) or None for auto-detection
        """
        self.project = project
        self.global_seed = global_seed or int(os.environ.get("SEED", "101"))
        self._model_cache: Dict[str, BaseChatModel] = {}
        
        # Determine user level
        self.user_level = self._determine_user_level(user_level)
        
        logger.info(f"LLM Orchestrator initialized for project: {project}, level: {self.user_level.value}")
    
    def _determine_user_level(self, user_level: Optional[str]) -> UserLevel:
        """
        Determine user level from parameter or environment variables
        
        Args:
            user_level: Explicit user level or None for auto-detection
            
        Returns:
            UserLevel enum
        """
        if user_level:
            try:
                return UserLevel(user_level.lower())
            except ValueError:
                logger.warning(f"Invalid user level '{user_level}', checking environment variables")
        
        # Check environment variables
        level_env = self._get_env_value(None, "USER_LEVEL") or self._get_env_value(None, "SKILL_LEVEL")
        if level_env:
            try:
                return UserLevel(level_env.lower())
            except ValueError:
                logger.warning(f"Invalid user level in environment '{level_env}', defaulting to SENIOR")
        
        # Default to SENIOR level
        logger.info("No user level specified, defaulting to SENIOR")
        return UserLevel.SENIOR
    
    def _get_env_value(self, model_type: ModelType, env_key: str) -> Optional[str]:
        """
        Get environment variable value with project-specific fallback
        
        Args:
            model_type: Type of model
            env_key: Environment variable key
            
        Returns:
            Environment variable value or None
        """
        if self.project:
            # Try project-specific env var first
            project_env_key = f"{self.project.upper()}_{env_key}"
            value = os.environ.get(project_env_key)
            if value:
                logger.debug(f"Using project-specific {project_env_key}={value}")
                return value
        
        # Fallback to global env var
        value = os.environ.get(env_key)
        if value:
            logger.debug(f"Using global {env_key}={value}")
        return value
    
    def _parse_model_string(self, model_string: str) -> ModelConfig:
        """
        Parse model string to determine provider and configuration
        
        Args:
            model_string: Model string (e.g., "gpt-4o", "claude-3-sonnet", "gemini-pro")
            
        Returns:
            ModelConfig object
        """
        model_string = model_string.lower().strip()
        
        # OpenAI models
        if any(keyword in model_string for keyword in ["gpt", "o1", "o3", "text-embedding"]):
            return ModelConfig(
                model_name=model_string,
                provider=ModelProvider.OPENAI,
                api_key_env="OPENAI_API_KEY"
            )
        
        # Anthropic models
        elif any(keyword in model_string for keyword in ["claude", "sonnet", "haiku", "opus"]):
            return ModelConfig(
                model_name=model_string,
                provider=ModelProvider.ANTHROPIC,
                api_key_env="ANTHROPIC_API_KEY"
            )
        
        # Google models
        elif any(keyword in model_string for keyword in ["gemini", "palm", "bard"]):
            return ModelConfig(
                model_name=model_string,
                provider=ModelProvider.GOOGLE,
                api_key_env="GOOGLE_API_KEY"
            )
        
        # Ollama models (local)
        elif any(keyword in model_string for keyword in ["llama", "mistral", "codellama", "ollama"]):
            return ModelConfig(
                model_name=model_string,
                provider=ModelProvider.OLLAMA,
                base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            )
        
        # Azure OpenAI
        elif "azure" in model_string or os.environ.get("AZURE_OPENAI_ENDPOINT"):
            return ModelConfig(
                model_name=model_string.replace("azure-", ""),
                provider=ModelProvider.AZURE,
                api_key_env="AZURE_OPENAI_API_KEY",
                base_url=os.environ.get("AZURE_OPENAI_ENDPOINT")
            )
            
        # Default to OpenAI
        else:
            logger.warning(f"Unknown model string '{model_string}', defaulting to OpenAI")
            return ModelConfig(
                model_name=model_string,
                provider=ModelProvider.OPENAI,
                api_key_env="OPENAI_API_KEY"
            )
    
    def _create_llm_instance(self, config: ModelConfig) -> BaseChatModel:
        """
        Create LLM instance based on configuration
        
        Args:
            config: Model configuration
            
        Returns:
            LangChain LLM instance
        """
        # Check if this is an OpenAI reasoning model that doesn't support temperature
        is_reasoning_model = any(keyword in config.model_name.lower() for keyword in ["o1", "o3"])

        common_params = {
            "model_name" if config.provider != ModelProvider.OPENAI else "model": config.model_name
        }

        # Add temperature only if supported (skip for OpenAI reasoning models)
        if not (config.provider == ModelProvider.OPENAI and is_reasoning_model):
            common_params["temperature"] = config.temperature

        # Add seed if supported and provided
        if config.seed and config.provider in [ModelProvider.OPENAI, ModelProvider.AZURE]:
            common_params["seed"] = config.seed

        # Add max_tokens if provided
        if config.max_tokens:
            common_params["max_tokens"] = config.max_tokens

        # Add additional parameters
        if config.additional_params:
            common_params.update(config.additional_params)

        try:
            if config.provider == ModelProvider.OPENAI:
                api_key = self._get_env_value(None, config.api_key_env or "OPENAI_API_KEY")
                return ChatOpenAI(
                    api_key=api_key,
                    **common_params
                )

            elif config.provider == ModelProvider.ANTHROPIC:
                if not ANTHROPIC_AVAILABLE:
                    raise ImportError(
                        "langchain-anthropic package is required for Anthropic models. Install with: pip install langchain-anthropic")

                api_key = self._get_env_value(None, config.api_key_env or "ANTHROPIC_API_KEY")
                return ChatAnthropic(
                    anthropic_api_key=api_key,
                    model_name=config.model_name,
                    temperature=config.temperature,
                    **(config.additional_params or {})
                )

            elif config.provider == ModelProvider.GOOGLE:
                if not GOOGLE_AVAILABLE:
                    raise ImportError(
                        "langchain-google-genai package is required for Google models. Install with: pip install langchain-google-genai")

                api_key = self._get_env_value(None, config.api_key_env or "GOOGLE_API_KEY")
                return ChatGoogleGenerativeAI(
                    google_api_key=api_key,
                    model=config.model_name,
                    temperature=config.temperature,
                    **(config.additional_params or {})
                )

            elif config.provider == ModelProvider.OLLAMA:
                if not OLLAMA_AVAILABLE:
                    raise ImportError(
                        "langchain-community package is required for Ollama models. Install with: pip install langchain-community")

                return Ollama(
                    model=config.model_name,
                    base_url=config.base_url or "http://localhost:11434",
                    temperature=config.temperature,
                    **(config.additional_params or {})
                )

            elif config.provider == ModelProvider.AZURE:
                return ChatOpenAI(
                    azure_endpoint=config.base_url,
                    api_key=self._get_env_value(None, config.api_key_env or "AZURE_OPENAI_API_KEY"),
                    api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                    azure_deployment=config.model_name,
                    **{k: v for k, v in common_params.items() if k != "model"}
                )

            else:
                raise ValueError(f"Unsupported provider: {config.provider}")

        except Exception as e:
            logger.error(f"Failed to create LLM instance for {config.provider.value}/{config.model_name}: {e}")
            raise

    def get_model_config(self, model_type: ModelType) -> ModelConfig:
        """
        Get model configuration for a specific model type
        
        Args:
            model_type: Type of model to get configuration for
            
        Returns:
            ModelConfig object
        """
        # Start with level-based config
        level_configs = self.LEVEL_CONFIGS.get(self.user_level, self.DEFAULT_CONFIGS)
        default_config = level_configs.get(model_type)
        
        if not default_config:
            # Fallback to DEFAULT_CONFIGS if not found in level config
            default_config = self.DEFAULT_CONFIGS.get(model_type)
            if not default_config:
                raise ValueError(f"No configuration for model type: {model_type}")
        
        # Check for explicit environment variable override
        env_key = self.ENV_MAPPINGS.get(model_type)
        if env_key:
            env_model = self._get_env_value(model_type, env_key)
            if env_model:
                logger.info(f"Overriding {model_type.value} model with environment variable: {env_model}")
                # Parse the environment model string
                parsed_config = self._parse_model_string(env_model)
                # Merge with default config
                config = ModelConfig(
                    model_name=parsed_config.model_name,
                    provider=parsed_config.provider,
                    temperature=default_config.temperature,
                    seed=self.global_seed,
                    max_tokens=default_config.max_tokens,
                    api_key_env=parsed_config.api_key_env,
                    base_url=parsed_config.base_url,
                    additional_params=default_config.additional_params
                )
                return config
        
        # Return level-based config with global seed
        config_copy = ModelConfig(
            model_name=default_config.model_name,
            provider=default_config.provider,
            temperature=default_config.temperature,
            seed=self.global_seed,
            max_tokens=default_config.max_tokens,
            api_key_env=default_config.api_key_env,
            base_url=default_config.base_url,
            additional_params=default_config.additional_params
        )
        return config_copy
    
    def get_llm(self, model_type: ModelType, use_cache: bool = True) -> BaseChatModel:
        """
        Get LLM instance for a specific model type
        
        Args:
            model_type: Type of model to retrieve
            use_cache: Whether to use cached instance
            
        Returns:
            LangChain LLM instance
        """
        cache_key = f"{self.project or 'global'}_{model_type.value}"
        
        if use_cache and cache_key in self._model_cache:
            logger.debug(f"Returning cached LLM for {model_type.value}")
            return self._model_cache[cache_key]
        
        config = self.get_model_config(model_type)
        llm_instance = self._create_llm_instance(config)
        
        if use_cache:
            self._model_cache[cache_key] = llm_instance
        
        logger.info(f"Created LLM instance: {config.provider.value}/{config.model_name} for {model_type.value}")
        return llm_instance
    
    def get_general_llm(self) -> BaseChatModel:
        """Get general purpose LLM"""
        return self.get_llm(ModelType.GENERAL)
    
    def get_mini_llm(self) -> BaseChatModel:
        """Get mini/lightweight LLM"""
        return self.get_llm(ModelType.MINI)
    
    def get_reasoning_llm(self) -> BaseChatModel:
        """Get reasoning LLM"""
        return self.get_llm(ModelType.REASONING)
    
    def get_chat_llm(self) -> BaseChatModel:
        """Get chat LLM"""
        return self.get_llm(ModelType.CHAT)
    
    def get_embedding_llm(self) -> BaseChatModel:
        """Get embedding LLM"""
        return self.get_llm(ModelType.EMBEDDING)
    
    def clear_cache(self):
        """Clear the model cache"""
        self._model_cache.clear()
        logger.info("Model cache cleared")
    
    def get_available_models(self) -> Dict[str, str]:
        """
        Get available models configuration
        
        Returns:
            Dictionary of model types and their configured model names
        """
        available = {"user_level": self.user_level.value}
        for model_type in ModelType:
            try:
                config = self.get_model_config(model_type)
                available[model_type.value] = f"{config.provider.value}/{config.model_name}"
            except Exception as e:
                available[model_type.value] = f"Error: {e}"
        
        return available
    
    def get_level_configurations(self) -> Dict[str, Dict[str, str]]:
        """
        Get all level configurations for comparison
        
        Returns:
            Dictionary of all level configurations
        """
        all_configs = {}
        for level in UserLevel:
            level_config = {}
            for model_type in ModelType:
                config = self.LEVEL_CONFIGS[level].get(model_type, self.DEFAULT_CONFIGS.get(model_type))
                if config:
                    level_config[model_type.value] = f"{config.provider.value}/{config.model_name}"
            all_configs[level.value] = level_config
        
        return all_configs
    
    def validate_configuration(self) -> Dict[str, bool]:
        """
        Validate that all required API keys and configurations are available
        
        Returns:
            Dictionary of model types and their validation status
        """
        validation_results = {}
        
        for model_type in ModelType:
            try:
                config = self.get_model_config(model_type)
                
                # Check API key if required
                if config.api_key_env:
                    api_key = self._get_env_value(model_type, config.api_key_env)
                    if not api_key:
                        validation_results[model_type.value] = False
                        logger.warning(f"Missing API key for {model_type.value}: {config.api_key_env}")
                        continue
                
                # Try to create instance (but don't cache it)
                self._create_llm_instance(config)
                validation_results[model_type.value] = True
                
            except Exception as e:
                validation_results[model_type.value] = False
                logger.error(f"Validation failed for {model_type.value}: {e}")
        
        return validation_results


# Usage example and helper functions
def create_orchestrator(project: Optional[str] = None, user_level: Optional[str] = None) -> LLMOrchestrator:
    """
    Factory function to create LLM orchestrator
    
    Args:
        project: Project name
        user_level: User level (junior, senior, scientist)
        
    Returns:
        LLMOrchestrator instance
    """
    return LLMOrchestrator(project=project, user_level=user_level)


# Example usage in your existing code
def example_usage():
    """Example of how to use the LLM Orchestrator with levels"""
    
    # Create orchestrator with specific level
    orchestrator = LLMOrchestrator(project="my_project", user_level="scientist")
    
    # Or let it auto-detect from environment
    # export USER_LEVEL=junior
    orchestrator_auto = LLMOrchestrator(project="my_project")
    
    # Get different types of models (will use level-appropriate models)
    general_llm = orchestrator.get_general_llm()      # gpt-4.1 for scientist
    mini_llm = orchestrator.get_mini_llm()            # gpt-4.1-mini for scientist
    reasoning_llm = orchestrator.get_reasoning_llm()  # claude-sonnet-4 for scientist
    chat_llm = orchestrator.get_chat_llm()            # o3 for scientist
    embedding_llm = orchestrator.get_embedding_llm()  # text-embedding-3-small
    
    # Check available models for current level
    available = orchestrator.get_available_models()
    print("Available models:", available)
    
    # Compare all level configurations
    all_levels = orchestrator.get_level_configurations()
    print("All level configurations:", all_levels)
    
    # Override with environment variable
    # export REASONING_MODEL=o1-preview
    # This will override the scientist-level default (claude-sonnet-4)
    
    # Validate configuration
    validation = orchestrator.validate_configuration()
    print("Validation results:", validation)
    
    return {
        "general": general_llm,
        "mini": mini_llm, 
        "reasoning": reasoning_llm,
        "chat": chat_llm,  
        "embedding": embedding_llm
    }
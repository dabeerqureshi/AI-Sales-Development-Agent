import logging
from typing import List, Tuple
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaService:
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, model: str = settings.OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def check_health(self) -> Tuple[bool, bool, List[str], str]:
        """
        Checks whether Ollama is reachable and whether the configured model is available.
        Returns: (is_reachable, is_model_available, list_of_available_models, error_message)
        """
        tags_url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(tags_url)
                if response.status_code == 200:
                    data = response.json()
                    models_raw = data.get("models", [])
                    available_models = [m.get("name", "") for m in models_raw if "name" in m]
                    
                    # Model check: match exact or name without tag (e.g. qwen3:4b or qwen3:4b-latest)
                    target_model = self.model.lower()
                    model_found = any(
                        target_model in m.lower() or m.lower() in target_model
                        for m in available_models
                    )
                    
                    error_msg = ""
                    if not model_found:
                        error_msg = f"Model '{self.model}' not found in Ollama. Run: ollama pull {self.model}"
                    
                    return True, model_found, available_models, error_msg
                else:
                    return False, False, [], f"Ollama returned HTTP status {response.status_code}"
        except httpx.ConnectError:
            return False, False, [], f"Could not connect to Ollama at {self.base_url}. Ensure 'ollama serve' is running."
        except httpx.TimeoutException:
            return False, False, [], f"Connection timed out when reaching Ollama at {self.base_url}."
        except Exception as e:
            return False, False, [], f"Unexpected error connecting to Ollama: {str(e)}"


ollama_service = OllamaService()

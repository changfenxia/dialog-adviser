import easyocr
import re
from typing import List
from yandex_cloud_ml_sdk import YCloudML
import logging
import aiohttp
import json

logger = logging.getLogger(__name__)

class TextRecognizer:
    def __init__(self):
        self.reader = easyocr.Reader(['ru', 'en'])
    
    async def extract_text_from_images(self, image_paths: List[str]) -> str:
        full_text = []
        
        for image_path in image_paths:
            result = self.reader.readtext(image_path)
            text = ' '.join([item[1] for item in result])
            full_text.append(text)
            
        return '\n'.join(full_text)

    def format_dialog(self, text: str) -> str:
        # Basic dialog formatting - can be improved based on actual input patterns
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Try to identify speaker patterns (e.g., "Name:", "Name -", etc.)
            if ':' in line or '-' in line:
                formatted_lines.append(line)
            else:
                formatted_lines.append(f"Person: {line}")
                
        return '\n'.join(formatted_lines)

class YandexGPTClient:
    def __init__(self, api_key: str, folder_id: str):
        try:
            if not folder_id or not api_key:
                raise ValueError("Missing Yandex credentials")
            
            self.sdk = YCloudML(folder_id=folder_id, auth=api_key)
            self.model = self.sdk.models.completions('yandexgpt')
            self.model = self.model.configure(temperature=0.7)
            logger.info("YandexGPT client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize YandexGPT client: {e}")
            raise

    async def generate_response(self, prompt: str) -> str:
        try:
            result = self.model.run(prompt)
            
            # Extract text from the first alternative
            for alternative in result:
                return alternative.text
                
            return "Извините, не удалось сгенерировать ответ."
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
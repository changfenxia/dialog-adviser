import logging
import easyocr
from typing import List
from yandex_cloud_ml_sdk import YCloudML
from config import (
    YANDEX_GPT_MODEL, 
    GPT_TEMPERATURE, 
    GPT_MAX_TOKENS,
    logger
)

class TextRecognizer:
    def __init__(self):
        logger.info("Initializing TextRecognizer...")
        self.reader = easyocr.Reader(['ru', 'en'])
        logger.info("TextRecognizer initialized successfully")
    
    async def extract_text_from_images(self, image_paths: List[str]) -> str:
        logger.info(f"Starting text extraction from images: {image_paths}")
        full_text = []
        
        for image_path in image_paths:
            try:
                logger.info(f"Processing image: {image_path}")
                result = self.reader.readtext(image_path)
                logger.info(f"Raw OCR result: {result}")
                
                text = ' '.join([item[1] for item in result])
                logger.info(f"Extracted text: {text}")
                full_text.append(text)
            except Exception as e:
                logger.error(f"Error processing image {image_path}: {e}")
                raise
            
        final_text = '\n'.join(full_text)
        logger.info(f"Final combined text: {final_text}")
        return final_text

    def format_dialog(self, text: str) -> str:
        logger.info(f"Formatting dialog text: {text}")
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            if ':' in line or '-' in line:
                formatted_lines.append(line)
            else:
                formatted_lines.append(f"Person: {line}")
        
        result = '\n'.join(formatted_lines)
        logger.info(f"Formatted dialog: {result}")
        return result

class YandexGPTClient:
    def __init__(self, api_key: str, folder_id: str):
        logger.info("Initializing YandexGPTClient...")
        try:
            if not folder_id or not api_key:
                raise ValueError("Missing Yandex credentials")
            
            self.sdk = YCloudML(folder_id=folder_id, auth=api_key)
            self.model = self.sdk.models.completions(YANDEX_GPT_MODEL)
            self.model = self.model.configure(
                temperature=GPT_TEMPERATURE,
                max_tokens=GPT_MAX_TOKENS
            )
            logger.info(f"YandexGPTClient initialized successfully with model={YANDEX_GPT_MODEL}, "
                       f"temperature={GPT_TEMPERATURE}, max_tokens={GPT_MAX_TOKENS}")
        except Exception as e:
            logger.error(f"Failed to initialize YandexGPTClient: {e}")
            raise

    async def generate_response(self, prompt: str) -> str:
        logger.info("Generating response from YandexGPT")
        logger.info(f"Prompt: {prompt}")
        try:
            result = self.model.run(prompt)
            
            for alternative in result:
                response = alternative.text
                logger.info(f"Generated response: {response}")
                return response
                
            logger.warning("No response generated")
            return "Извините, не удалось сгенерировать ответ."
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже." 
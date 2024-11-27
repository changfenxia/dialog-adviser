import logging
from dotenv import load_dotenv
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
YANDEX_AUTH_TOKEN = os.getenv('YANDEX_AUTH_TOKEN')
YANDEX_FOLDER_ID = os.getenv('YANDEX_FOLDER_ID')

# YandexGPT prompts
ANALYZE_PROMPT = """Действуй как опытный психолог. Проанализируй следующий диалог и дай профессиональную оценку 
взаимодействию между собеседниками, их намерениям и чувствам:

{dialog}

Предоставь развернутый анализ."""

ADVICE_PROMPT = """Действуй как опытный психолог. Прочитай следующий диалог и посоветуй, как лучше всего 
ответить дальше, чтобы улучшить коммуникацию и достичь положительного результата:

{dialog}

Дай конкретный совет, что написать дальше."""

# Existing code... 
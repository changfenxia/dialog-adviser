import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import os
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).resolve().parent
if str(app_dir) not in sys.path:
    sys.path.append(str(app_dir))

from config import BOT_TOKEN, YANDEX_AUTH_TOKEN, YANDEX_FOLDER_ID, ANALYZE_PROMPT, ADVICE_PROMPT
from utils import TextRecognizer, YandexGPTClient

# Initialize logging
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
text_recognizer = TextRecognizer()
gpt_client = YandexGPTClient(YANDEX_AUTH_TOKEN, YANDEX_FOLDER_ID)

class DialogStates(StatesGroup):
    waiting_for_images = State()
    ready_for_analysis = State()

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await DialogStates.waiting_for_images.set()
    await message.answer(
        "Привет! Я помогу проанализировать ваш диалог и дать советы по общению.\n"
        "Отправьте мне скриншот диалога (можно загрузить до 3 скриншотов)."
    )

@dp.message_handler(content_types=['photo'], state=DialogStates.waiting_for_images)
async def handle_photos(message: types.Message, state: FSMContext):
    logger.info("Received photo message")
    async with state.proxy() as data:
        if 'photos' not in data:
            data['photos'] = []
            
        if len(data['photos']) >= 3:
            logger.warning("Maximum number of photos reached")
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add("Отправить диалог")
            await message.answer(
                "Достигнуто максимальное количество фотографий (3).\n"
                "Нажмите 'Отправить диалог' для анализа.",
                reply_markup=keyboard
            )
            return
            
        try:
            photo = message.photo[-1]
            file_path = f"temp_{len(data['photos'])}.jpg"
            logger.info(f"Saving photo to {file_path}")
            await photo.download(file_path)
            data['photos'].append(file_path)
            photos_count = len(data['photos'])
            logger.info(f"Photo saved successfully. Total photos: {photos_count}")
            
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add("Отправить диалог")
            
            if photos_count >= 3:
                await message.answer(
                    "Достигнуто максимальное количество фотографий (3).\n"
                    "Нажмите 'Отправить диалог' для анализа.",
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    f"Фото {photos_count} загружено.\n"
                    f"Отправьте ещё один скриншот или нажмите 'Отправить диалог' для анализа.",
                    reply_markup=keyboard
                )
                
        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            await message.answer("Произошла ошибка при обработке фото. Пожалуйста, попробуйте еще раз.")

@dp.message_handler(text="Отправить диалог", state=DialogStates.waiting_for_images)
async def process_images(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if not data.get('photos'):
            await message.answer("Сначала отправьте хотя бы один скриншот диалога.")
            return
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Что сказать?", callback_data="advice"),
            types.InlineKeyboardButton("Анализ диалога", callback_data="analyze")
        )
        await message.answer(
            "Начинаю анализ диалога.\n"
            "Выберите тип анализа:",
            reply_markup=keyboard
        )
        await DialogStates.ready_for_analysis.set()

@dp.callback_query_handler(lambda c: c.data in ['advice', 'analyze'], state=DialogStates.ready_for_analysis)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    logger.info(f"Processing callback: {callback_query.data}")
    await callback_query.message.answer("Анализирую диалог...")
    
    async with state.proxy() as data:
        try:
            image_paths = data['photos']
            logger.info(f"Processing images: {image_paths}")
            
            text = await text_recognizer.extract_text_from_images(image_paths)
            logger.info(f"Extracted text: {text}")
            
            formatted_dialog = text_recognizer.format_dialog(text)
            logger.info(f"Formatted dialog: {formatted_dialog}")
            
            # Clean up temporary files
            for path in image_paths:
                try:
                    os.remove(path)
                    logger.info(f"Removed temporary file: {path}")
                except Exception as e:
                    logger.error(f"Error removing file {path}: {e}")
            
            prompt = ADVICE_PROMPT if callback_query.data == 'advice' else ANALYZE_PROMPT
            prompt = prompt.format(dialog=formatted_dialog)
            logger.info(f"Generated prompt: {prompt}")
            
            response = await gpt_client.generate_response(prompt)
            logger.info(f"Got response from GPT: {response}")
            
            await callback_query.message.answer(response)
            logger.info("Sent response to user")
            
        except Exception as e:
            logger.error(f"Error processing callback: {e}")
            await callback_query.message.answer("Произошла ошибка при обработке запроса. Пожалуйста, попробуйте еще раз.")
        
    await state.finish()
    logger.info("Finished processing callback")

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
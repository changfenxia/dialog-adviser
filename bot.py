from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import os
from config import BOT_TOKEN, YANDEX_AUTH_TOKEN, YANDEX_FOLDER_ID, ANALYZE_PROMPT, ADVICE_PROMPT
from utils import TextRecognizer, YandexGPTClient

class DialogStates(StatesGroup):
    waiting_for_images = State()

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
text_recognizer = TextRecognizer()
gpt_client = YandexGPTClient(YANDEX_AUTH_TOKEN, YANDEX_FOLDER_ID)

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(types.KeyboardButton("Отправить диалог"))
    
    await message.answer(
        "Привет! Я помогу проанализировать ваш диалог и дать советы по общению. "
        "Нажмите кнопку 'Отправить диалог' и отправьте мне 1-3 скриншота диалога.",
        reply_markup=keyboard
    )

@dp.message_handler(text="Отправить диалог")
async def request_images(message: types.Message):
    await DialogStates.waiting_for_images.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(types.KeyboardButton("Отправить диалог"))
    
    await message.answer(
        "Пожалуйста, отправьте от 1 до 3 скриншотов диалога.",
        reply_markup=keyboard
    )

@dp.message_handler(content_types=['photo'], state=DialogStates.waiting_for_images)
async def handle_photos(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if 'photos' not in data:
            data['photos'] = []
            
        if len(data['photos']) >= 3:
            await message.answer("Вы уже отправили максимальное количество фотографий (3).")
            return
            
        # Save photo
        photo = message.photo[-1]
        file_path = f"temp_{len(data['photos'])}.jpg"
        await photo.download(file_path)
        data['photos'].append(file_path)
        
        if len(data['photos']) >= 1:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton("Что сказать?", callback_data="advice"),
                types.InlineKeyboardButton("Анализ диалога", callback_data="analyze")
            )
            await message.answer("Выберите действие:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data in ['advice', 'analyze'], state=DialogStates.waiting_for_images)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        image_paths = data['photos']
        
        # Extract text from images
        text = await text_recognizer.extract_text_from_images(image_paths)
        formatted_dialog = text_recognizer.format_dialog(text)
        
        # Clean up temporary files
        for path in image_paths:
            os.remove(path)
            
        # Generate response based on callback type
        prompt = ADVICE_PROMPT if callback_query.data == 'advice' else ANALYZE_PROMPT
        prompt = prompt.format(dialog=formatted_dialog)
        
        response = await gpt_client.generate_response(prompt)
        await callback_query.message.answer(response)
        
    await state.finish()

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True) 
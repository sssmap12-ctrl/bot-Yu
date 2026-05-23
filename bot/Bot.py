import os
import asyncio
import yt_dlp
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
import logging
import shutil
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Конфигурация
TOKEN = "8841128083:AAHNLQNSY6TPuOAzNO_aGbOBEIbkFVTvCoA"  # Замените на токен вашего бота
DOWNLOAD_PATH = "downloads"

# Создаем папку для скачивания
Path(DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)

# Инициализация бота
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Настройки для yt-dlp
def get_ydl_opts(output_path):
    return {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            },
            {
                'key': 'FFmpegMetadata',
            },
            {
                'key': 'EmbedThumbnail',
            }
        ],
        'writethumbnail': True,
        'embedsubs': False,
        'embedthumbnail': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
    }

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🎵 *YouTube Music Downloader*\n\n"
        "Я могу скачать аудио из YouTube видео и отправить тебе MP3 файл с обложкой!\n\n"
        "📌 *Как использовать:*\n"
        "Просто отправь мне ссылку на YouTube видео\n\n"
        "🔧 *Команды:*\n"
        "/start - Показать это сообщение\n"
        "/help - Помощь\n"
        "/stats - Статистика бота\n\n"
        "⚡ *Поддерживаются:*\n"
        "• Обычные видео\n"
        "• YouTube Shorts\n\n"
        "✨ Обложка автоматически встраивается в аудио!",
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 *Помощь*\n\n"
        "1. Скопируйте ссылку на YouTube видео\n"
        "2. Отправьте её мне\n"
        "3. Дождитесь загрузки и обработки\n"
        "4. Получите MP3 файл с обложкой!\n\n"
        "*Примеры ссылок:*\n"
        "• `https://youtube.com/watch?v=...`\n"
        "• `https://youtu.be/...`\n"
        "• `https://youtube.com/shorts/...`\n\n"
        "⚠️ *Примечание:* Большие файлы могут загружаться дольше.",
        parse_mode="Markdown"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    # Подсчет файлов в папке за сегодня
    today = datetime.now().strftime("%Y-%m-%d")
    files = list(Path(DOWNLOAD_PATH).glob(f"*"))
    
    stats_text = (
        f"📊 *Статистика бота*\n\n"
        f"📁 Всего скачано файлов: {len(files)}\n"
        f"💾 Место занято: {get_folder_size(DOWNLOAD_PATH):.2f} MB\n"
        f"🔄 Бот активен и готов к работе!\n\n"
        f"⚡ *Лимиты Telegram:*\n"
        f"• Максимальный размер файла: 50 MB\n"
        f"• Если трек больше 50 MB, я не смогу его отправить"
    )
    await message.answer(stats_text, parse_mode="Markdown")

def get_folder_size(folder):
    total = 0
    for path in Path(folder).iterdir():
        if path.is_file():
            total += path.stat().st_size
        elif path.is_dir():
            total += get_folder_size(path)
    return total / (1024 * 1024)  # В MB

def clean_old_files(hours=24):
    """Удаляет файлы старше указанного количества часов"""
    now = datetime.now()
    for file in Path(DOWNLOAD_PATH).glob("*"):
        if file.is_file():
            file_time = datetime.fromtimestamp(file.stat().st_mtime)
            if (now - file_time).total_seconds() > hours * 3600:
                try:
                    os.remove(file)
                    logging.info(f"Удален старый файл: {file.name}")
                except Exception as e:
                    logging.error(f"Ошибка удаления {file.name}: {e}")

async def download_audio(url, message_id):
    """Асинхронное скачивание аудио"""
    # Создаем уникальную папку для этого запроса
    user_folder = os.path.join(DOWNLOAD_PATH, str(message_id))
    Path(user_folder).mkdir(parents=True, exist_ok=True)
    
    ydl_opts = get_ydl_opts(user_folder)
    
    try:
        # Запускаем скачивание в отдельном потоке
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            
            # Находим скачанный файл
            for file in Path(user_folder).glob("*.mp3"):
                return file, info.get('title', 'track')
        
        return None, None
    except Exception as e:
        logging.error(f"Ошибка скачивания: {e}")
        return None, None

@dp.message()
async def handle_youtube_url(message: Message):
    text = message.text.strip()
    
    # Проверяем, является ли сообщение ссылкой на YouTube
    if not ('youtube.com' in text.lower() or 'youtu.be' in text.lower()):
        await message.answer(
            "❌ Пожалуйста, отправьте корректную ссылку на YouTube видео.\n"
            "Отправьте /help для получения помощи."
        )
        return
    
    # Отправляем сообщение о начале обработки
    status_msg = await message.answer("🎵 *Начинаю загрузку...*\n\n⏳ Пожалуйста, подождите...", parse_mode="Markdown")
    
    try:
        # Скачиваем аудио
        audio_file, title = await download_audio(text, status_msg.message_id)
        
        if audio_file and audio_file.exists():
            # Проверяем размер файла (Telegram ограничение 50 MB)
            file_size = audio_file.stat().st_size / (1024 * 1024)
            
            if file_size > 50:
                await status_msg.edit_text(
                    f"❌ *Файл слишком большой!*\n\n"
                    f"Размер: {file_size:.1f} MB\n"
                    f"Лимит Telegram: 50 MB\n\n"
                    f"Попробуйте другое видео.",
                    parse_mode="Markdown"
                )
            else:
                # Редактируем сообщение о статусе
                await status_msg.edit_text(
                    f"✅ *Готово!*\n\n"
                    f"📝 Название: `{title[:50]}`\n"
                    f"📦 Размер: {file_size:.1f} MB\n\n"
                    f"📤 Отправляю файл...",
                    parse_mode="Markdown"
                )
                
                # Отправляем аудио файл
                audio_input = FSInputFile(str(audio_file))
                await message.answer_audio(
                    audio_input,
                    title=title[:200],  # Ограничиваем длину названия
                    performer="YouTube Music",
                    caption=f"🎵 *{title[:100]}*\n\n✨ Скачано с YouTube",
                    parse_mode="Markdown"
                )
                
                # Удаляем сообщение со статусом
                await status_msg.delete()
                
                # Очищаем старые файлы (опционально)
                clean_old_files(hours=24)
        else:
            await status_msg.edit_text(
                "❌ *Ошибка загрузки!*\n\n"
                "Не удалось скачать аудио. Проверьте:\n"
                "• Ссылку (должна быть корректной)\n"
                "• Доступность видео\n"
                "• Интернет-соединение\n\n"
                "Попробуйте другую ссылку.",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logging.error(f"Ошибка обработки: {e}")
        await status_msg.edit_text(
            f"❌ *Произошла ошибка!*\n\n"
            f"```\n{str(e)[:200]}\n```\n\n"
            f"Попробуйте позже или отправьте другую ссылку.",
            parse_mode="Markdown"
        )
    
    # Очищаем временные файлы
    try:
        user_folder = os.path.join(DOWNLOAD_PATH, str(status_msg.message_id))
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
    except Exception as e:
        logging.error(f"Ошибка очистки: {e}")

async def main():
    # Запускаем бота
    print("🤖 Бот запущен!")
    print("📌 Используйте @BotFather для получения токена")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
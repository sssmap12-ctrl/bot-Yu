import os
import asyncio
import logging
import shutil
from pathlib import Path
from datetime import datetime

import yt_dlp
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
# from dotenv import load_dotenv

# Load environment variables (TOKEN, WEBHOOK_URL optional)
# load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN environment variable not set")

# Vercel provides a temporary /tmp directory for file storage
TMPDIR = os.getenv("TMPDIR", "/tmp")
DOWNLOAD_PATH = os.path.join(TMPDIR, "downloads")
Path(DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)

# Initialize bot and dispatcher (no long‑polling, used via webhook)
bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_ydl_opts(output_path: str) -> dict:
    """yt‑dlp options for MP3 extraction with thumbnail embed."""
    return {
        "format": "bestaudio/best",
        "extractaudio": True,
        "audioformat": "mp3",
        "outtmpl": os.path.join(output_path, "%(title)s.%(ext)s"),
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"},
            {"key": "FFmpegMetadata"},
            {"key": "EmbedThumbnail"},
        ],
        "writethumbnail": True,
        "embedthumbnail": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
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
        parse_mode="Markdown",
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
        parse_mode="Markdown",
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    files = list(Path(DOWNLOAD_PATH).glob("*"))
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

def get_folder_size(folder: str) -> float:
    total = 0
    for path in Path(folder).iterdir():
        if path.is_file():
            total += path.stat().st_size
        elif path.is_dir():
            total += get_folder_size(str(path))
    return total / (1024 * 1024)

def clean_old_files(hours: int = 24) -> None:
    """Delete files older than *hours* in the download directory."""
    now = datetime.now()
    for file in Path(DOWNLOAD_PATH).glob("*"):
        if file.is_file():
            file_time = datetime.fromtimestamp(file.stat().st_mtime)
            if (now - file_time).total_seconds() > hours * 3600:
                try:
                    os.remove(file)
                    logging.info(f"Deleted old file: {file.name}")
                except Exception as e:
                    logging.error(f"Error deleting {file.name}: {e}")

async def download_audio(url: str, message_id: int) -> tuple[Path | None, str | None]:
    """Download audio to a unique sub‑folder and return (file_path, title)."""
    user_folder = os.path.join(DOWNLOAD_PATH, str(message_id))
    Path(user_folder).mkdir(parents=True, exist_ok=True)
    ydl_opts = get_ydl_opts(user_folder)
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            for file in Path(user_folder).glob("*.mp3"):
                return file, info.get('title', 'track')
        return None, None
    except Exception as e:
        logging.error(f"Download error: {e}")
        return None, None

@dp.message()
async def handle_youtube_url(message: Message):
    text = message.text.strip()
    if not ("youtube.com" in text.lower() or "youtu.be" in text.lower()):
        await message.answer(
            "❌ Пожалуйста, отправьте корректную ссылку на YouTube видео.\n"
            "Отправьте /help для получения помощи.",
            parse_mode="Markdown",
        )
        return
    status_msg = await message.answer("🎵 *Начинаю загрузку...*\n\n⏳ Пожалуйста, подождите...", parse_mode="Markdown")
    try:
        audio_file, title = await download_audio(text, status_msg.message_id)
        if audio_file and audio_file.exists():
            size_mb = audio_file.stat().st_size / (1024 * 1024)
            if size_mb > 50:
                await status_msg.edit_text(
                    f"❌ *Файл слишком большой!*\n\nРазмер: {size_mb:.1f} MB\nЛимит Telegram: 50 MB\n\nПопробуйте другое видео.",
                    parse_mode="Markdown",
                )
            else:
                await status_msg.edit_text(
                    f"✅ *Готово!*\n\n📝 Название: `{title[:50]}`\n📦 Размер: {size_mb:.1f} MB\n\n📤 Отправляю файл...",
                    parse_mode="Markdown",
                )
                audio_input = FSInputFile(str(audio_file))
                await message.answer_audio(
                    audio_input,
                    title=title[:200],
                    performer="YouTube Music",
                    caption=f"🎵 *{title[:100]}*\n\n✨ Скачано с YouTube",
                    parse_mode="Markdown",
                )
                await status_msg.delete()
                clean_old_files(hours=24)
        else:
            await status_msg.edit_text(
                "❌ *Ошибка загрузки!*\n\nНе удалось скачать аудио. Проверьте ссылку, доступность видео и соединение.",
                parse_mode="Markdown",
            )
    except Exception as e:
        logging.error(f"Processing error: {e}")
        await status_msg.edit_text(
            f"❌ *Произошла ошибка!*\n\n```\n{str(e)[:200]}\n```\n\nПопробуйте позже.",
            parse_mode="Markdown",
        )
    finally:
        try:
            user_folder = os.path.join(DOWNLOAD_PATH, str(status_msg.message_id))
            if os.path.exists(user_folder):
                shutil.rmtree(user_folder)
        except Exception as e:
            logging.error(f"Cleanup error: {e}")

# No polling entry point – Vercel will invoke via webhook
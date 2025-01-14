import os
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Get the bot token from the environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize the bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Set up Google Drive authentication
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def authenticate_gdrive():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Google Drive authentication is not set up properly.")
    return build("drive", "v3", credentials=creds)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! Send me a Google Drive folder link to start.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /stop is issued and stop the bot."""
    await update.message.reply_text("Bot is stopping...")
    context.application.stop()

async def handle_drive_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message.text
    if "drive.google.com" not in message or "folders" not in message:
        await update.message.reply_text("Invalid Google Drive link.")
        return

    await update.message.reply_text("Processing Google Drive link, please wait...")
    try:
        folder_id = extract_folder_id(message)
        if not folder_id:
            await update.message.reply_text("Invalid Google Drive link.")
            return

        drive_service = authenticate_gdrive()
        await download_files_from_drive(folder_id, update, drive_service)
    except Exception as e:
        logger.error(f"Error processing link: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")

def extract_folder_id(link: str) -> str:
    """Extract the folder ID from a Google Drive link."""
    if "folders/" in link:
        parts = link.split("folders/")
        folder_id = parts[1].split("?")[0]
        return folder_id
    return None

async def download_files_from_drive(folder_id: str, update: Update, drive_service) -> None:
    """List files in a Google Drive folder and download them."""
    query = f"'{folder_id}' in parents"
    results = drive_service.files().list(
        q=query,
        pageSize=10,
        fields="nextPageToken, files(id, name, mimeType)"
    ).execute()

    files = results.get('files', [])
    next_page_token = results.get('nextPageToken', None)

    while next_page_token or files:
        for file in files:
            await download_file(file['id'], file['name'], update)
        if next_page_token:
            results = drive_service.files().list(
                q=query,
                pageSize=10,
                pageToken=next_page_token,
                fields="nextPageToken, files(id, name, mimeType)"
            ).execute()
            files = results.get('files', [])
            next_page_token = results.get('nextPageToken', None)
        else:
            break

async def download_file(file_id: str, file_name: str, update: Update) -> None:
    """Download a file from Google Drive."""
    drive_service = authenticate_gdrive()
    request = drive_service.files().get_media(fileId=file_id)
    file_path = os.path.join("downloads", file_name)
    os.makedirs("downloads", exist_ok=True)

    with open(file_path, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            try:
                status, done = downloader.next_chunk(num_retries=3)
                progress = int(status.progress() * 100) if status else 0
                await update.message.reply_text(f"Downloading {file_name}: {progress}%")
            except Exception as e:
                logger.error(f"Error downloading file {file_name}: {e}", exc_info=True)
                await update.message.reply_text(f"Error downloading {file_name}: {e}")
                break

    if done:
        await update.message.reply_text(f"Download completed: {file_name}")
        await update.message.reply_document(open(file_path, 'rb'))
        os.remove(file_path)

def main() -> None:
    """Run the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_drive_link))
    application.run_polling()

if __name__ == "__main__":
    main()

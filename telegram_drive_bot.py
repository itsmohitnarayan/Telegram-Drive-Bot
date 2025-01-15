import os
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
from dotenv import load_dotenv
import mimetypes
import io
from googleapiclient.errors import HttpError
from telegram.error import NetworkError, RetryAfter

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

# Initialize Google Drive service
drive_service = authenticate_gdrive()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! Send me a Google Drive folder link to start.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /stop is issued and stop the bot."""
    await update.message.reply_text("Bot is stopping...")
    context.application.stop()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide help information about the bot commands."""
    help_text = (
        "/start - Start the bot\n"
        "/stop - Stop the bot\n"
        "/help - Show this help message\n"
        "Send a Google Drive folder link to download files."
    )
    await update.message.reply_text(help_text)

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
            mime_type = file.get("mimeType", "Unknown")
            file_name = file["name"]
            await update.message.reply_text(f"Found: {file_name} ({mime_type})")
            if mime_type.startswith("application/vnd.google-apps."):
                await export_google_file(file["id"], file_name, mime_type, update, drive_service)
            else:
                await download_file(file["id"], file_name, update)
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

async def export_google_file(file_id: str, file_name: str, mime_type: str, update: Update, drive_service) -> None:
    """Export Google Docs, Sheets, or Slides to a downloadable format."""
    export_mime_types = {
        "application/vnd.google-apps.document": "application/pdf",
        "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.google-apps.presentation": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    export_mime_type = export_mime_types.get(mime_type)
    if not export_mime_type:
        await update.message.reply_text(f"Cannot export file: {file_name} of type {mime_type}")
        return

    request = drive_service.files().export_media(fileId=file_id, mimeType=export_mime_type)
    file_path = os.path.join("downloads", file_name)
    os.makedirs("downloads", exist_ok=True)

    with open(file_path, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            try:
                status, done = downloader.next_chunk(num_retries=3)
                progress = int(status.progress() * 100) if status else 0
                await update.message.reply_text(f"Exporting {file_name}: {progress}%")
            except Exception as e:
                logger.error(f"Error exporting file {file_name}: {e}", exc_info=True)
                await update.message.reply_text(f"Error exporting {file_name}: {e}")
                break

    if done:
        await update.message.reply_text(f"Export completed: {file_name}")
        await update.message.reply_document(open(file_path, 'rb'))
        os.remove(file_path)

# Function to download a file from Google Drive
async def download_file(file_id, file_name, update):
    try:
        # Get the file metadata
        file = drive_service.files().get(fileId=file_id).execute()
        mime_type = file.get('mimeType')

        # Check if the file is a Google Docs Editors file
        if mime_type.startswith('application/vnd.google-apps.'):
            # Export the file to a downloadable format
            request = drive_service.files().export_media(fileId=file_id, mimeType='application/pdf')
            file_name += '.pdf'
        else:
            # Download the file directly
            request = drive_service.files().get_media(fileId=file_id)

        # Create a file handle
        fh = io.FileIO(file_name, 'wb')

        # Create a downloader object
        downloader = MediaIoBaseDownload(fh, request)

        # Download the file in chunks
        done = False
        while done is False:
            status, done = downloader.next_chunk(num_retries=3)
            logger.info("Download %d%%." % int(status.progress() * 100))

        # Close the file handle
        fh.close()

        # Send the file to the user
        await update.message.reply_document(document=open(file_name, 'rb'))

    except HttpError as error:
        logger.error(f"Error downloading file {file_name}: {error}")
        await update.message.reply_text(f"Error downloading file {file_name}: {error}")

# Define an error handler function
async def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if isinstance(context.error, NetworkError):
        await update.message.reply_text("Network error occurred. Please check your connection and try again.")
    elif isinstance(context.error, RetryAfter):
        await update.message.reply_text("Rate limit exceeded. Please try again later.")
    else:
        await update.message.reply_text("An error occurred. Please try again later.")

def main() -> None:
    """Run the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_drive_link))

    # Add the error handler
    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Bot stopped by user.")
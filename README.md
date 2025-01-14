# Telegram Drive Bot

This project is a Telegram bot that allows users to download files from Google Drive by sending a Google Drive folder link. The bot is built using the `python-telegram-bot` library and the Google Drive API.

## Features

- Start the bot with a `/start` command.
- Send a Google Drive folder link to the bot to download files from the folder.
- The bot will process the link, authenticate with Google Drive, and download the files.
- Stop the bot with a `/stop` command.

## Prerequisites

- Python 3.9+
- A Telegram bot token from [BotFather](https://core.telegram.org/bots#botfather)
- Google Drive API credentials

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/telegram-drive-bot.git
    cd telegram-drive-bot
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Create a [.env](http://_vscodecontentref_/1) file in the root directory and add your Telegram bot token:
    ```properties
    TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
    ```

5. Set up Google Drive API credentials:
    - Follow the instructions [here](https://developers.google.com/drive/api/v3/quickstart/python) to create [credentials.json](http://_vscodecontentref_/2).
    - Place the [credentials.json](http://_vscodecontentref_/3) file in the root directory of the project.

## Usage

1. Run the bot:
    ```sh
    python telegram_drive_bot.py
    ```

2. Start a chat with your bot on Telegram and send the `/start` command.

3. Send a Google Drive folder link to the bot. The bot will process the link and download the files from the folder.

4. Stop the bot with the `/stop` command.

## Code Overview

### [telegram_drive_bot.py](http://_vscodecontentref_/4)

This is the main script that contains the bot logic.

- **Imports**:
    - [os](http://_vscodecontentref_/5): For file operations.
    - [dotenv](http://_vscodecontentref_/6): To load environment variables from the [.env](http://_vscodecontentref_/7) file.
    - [telegram](http://_vscodecontentref_/8): For interacting with the Telegram API.
    - [telegram.ext](http://_vscodecontentref_/9): For handling commands and messages.
    - `googleapiclient.discovery`: For interacting with the Google Drive API.
    - `google_auth_oauthlib.flow`: For handling OAuth 2.0 authorization.
    - `google.auth.transport.requests`: For handling HTTP requests.

- **Functions**:
    - [start(update, context)](http://_vscodecontentref_/10): Sends a welcome message when the `/start` command is issued.
    - [stop(update, context)](http://_vscodecontentref_/11): Sends a message when the `/stop` command is issued and stops the bot.
    - [handle_drive_link(update, context)](http://_vscodecontentref_/12): Handles messages containing Google Drive folder links.
    - `download_files_from_drive(folder_id)`: Downloads files from a Google Drive folder.
    - [main()](http://_vscodecontentref_/13): Initializes and runs the bot.

- **Main Logic**:
    - Loads environment variables from the [.env](http://_vscodecontentref_/14) file.
    - Initializes the bot with the Telegram bot token.
    - Adds command handlers for `/start` and `/stop`.
    - Adds a message handler for processing Google Drive folder links.
    - Runs the bot using polling.

### [.env](http://_vscodecontentref_/15)

This file contains environment variables, including the Telegram bot token.

### [credentials.json](http://_vscodecontentref_/16)

This file contains Google Drive API credentials.

### [downloads](http://_vscodecontentref_/17)

This directory is where downloaded files are stored.

### [token.json](http://_vscodecontentref_/18)

This file stores the Google Drive API token.

## License

This project is licensed under the MIT License. See the [LICENSE](http://_vscodecontentref_/19) file for details.
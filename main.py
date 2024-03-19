import telebot
from PIL import Image
from io import BytesIO
import os
from webserver import keep_alive

telegram_token = os.environ['TELEGRAM_TOKEN']
bot = telebot.TeleBot(telegram_token)

# Dictionary to store user settings
user_settings = {}

# Handler for the /start command
@bot.message_handler(commands=['start'])
def handle_start_command(message):
    bot.reply_to(message, "Welcome to the Image Resizer Bot! Use the /resizeimage command to start resizing images.")

# Handler for the /help command
@bot.message_handler(commands=['help'])
def handle_help_command(message):
    help_message = "This bot can resize images. Here are the available commands:\n\n" \
                   "/start - Start the bot\n" \
                   "/help - Show help information\n" \
                   "/resizeimage - Resize an image"

    bot.reply_to(message, help_message)

# Handler for the /resizeimage command
@bot.message_handler(commands=['resizeimage'])
def handle_resize_image_command(message):
    chat_id = message.chat.id

    # Ask the user to upload an image
    bot.reply_to(message, "Please upload an image to resize.")

    # Store the command state for the user
    user_settings[chat_id] = {'command_state': 'upload_image'}

# Handler for receiving image messages
@bot.message_handler(content_types=['photo'])
def handle_image(message):
    chat_id = message.chat.id

    # Check if the user is in the command state for uploading an image
    if chat_id in user_settings and user_settings[chat_id]['command_state'] == 'upload_image':
        # Retrieve the photo ID
        photo_id = message.photo[-1].file_id

        # Download the photo using the photo ID
        file_info = bot.get_file(photo_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Load the downloaded photo into Pillow
        image = Image.open(BytesIO(downloaded_file))

        # Store the image in user settings
        user_settings[chat_id]['image'] = image

        # Get image details
        image_details = f"Image Details:\n\n" \
                        f"File Name: {file_info.file_path}\n" \
                        f"File Size: {file_info.file_size / (1024 * 1024):.2f} MB " \
                        f"({file_info.file_size / 1024:.2f} KB)\n" \
                        f"Image Width: {image.width}px\n" \
                        f"Image Height: {image.height}px\n"

        # Ask the user for the desired modification
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(telebot.types.InlineKeyboardButton('Modify File Size', callback_data='modify_file_size'))
        markup.row(telebot.types.InlineKeyboardButton('Modify File Dimensions', callback_data='modify_file_dimensions'))

        bot.reply_to(message, f"{image_details}\n"
                              f"Please choose the modification option:", reply_markup=markup)

        # Update the command state for the user
        user_settings[chat_id]['command_state'] = 'choose_modification'

# Handler for inline keyboard button callbacks
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id

    if chat_id in user_settings and user_settings[chat_id]['command_state'] == 'choose_modification':
        action = call.data

        if action == 'modify_file_size':
            # Ask the user to enter the desired file size
            bot.reply_to(call.message, "Please enter the desired file size in kilobytes (KB):")
            user_settings[chat_id]['command_state'] = 'enter_file_size'

        elif action == 'modify_file_dimensions':
            # Ask the user to enter the desired dimensions
            bot.reply_to(call.message, "Please enter the desired width and height in pixels (separated by a space):")
            user_settings[chat_id]['command_state'] = 'enter_dimensions'

# Handler for receiving text messages
@bot.message_handler(func=lambda message: message.content_type == 'text')
def handle_text(message):
    chat_id = message.chat.id

    # Check if the user has a command state
    if chat_id in user_settings:
        # Check the command state for the user
        if user_settings[chat_id]['command_state'] == 'enter_file_size':
            try:
                # Get the user's desired file size
                target_file_size = float(message.text.strip())

                # Retrieve the image from user settings
                image = user_settings[chat_id]['image']

                # Reduce the image quality to achieve the target file size
                quality = 80  # Initial quality level
                while True:
                    output = BytesIO()
                    image.save(output, format='JPEG', quality=quality)
                    image_size = output.tell()
                    if image_size / 1024 <= target_file_size:
                        break
                    quality -= 5  # Adjust the decrement value as needed

                # Save the resized image to a temporary file
                output.seek(0)
                with open('resized_image.jpg', 'wb') as f:
                    f.write(output.read())

                # Send the resized image back to the user
                with open('resized_image.jpg', 'rb') as f:
                    bot.send_photo(chat_id, f)

                # Clean up the temporary file
                os.remove('resized_image.jpg')

                # Get the details of the resized image
                resized_image_details = f"Resized Image Details:\n\n" \
                                        f"File Name: resized_image.jpg\n" \
                                        f"File Size: {target_file_size} KB\n" \
                                        f"Image Width: {image.width}px\n" \
                                        f"Image Height: {image.height}px\n"

                bot.send_message(chat_id, resized_image_details)

            except ValueError:
                bot.reply_to(message, "Invalid file size. Please enter a valid size in kilobytes (KB).")

            # Clear user settings
            del user_settings[chat_id]

        elif user_settings[chat_id]['command_state'] == 'enter_dimensions':
            try:
                # Get the user's desired dimensions
                dimensions = message.text.strip().split(' ')
                width = int(dimensions[0])
                height = int(dimensions[1])

                # Retrieve the image from user settings
                image = user_settings[chat_id]['image']

                # Resize the image to the desired dimensions
                image.thumbnail((width, height), Image.LANCZOS)

                # Save the resized image to a temporary file
                output_path = 'resized_image.jpg'
                image.save(output_path)

                # Send the resized image back to the user
                with open(output_path, 'rb') as file:
                    bot.send_photo(chat_id, file)

                # Clean up the temporary file
                os.remove(output_path)

                # Get the details of the resized image
                resized_image_details = f"Resized Image Details:\n\n" \
                                        f"File Name: resized_image.jpg\n" \
                                        f"File Size: {file_info.file_size / 1024:.2f} KB\n" \
                                        f"Image Width: {image.width}px\n" \
                                        f"Image Height: {image.height}px\n"

                bot.send_message(chat_id, resized_image_details)

            except (IndexError, ValueError):
                bot.reply_to(message, "Invalid dimensions. Please enter valid width and height values.")

            # Clear user settings
            del user_settings[chat_id]

        else:
            bot.reply_to(message, "Invalid command or input.")

    else:
        bot.reply_to(message, "Please start with the /resizeimage command to resize an image.")

# Handler for unrecognized commands or messages
@bot.message_handler(func=lambda message: True)
def handle_unrecognized(message):
    bot.reply_to(message, "Unrecognized command or message. Use /help to see the available commands.")

# Start the bot
keep_alive()
bot.polling(none_stop=True, timeout=123)


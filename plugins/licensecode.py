import base64
import aiohttp
from pyrogram import Client, filters
from info import ADMINS, LOG_CHANNEL
from database.users_chats_db import db
import asyncio
import binascii

ACCESS_KEY = "PZUNTLGIZFE67MR0I0H0"

@Client.on_message(filters.command("licensegen") & filters.user(ADMINS))
async def generate(client, message):
    num_codes = 1  # default value
    duration = 28  # default duration

    # Extract number of codes and duration if provided
    command_args = message.command[1:]
    if len(command_args) > 0:
        try:
            num_codes = int(command_args[0])
            if len(command_args) > 1:
                duration = int(command_args[1])
                if duration < 1 or duration > 365:
                    raise ValueError("Invalid duration. Duration should be between 1 to 365 days.")
            if num_codes <= 0:
                raise ValueError("Number of codes should be greater than 0.")
        except ValueError as e:
            await message.reply_text(str(e))
            return

    # Convert duration to base64 and remove '=' padding
    encoded_duration = base64.b64encode(str(duration).zfill(3).encode()).decode('utf-8').rstrip('=')

    codes_generated = []
    for _ in range(num_codes):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://licensegen.onrender.com/?access_key={ACCESS_KEY}&action=generate&days=30") as resp:
                if resp.status == 200:
                    json_response = await resp.json()
                    license_code = f"{json_response.get('license_code')[:10]}{encoded_duration}{json_response.get('license_code')[10:]}"
                    codes_generated.append(license_code)
                else:
                    await message.reply_text("Error generating license code. Please try again.")
                    return
                
    codes_str = "\n".join(f"`{code}`" for code in codes_generated)
    await message.reply_text(f"<b>Redeem codes:</b>\n\n{codes_str}")

@Client.on_message(filters.regex(r"^([A-Z0-9]{10})([A-Za-z0-9+/]{4})([A-Z0-9]{10})$") & filters.private)
async def validate_code(client, message):
    # Access the matched groups directly
    first_part_code = message.matches[0][1]
    encoded_duration = message.matches[0][2]
    second_part_code = message.matches[0][3]

    # Add back padding to encoded duration for proper decoding
    padding_needed = 4 - (len(encoded_duration) % 4)
    encoded_duration += '=' * padding_needed

    # Decode the base64 duration
    try:
        duration_str = base64.b64decode(encoded_duration.encode()).decode('utf-8')
        duration = int(duration_str)
    except (ValueError, binascii.Error):
        await message.reply_text("Invalid format. Unable to determine subscription duration.")
        return

    full_code = first_part_code + second_part_code  # Actual code without the duration part.

    user_id = message.from_user.id
    if await db.is_premium_status(user_id) is True:
        await message.reply_text("You can't redeem this code because you are already a premium user")
        return

    m = await message.reply_text(f"Please wait, checking your redeem code....")
    await asyncio.sleep(3)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://licensegen.onrender.com/?access_key={ACCESS_KEY}&action=validate&code={full_code}") as resp:
            if resp.status == 404:
                await m.edit("Invalid code brrrrrah!...")
            if resp.status == 403:
                respo = await resp.json()
                if respo.get('message') == "This code does not belong to the provided access key":
                    await m.edit("This code does not belong to the provided access key.")
                    return
                if respo.get('message') == "This code is already in use":
                    await m.edit("This redeem code's already used.")
                    return
                if respo.get('message') == "The code has expired":
                    await m.edit("The redeem code has expired.")
                    return
            if resp.status == 200:
                json_response = await resp.json()
                if json_response.get('message') == "Code validated successfully":
                    s = await m.edit("Redeem code validated successfully.")
                    await db.add_user_as_premium(user_id, duration)
                    await asyncio.sleep(5)
                    a = await s.edit(f"Activating your subscription...")
                    await asyncio.sleep(5)
                    await a.edit(f"Your subscription has been enabled successfully for {duration} days.")
                    # send message to log channel
                    await client.send_message(LOG_CHANNEL, f"#redeem\n<code>{full_code}</code>\n{message.from_user.mention} <code>{message.from_user.id}</code> successfully redeemed a code.")
                else:
                    await m.edit(json_response.get('message'))


@Client.on_message(filters.regex(r"^([A-Z0-9]{20})$") & filters.private)
async def ras_validate_code(client, message):
    s = await message.reply_text("Please wait, checking your redeem code....")
    await asyncio.sleep(5)
    await s.edit("Hmm, there's an issue with the redeem code. Double-check it?")

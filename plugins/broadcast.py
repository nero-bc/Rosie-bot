from pyrogram import Client, filters
import datetime
import time
from database.users_chats_db import db
from info import ADMINS
from utils import broadcast_messages
import asyncio

@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def verupikkals(bot, message):
    users = await db.get_all_users()
    b_msg = message.reply_to_message
    sts = await message.reply_text(
        text='Broadcasting your messages...'
    )   

    start_time = time.perf_counter()
    total_users = await db.total_users_count()
    done = blocked = deleted = failed = success = 0

    sem = asyncio.Semaphore(25) # limit the number of concurrent tasks to 100

    async def run_task(user):
        async with sem:
            return await broadcast_func(user, b_msg)

    tasks = (run_task(user) for user in users)

    for future in asyncio.as_completed(tasks):
        success1, blocked1, deleted1, failed1, done1 = await future
        done += done1
        blocked += blocked1
        deleted += deleted1
        failed += failed1
        success += success1

        if done % 50 == 0:
            await sts.edit(f"Broadcast in progress:\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nBlocked: {blocked}\nDeleted: {deleted}")    

    time_taken = datetime.timedelta(seconds=int(time.perf_counter()-start_time))
    await sts.edit(f"Broadcast Completed:\nCompleted in {time_taken} seconds.\n\nTotal Users {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nBlocked: {blocked}\nDeleted: {deleted}")

async def broadcast_func(user, b_msg):
    success, blocked, deleted, failed, done = 0, 0, 0, 0, 0
    pti, sh = await broadcast_messages(int(user['id']), b_msg)
    status_dict = {"Blocked": (1, 0, 0, 0), "Deleted": (0, 1, 0, 0), "Error": (0, 0, 1, 0)}
    if pti:
        success = 1
    elif pti == False:
        success, blocked, deleted, failed = status_dict.get(sh, (0, 0, 0, 0))
    done = 1
    return success, blocked, deleted, failed, done
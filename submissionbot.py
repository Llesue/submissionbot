import telebot
import os
import sqlite3
import subprocess
import time

dir = "/path/to/directory/submissionbot"
bot_token = ""
admin_id = ""
channel_id = ""

bot = telebot.TeleBot(bot_token, parse_mode=None, num_threads=10)
os.makedirs(dir, exist_ok=True)

db_path = f"{dir}/submission.db"
if not os.path.exists(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE files ( \
            id INTEGER PRIMARY KEY, \
            user_id INTEGER, \
            file_id TEXT, \
            file_name, \
            convert_fid TEXT, \
            caption TEXT, \
            cost_time INTEGER, \
            filesize INTEGER, \
            thumbnail_fid TEXT, \
            msg_id INTEGER, \
            amsg_id INTEGER, \
            timestamp INTEGER \
        )')
        cursor.execute('CREATE TABLE users ( \
            id INTEGER PRIMARY KEY, \
            user_id INTEGER, \
            fullname TEXT, \
            username TEXT, \
            submission INETEGER, \
            is_banned INTEGER, \
            timestamp INTEGER \
        )')
        conn.commit()

def adduser(message):
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    fullname = f"{first_name} {last_name}" if last_name else first_name
    username = message.from_user.username
    user_id = message.from_user.id
    timestamp = message.date
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT count(user_id) FROM users WHERE user_id=?',(user_id,))
        record = cursor.fetchone()[0]
        user_exists = True if record > 0 else False

    if not user_exists:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users \
                (user_id, fullname, username, timestamp) \
                VALUES (?, ?, ?, ?)',(user_id, fullname, username, timestamp))
        conn.commit()

# 自定义更新数据库
def dbUpdate(query, params=None):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params) if params else cursor.execute(query)
        conn.commit()

# 自定义获取数据库信息
def dbGet(query, fetch=1):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone() if fetch == 1 else cursor.fetchall()
        return result

@bot.message_handler(commands=["start"])
def handleStart(message):
    is_private = True if not message.chat.title else False
    user_id = message.from_user.id
    if is_private:
        adduser(message)
        bot.send_message(user_id,"🤖  我是 «轻口味时间» 频道 (@lightrekt) 的投稿机器人，您想投稿吗？请把您的视频直接转发给我吧。\n\n🤖 I'm submission bot of @lightrekt. Do you want send videos to the channel? Submit your video to me.")

@bot.message_handler(commands=["ad"])
def handleStart(message):
    user_id = message.from_user.id
    try:
        inputs = message.text.split()[1:]
        inputs = inputs[0]
    except:
        pass
    caption = inputs if inputs else "大家来投稿！"
    if int(user_id) == int(admin_id):
        markup = telebot.types.InlineKeyboardMarkup()
        btn_sub = telebot.types.InlineKeyboardButton("投稿 SUBMISSION", url="https://t.me/tolightrektbot")
        markup.add(btn_sub)
        with open(f"{dir}/submissionBot.jpg", "rb") as p:
            bot.send_photo(channel_id, p, caption=caption, reply_markup=markup)
        bot.send_message(admin_id,"成功发送了广告")

@bot.message_handler(commands=["unban"])
def handleStart(message):
    user_id = message.from_user.id
    if int(user_id) == int(admin_id):
        try:
            inputs = message.text.split()[1:]
            inputs = inputs[0]
        except:
            inputs = None
        if inputs:
            try:
                user_id, fullname, username = dbGet(f"SELECT user_id, fullname, username FROM users WHERE user_id={inputs}")
            except:
                fullname = None
            if fullname:
                query = "UPDATE users SET is_banned=? WHERE user_id=?"
                params = (None, inputs)
                dbUpdate(query,params)
                linked_name = f"[{fullname}](https://t.me/{username})" if username else f"[{fullname}](tg://user?id={inputs})"
                bot.send_message(admin_id, f"{linked_name} 已被解封",parse_mode="MARKDOWN",disable_web_page_preview=True)
                bot.send_message(user_id, "您又被允许投稿了呢\nYou're Unbanned. Jeez.")
            else:
                bot.send_message(user_id, f"没找到该用户，请输入有效的 chat_id 解封")

@bot.message_handler(commands=["ranking"])
def handleStart(message):
    is_private = True if not message.chat.title else False
    send_user_id = message.from_user.id
    msg_id = message.message_id
    if is_private:
        records = dbGet("SELECT fullname, user_id, username, submission FROM users ORDER BY submission DESC LIMIT 10",0)
        num = 0
        users = []
        for record in records:
            fullname, user_id, username, submission = record
            num = num + 1

            linked_name = f"[{fullname}](https://t.me/{username})" if username else f"[{fullname}](tg://user?id={user_id})"
            users.append(f"{num}. {linked_name} _{submission or 0}_")
            list = "\n".join(users)

        text = f"*投稿排行 Top 10 Submissioners*\n\n{list}"
        bot.send_message(send_user_id,text,parse_mode="MARKDOWN",disable_web_page_preview=True)

# receive contents
@bot.message_handler(content_types=["video", "text"])
def handle_video(message):
    is_private = True if not message.chat.title else False
    msg_id = message.message_id
    timestamp = message.date
    
    # 获取带链接用户名称
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username
    user_id = message.from_user.id

    full_name = f"{first_name} {last_name}" if last_name else f"{first_name}"
    linked_name = f"[{full_name}](https://t.me/{username})" if username else f"[{full_name}](tg://user?id={user_id})"

    if is_private:
        adduser(message)
        is_banned, _ = dbGet(f"SELECT is_banned, timestamp FROM users WHERE user_id={user_id}")
        banned_user = True if is_banned else False
        if not banned_user:
            if message.content_type == "video":
                video_fid = message.video.file_id
                caption = message.caption
                filesize = int(message.video.file_size)
                filename = message.video.file_name or f"{message.video.file_unique_id}.mp4"
                thumbnail_fid = message.video.thumbnail.file_id

                bot.delete_message(user_id, msg_id)
                sendvideo_id = bot.send_video(user_id,video_fid,caption=caption).message_id

                markup = telebot.types.InlineKeyboardMarkup()
                btn_submit = telebot.types.InlineKeyboardButton("提交 Submit", callback_data=f"submit_ok_{sendvideo_id}")
                btn_cancel = telebot.types.InlineKeyboardButton("取消 Cancel", callback_data=f"submit_cancel_{sendvideo_id}")
                markup.add(btn_submit, btn_cancel)

                # deal video
                query = "INSERT INTO files (user_id, file_id, thumbnail_fid, caption, filesize, file_name, msg_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                params = (user_id, video_fid, thumbnail_fid, caption, filesize, filename, sendvideo_id, timestamp)
                dbUpdate(query,params)

                text = "✏️ 请输入视频内容描述后点击提交。\n✏️ Write down the description of the video and Submit."
                bot.send_message(user_id,text,reply_to_message_id=sendvideo_id,reply_markup=markup)
            elif message.content_type == "text":
                caption = message.text
                db_capture = dbGet(f"SELECT convert_fid FROM files WHERE user_id={user_id} ORDER BY timestamp DESC LIMIT 1")
                cap_locked = db_capture[0] if db_capture else True
                # print(cap_locked)
                if not cap_locked:
                    pid, vidmsg_id = dbGet(f"SELECT id, msg_id FROM files WHERE user_id={user_id} ORDER BY timestamp DESC LIMIT 1")
                    query = "UPDATE files SET caption=?, timestamp=? WHERE id=?"
                    params = (caption, timestamp, pid)
                    dbUpdate(query,params)

                    try:
                        bot.edit_message_caption(caption, user_id, vidmsg_id)
                        bot.delete_message(user_id, msg_id)
                    except:
                        pass
                else:
                    text = f"{linked_name}: {caption}"
                    bot.send_message(admin_id,text,parse_mode="MARKDOWN",disable_web_page_preview=True)
                    
                # 管理员编辑视频标题流程
                if int(user_id) == int(admin_id):
                    try:
                        id, vidmsg_id, ovidmsg_id, sender_id = dbGet(f"SELECT id, amsg_id, msg_id, user_id FROM files WHERE convert_fid='789' ORDER BY timestamp DESC LIMIT 1") 
                    except:
                        vidmsg_id = None

                    if vidmsg_id:
                        query = "UPDATE files SET caption=?, timestamp=? WHERE id=?"
                        params = (caption, timestamp, id)
                        dbUpdate(query,params)

                        try:
                            bot.edit_message_caption(caption, user_id, vidmsg_id)
                            bot.delete_message(user_id, msg_id)
                            bot.edit_message_caption(caption, sender_id, ovidmsg_id)
                        except:
                            pass
                    # 管理员回复视频流程
                    is_reply = True if message.reply_to_message else False
                    if is_reply:
                        is_video = True if message.reply_to_message else False
                        if is_video:
                            text = message.text
                            reply_caption = message.reply_to_message.caption
                            try:
                                target_uid,msg_id = dbGet(f"SELECT user_id, msg_id FROM files WHERE caption='{reply_caption}'")
                            except:
                                target_uid = None
                            try:
                                bot.send_message(target_uid,text,reply_to_message_id=msg_id) if target_uid else None
                                text = "消息发送成功" if target_uid else "消息发送失败"
                                del_later = bot.send_message(admin_id,text).message_id
                                time.sleep(3)
                                bot.delete_message(admin_id,del_later)
                            except:
                                del_later = bot.send_message(admin_id,"消息发送失败").message_id
                                time.sleep(3)
                                bot.delete_message(admin_id,del_later)
            else:
                bot.send_message(user_id,"我们频道仅接受视频投稿哦")
        else:
            bot.send_message(user_id, "💩 您已被禁止投稿。\n💩 You're been banned.")

# 视频压缩并发送流程
def compress_and_send(id):
    file_size, file_name, caption, file_id, thumb_fid, user_id, msg_id = dbGet(f"SELECT filesize, file_name, caption, file_id, thumbnail_fid, user_id, msg_id FROM files WHERE id={id}")
    caption = caption or ""
    caption = caption + "\n#投稿 💌 via @tolightrektbot"
    status = False
    if file_size < 20*1024*1024+1:
        file_info = bot.get_file(file_id)
        download_file = bot.download_file(file_info.file_path)
        os.makedirs(f"{dir}/download/videos", exist_ok=True)
        path = f"{dir}/download/{file_info.file_path}"
        with open(path, "wb") as f:
            f.write(download_file)
        new_path = f"{dir}/download/videos/{id}_{file_name}"
        os.rename(path, new_path)
        
        output_dir = f"{dir}/download/converted"
        os.makedirs(output_dir, exist_ok=True)
        output_file = f"{output_dir}/submission_{id}_{file_name}"
        print(path)
        print(new_path)
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", new_path,
            "-i", f"{dir}/watermark.png",
            "-filter_complex",
                "[0]scale=w='if(lt(iw,ih),480,-2):h=if(gte(iw,ih),480,-2)'[vid];"
                "[1]scale=w='if(gt(iw,ih),iw*35/100,iw*40/100)':h=-1[wm];"
                "[vid][wm]overlay=x=w/4:y=w/4:enable='between(t,5,10)+between(t,25,60)+between(t,90,600)':format=auto,format=yuv420p",
            "-c:a", "aac",
            "-c:v", "libx264",
            "-strict", "-2",
            "-crf", "26",
            "-y", output_file
        ]
        try:
            subprocess.run(ffmpeg_cmd)
        except:
            pass

        # 查看文件是否超过50MB
        converted_size = round(os.path.getsize(output_file) / 1024 / 1024, 2)
        sendto_id = channel_id if converted_size < 10 else admin_id

        if converted_size < 50:
            with open(output_file, "rb") as v:
                new_fid = bot.send_video(sendto_id, v, caption=caption, thumb=thumb_fid, thumbnail=thumb_fid).video.file_id
        else:
            new_fid = bot.send_video(sendto_id, file_id, caption=caption).video.file_id

        query = "UPDATE files SET convert_fid=? WHERE id=?"
        params = (new_fid,id)
        dbUpdate(query,params)
        status = True
    else:
        new_fid = bot.send_video(admin_id, file_id, caption=caption).video.file_id
        query = "UPDATE files SET convert_fid=? WHERE id=?"
        params = (new_fid,id)
        dbUpdate(query,params)
        status = True

    query = "UPDATE users SET submission=COALESCE(submission, 0) +1 WHERE user_id=?"
    params = (user_id,)
    dbUpdate(query,params)

    return status, user_id, msg_id

# Admin 接收投稿流程
def sendto_admin(id,vid_fid, caption):
    markup = telebot.types.InlineKeyboardMarkup()
    btn_accept = telebot.types.InlineKeyboardButton("接受稿件", callback_data=f"admin_accept_{id}")
    btn_reject = telebot.types.InlineKeyboardButton("拒绝稿件", callback_data=f"admin_reject_{id}")
    btn_edit = telebot.types.InlineKeyboardButton("编辑描述", callback_data=f"admin_edit_{id}")
    btn_ban = telebot.types.InlineKeyboardButton("封禁用户", callback_data=f"admin_ban_{id}")
    markup.add(btn_edit, btn_accept)
    markup.add(btn_reject, btn_ban)
    send_id = bot.send_video(admin_id, vid_fid, caption=caption).message_id

    query = "UPDATE files SET amsg_id=? WHERE id=?"
    params = (send_id,id)
    dbUpdate(query,params)

    user_id,_ = dbGet(f"SELECT user_id, timestamp FROM files WHERE id={id}")
    fullname, username = dbGet(f"SELECT fullname, username FROM users WHERE user_id={user_id}")
    linked_name = f"[{fullname}](https://t.me/{username})" if username else f"[{fullname}](tg://user?id={user_id})"
    bot.send_message(admin_id, f"{linked_name} 的投稿，请对该投稿进行如下选择", reply_to_message_id=send_id, reply_markup=markup, disable_web_page_preview=True, parse_mode="MARKDOWN")

# 按钮接收回应
@bot.callback_query_handler(func=lambda call: call.data)
def callData(call):
    data = call.data
    if data.startswith("submit"):
        command = data.split("_")[1]
        vidmsg_id = int(data.split("_")[2])
        id, vid_fid, caption = dbGet(f"SELECT id, file_id, caption FROM files WHERE msg_id={vidmsg_id} AND user_id={call.message.chat.id} ORDER BY timestamp DESC LIMIT 1")
        if command == "ok":
            # convert_fid 插入随机信息，以锁定 caption
            query ="UPDATE files SET convert_fid=? WHERE id=?"
            params = ("999", id)
            dbUpdate(query,params)

            sendto_admin(id,vid_fid,caption)
            bot.edit_message_text("视频已提交 Submitted", call.message.chat.id, call.message.message_id)
        else:
            # convert_fid 插入随机信息，以锁定 caption
            query ="UPDATE files SET convert_fid=? WHERE id=?"
            params = ("666", id)
            dbUpdate(query,params)
            bot.edit_message_text("视频已取消提交 Submit Canceled", call.message.chat.id, call.message.message_id)
    if data.startswith("admin"):
        command = data.split("_")[1]
        id = data.split("_")[2]
        if command == "accept":
            bot.edit_message_text("稿件正在处理中……", call.message.chat.id, call.message.message_id)
            status, user_id, msg_id = compress_and_send(id)
            if status: 
                try:
                    bot.edit_message_text("投稿已接受", call.message.chat.id, call.message.message_id)
                    bot.send_message(user_id,"您的投稿已被接受\nYour submission accepted!",reply_to_message_id=msg_id)
                except:
                    pass
            else:
                bot.edit_message_text("投稿处理出错了", call.message.chat.id, call.message.message_id)
        # 投稿拒绝流程
        elif command == "reject":
            user_id, msg_id = dbGet(f"SELECT user_id, msg_id FROM files WHERE id={id}")
            bot.edit_message_text("投稿已拒绝。", call.message.chat.id, call.message.message_id)
            try:
                bot.send_message(user_id,"该投稿被拒绝了 This content been rejected",reply_to_message_id=msg_id)
            except:
                bot.send_message(user_id,"您的某个投稿被拒绝了 Your content been rejected")
        # 修改视频描述流程
        elif command == "edit":
            markup = telebot.types.InlineKeyboardMarkup()
            btn_dealok = telebot.types.InlineKeyboardButton("确定",callback_data=f"deal_ok_{id}")
            btn_dealcancel = telebot.types.InlineKeyboardButton("取消",callback_data=f"deal_cancel_{id}")
            markup.add(btn_dealok,btn_dealcancel)
            bot.edit_message_text("请输入新描述后确定：", call.message.chat.id, call.message.message_id,reply_markup=markup)
            # 用数据库做标记，以便接收新描述
            query = "UPDATE files SET convert_fid=? WHERE id=?"
            params = ("789",id)
            dbUpdate(query,params)
        # 用户封禁流程
        elif command == "ban":
            user_id, msg_id = dbGet(f"SELECT user_id, msg_id FROM files WHERE id={id}")
            query = "UPDATE users SET is_banned=? WHERE user_id=?"
            params = (1,user_id)
            dbUpdate(query,params)
            bot.edit_message_text("该用户已被封禁", call.message.chat.id, call.message.message_id)

    if data.startswith("deal"):
        command = data.split("_")[1]
        id = data.split("_")[2]
        if command == "ok":
            query = "UPDATE files SET convert_fid=? WHERE id=?"
            params = ("999",id)
            dbUpdate(query,params)
            bot.edit_message_text("修改完成，正在处理稿件中……", call.message.chat.id, call.message.message_id)

            status, user_id, msg_id = compress_and_send(id)
            if status: 
                try:
                    bot.edit_message_text("投稿已接受。", call.message.chat.id, call.message.message_id)
                    bot.send_message(user_id,"您的投稿已被接受\nYour submission accepted!",reply_to_message_id=msg_id)
                except:
                    pass
            else:
                bot.edit_message_text("投稿处理出错了。", call.message.chat.id, call.message.message_id)
        if command == "cancel":
            query = "UPDATE files SET convert_fid=? WHERE id=?"
            params = ("999",id)
            dbUpdate(query,params)
            user_id, msg_id = dbGet(f"SELECT user_id, msg_id FROM files WHERE id={id}")
            bot.edit_message_text("投稿已拒绝。", call.message.chat.id, call.message.message_id)
            try:
                bot.send_message(user_id,"该投稿被拒绝了 This content been rejected",reply_to_message_id=msg_id)
            except:
                bot.send_message(user_id,"您的某个投稿被拒绝了 Your content been rejected")

bot.infinity_polling(timeout=10, long_polling_timeout=5)

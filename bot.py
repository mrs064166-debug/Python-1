import json
import logging
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================= কনফিগারেশন =================
BOT_TOKEN = "8222516603:AAGv9fph1jkZJKnzoSCvZddbZ7sUoDo5yzg"
ADMIN_IDS = [6985943036]

# ফোর্স সাবস্ক্রাইব চ্যানেল (৩-৪টি চ্যানেল বসিয়ে বটকে সব চ্যানেলের Admin করতে হবে)
FORCE_CHANNELS = [
    {"name": "Join Channel", "chat_id": "@your_channel_1", "url": "https://t.me/your_channel_1"},
    {"name": "Join Channel", "chat_id": "@your_channel_2", "url": "https://t.me/your_channel_2"},
    {"name": "Join Channel", "chat_id": "@your_channel_3", "url": "https://t.me/your_channel_3"},
]

DB_FILE = "bot_data.json"
REFERRAL_REWARD = 10

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# ================= ডেটাবেস হেল্পার =================
def load_db():
    if not os.path.exists(DB_FILE):
        data = {
            "users": {},
            "files": {
                "Ai Image Generator": {
                    "type": "text",
                    "content": "Ai Image Generator - New Update Coming Soon....",
                    "caption": "Ai Image Generator - New Update Coming Soon....",
                },
                "Info Python File": {
                    "type": "text",
                    "content": "Info Python File - New Update Coming Soon....",
                    "caption": "Info Python File - New Update Coming Soon....",
                },
                "Camera Hacking": {
                    "type": "text",
                    "content": "Camera Hacking - New Update Coming Soon....",
                    "caption": "Camera Hacking - New Update Coming Soon....",
                },
                "Screen Capture File": {
                    "type": "text",
                    "content": "Screen Capture File - New Update Coming Soon....",
                    "caption": "Screen Capture File - New Update Coming Soon....",
                },
            },
        }
        save_db(data)
        return data
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_user(db, user_id, first_name="User", ref_by=None):
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "name": first_name,
            "balance": 0,
            "referrals": 0,
            "banned": False,
            "ref_by": ref_by,
        }
        if ref_by and str(ref_by) in db["users"] and str(ref_by) != uid:
            db["users"][str(ref_by)]["balance"] += REFERRAL_REWARD
            db["users"][str(ref_by)]["referrals"] += 1
        save_db(db)
    else:
        db["users"][uid]["name"] = first_name
        save_db(db)
    return db["users"][uid]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ================= ফোর্স সাবস্ক্রাইব চেক =================
async def check_force_sub(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for ch in FORCE_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logger.warning(f"Force sub check error for {ch['chat_id']}: {e}")
            return False
    return True


def force_sub_markup() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(FORCE_CHANNELS), 2):
        row = [InlineKeyboardButton(f"↗️ {FORCE_CHANNELS[i]['name']}", url=FORCE_CHANNELS[i]["url"])]
        if i + 1 < len(FORCE_CHANNELS):
            row.append(InlineKeyboardButton(f"↗️ {FORCE_CHANNELS[i+1]['name']}", url=FORCE_CHANNELS[i+1]["url"]))
        rows.append(row)
    rows.append([InlineKeyboardButton("🟢 JOINED", callback_data="check_joined")])
    return InlineKeyboardMarkup(rows)


# ================= কীবোর্ড লেআউট (স্ক্রিনশটের মতো ৬ বাটন) =================
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("💎 GET CODE 💎")],
        [KeyboardButton("👥 Referral"), KeyboardButton("💰 Balance")],
        [KeyboardButton("📖 How To Use")],
        [KeyboardButton("🆔 Chat Id"), KeyboardButton("👤 My Account")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def code_categories_keyboard(db) -> ReplyKeyboardMarkup:
    categories = list(db["files"].keys())
    rows = []
    for i in range(0, len(categories), 2):
        row = [KeyboardButton(categories[i])]
        if i + 1 < len(categories):
            row.append(KeyboardButton(categories[i + 1]))
        rows.append(row)
    rows.append([KeyboardButton("🔙 Back")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("📤 Upload File"), KeyboardButton("📢 Broadcast")],
        [KeyboardButton("👥 User List"), KeyboardButton("🚫 Ban/Unban User")],
        [KeyboardButton("💸 Withdraw Requests"), KeyboardButton("🔙 Main Menu")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ================= কমান্ড ও মেসেজ হ্যান্ডলার =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = load_db()

    ref_by = None
    if context.args and context.args[0].startswith("ref_"):
        ref_by = context.args[0].replace("ref_", "")

    u_data = get_user(db, user.id, user.first_name, ref_by=ref_by)
    if u_data.get("banned"):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    if FORCE_CHANNELS and not await check_force_sub(user.id, context):
        await update.message.reply_text(
            f"👋 HEY **{user.first_name}**\n\n"
            "➡️ After Joining All Channels,\n"
            "Click On 🟢 **JOINED**",
            reply_markup=force_sub_markup(),
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        f"Welcome To **{user.first_name}**",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    db = load_db()
    await update.message.reply_text(
        f"🛠️ **Admin Control Panel**\nTotal Users: **{len(db['users'])}**",
        reply_markup=admin_panel_keyboard(),
        parse_mode="Markdown",
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    db = load_db()
    u_data = get_user(db, user.id, user.first_name)

    if u_data.get("banned"):
        await query.answer("🚫 You are banned!", show_alert=True)
        return

    if data == "check_joined":
        if await check_force_sub(user.id, context):
            await query.message.delete()
            await context.bot.send_message(
                chat_id=user.id,
                text="✅ Verified! Welcome to Main Menu:",
                reply_markup=main_menu_keyboard(),
            )
        else:
            await query.answer("❌ Join all channels first!", show_alert=True)

    elif data.startswith("req_file|"):
        cat_name = data.split("|", 1)[1]
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"conf_file|{cat_name}"),
                InlineKeyboardButton("🔙 Back", callback_data="cancel_file"),
            ]
        ])
        await query.message.reply_text(
            "⚡ Please Click On Confirm",
            reply_markup=markup,
        )
        await query.answer()

    elif data.startswith("conf_file|"):
        cat_name = data.split("|", 1)[1]
        file_info = db["files"].get(cat_name)
        if not file_info:
            await query.message.reply_text(f"{cat_name}\nNew Update Coming Soon....")
            await query.answer()
            return

        ftype = file_info.get("type", "text")
        cap = file_info.get("caption") or cat_name

        if ftype == "document":
            await query.message.reply_document(document=file_info["file_id"], caption=cap)
        elif ftype == "photo":
            await query.message.reply_photo(photo=file_info["file_id"], caption=cap)
        elif ftype == "video":
            await query.message.reply_video(video=file_info["file_id"], caption=cap)
        elif ftype == "voice":
            await query.message.reply_voice(voice=file_info["file_id"], caption=cap)
        else:
            await query.message.reply_text(file_info.get("content") or cap)
        await query.answer("✅ Sent!")

    elif data == "cancel_file":
        await query.message.delete()
        await query.answer("Cancelled")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user = update.effective_user
    text = update.message.text or ""
    db = load_db()
    u_data = get_user(db, user.id, user.first_name)

    if u_data.get("banned"):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    if FORCE_CHANNELS and not await check_force_sub(user.id, context):
        await update.message.reply_text(
            "⚠️ Join all channels first and click JOINED:",
            reply_markup=force_sub_markup(),
        )
        return

    # ---------- অ্যাডমিন স্টেট হ্যান্ডলার ----------
    admin_state = context.user_data.get("admin_state")
    if is_admin(user.id) and admin_state:
        if text in ["🔙 Main Menu", "🔙 Back", "/cancel"]:
            context.user_data.clear()
            await update.message.reply_text("Main Menu:", reply_markup=main_menu_keyboard())
            return

        if admin_state == "upload_cat":
            context.user_data["upload_category"] = text.strip()
            context.user_data["admin_state"] = "upload_media"
            await update.message.reply_text(
                f"Category: **{text.strip()}**\nNow send Document, Photo, Video, Voice or Text:",
                parse_mode="Markdown",
            )
            return

        elif admin_state == "upload_media":
            cat = context.user_data.get("upload_category")
            if update.message.document:
                ftype, fid = "document", update.message.document.file_id
            elif update.message.photo:
                ftype, fid = "photo", update.message.photo[-1].file_id
            elif update.message.video:
                ftype, fid = "video", update.message.video.file_id
            elif update.message.voice:
                ftype, fid = "voice", update.message.voice.file_id
            elif update.message.text:
                db["files"][cat] = {
                    "type": "text",
                    "content": update.message.text,
                    "caption": update.message.text,
                }
                save_db(db)
                context.user_data.clear()
                await update.message.reply_text(f"✅ Saved text for **{cat}**!", reply_markup=admin_panel_keyboard(), parse_mode="Markdown")
                return
            else:
                await update.message.reply_text("❌ Unsupported file type.")
                return

            db["files"][cat] = {
                "type": ftype,
                "file_id": fid,
                "caption": update.message.caption or cat,
            }
            save_db(db)
            context.user_data.clear()
            await update.message.reply_text(f"✅ Uploaded to **{cat}**!", reply_markup=admin_panel_keyboard(), parse_mode="Markdown")
            return

        elif admin_state == "broadcast":
            sent, failed = 0, 0
            for uid in list(db["users"].keys()):
                try:
                    await context.bot.copy_message(
                        chat_id=int(uid),
                        from_chat_id=update.message.chat_id,
                        message_id=update.message.message_id,
                    )
                    sent += 1
                except Exception:
                    failed += 1
            context.user_data.clear()
            await update.message.reply_text(
                f"📢 Broadcast Complete!\n✅ Sent: {sent} | ❌ Failed: {failed}",
                reply_markup=admin_panel_keyboard(),
            )
            return

        elif admin_state == "ban_toggle":
            target_id = text.strip()
            if target_id in db["users"]:
                cur = db["users"][target_id].get("banned", False)
                db["users"][target_id]["banned"] = not cur
                save_db(db)
                status = "BANNED" if not cur else "UNBANNED"
                await update.message.reply_text(f"✅ User `{target_id}` is now **{status}**.", reply_markup=admin_panel_keyboard(), parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ User ID not found.")
            context.user_data.clear()
            return

    # ---------- মেইন মেনু বাটনসমূহ ----------
    if text == "💎 GET CODE 💎":
        await update.message.reply_text(
            "Welcome To Code Store Bot",
            reply_markup=code_categories_keyboard(db),
        )

    elif text in ["🔙 Back", "🔙 Main Menu"]:
        context.user_data.clear()
        await update.message.reply_text(
            "Main Menu:",
            reply_markup=main_menu_keyboard(),
        )

    elif text == "👥 Referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        await update.message.reply_text(
            f"🎁 **Referral System**\n\n"
            f"Reward per referral: **{REFERRAL_REWARD}**\n"
            f"Total Referrals: **{u_data['referrals']}**\n"
            f"Balance: **{u_data['balance']}**\n\n"
            f"🔗 Your Link:\n`{ref_link}`",
            parse_mode="Markdown",
        )

    elif text == "💰 Balance":
        await update.message.reply_text(
            f"💰 Your Balance: **{u_data['balance']}**",
            parse_mode="Markdown",
        )

    elif text == "🆔 Chat Id":
        await update.message.reply_text(f"🆔 Your Chat ID: `{user.id}`", parse_mode="Markdown")

    elif text == "👤 My Account":
        await update.message.reply_text(
            f"👤 **My Account**\n\n"
            f"Name: {user.full_name}\n"
            f"Chat ID: `{user.id}`\n"
            f"Balance: **{u_data['balance']}**\n"
            f"Referrals: **{u_data['referrals']}**",
            parse_mode="Markdown",
        )

    elif text == "📖 How To Use":
        await update.message.reply_text(
            "📖 **How To Use**\n\n"
            "1. Join all channels & click JOINED.\n"
            "2. Click `💎 GET CODE 💎` and choose a category.\n"
            "3. Click the inline button and press **Confirm** to get your file."
        )

    # ---------- অ্যাডমিন বাটনসমূহ ----------
    elif text == "📤 Upload File" and is_admin(user.id):
        context.user_data["admin_state"] = "upload_cat"
        await update.message.reply_text("Enter category name (e.g. `Ai Image Generator`):", parse_mode="Markdown")

    elif text == "📢 Broadcast" and is_admin(user.id):
        context.user_data["admin_state"] = "broadcast"
        await update.message.reply_text("Send message, photo, voice, video or file to broadcast:")

    elif text == "👥 User List" and is_admin(user.id):
        lines = [
            f"• `{uid}` - {info.get('name')} | Bal: {info.get('balance')} | Ban: {info.get('banned')}"
            for uid, info in list(db["users"].items())[:30]
        ]
        await update.message.reply_text("👥 **Users:**\n\n" + ("\n".join(lines) or "Empty"), parse_mode="Markdown")

    elif text == "🚫 Ban/Unban User" and is_admin(user.id):
        context.user_data["admin_state"] = "ban_toggle"
        await update.message.reply_text("Enter User Chat ID to Ban/Unban:")

    # ---------- ক্যাটাগরি বাটন ক্লিক ----------
    elif text in db["files"]:
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(text, callback_data=f"req_file|{text}")]
        ])
        await update.message.reply_text(
            f"{text}\nNew Update Coming Soon....",
            reply_markup=markup,
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()

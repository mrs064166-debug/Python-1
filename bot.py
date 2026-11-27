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
BOT_TOKEN = os.getenv("BOT_TOKEN", "8222516603:AAGv9fph1jkZJKnzoSCvZddbZ7sUoDo5yzg")
ADMIN_IDS = [6985943036]  # এখানে তোমার টেলিগ্রাম নিউমেরিক ইউজার আইডি বসাও

# ফোর্স সাবস্ক্রাইব চ্যানেল (বটকে চ্যানেলের অ্যাডমিন করতে হবে)
FORCE_CHANNELS = [
    {"name": "Join Channel 1", "chat_id": "@your_channel_1", "url": "https://t.me/Miteam_official786_bd"},
    {"name": "Join Channel 2", "chat_id": "@your_channel_2", "url": "https://t.me/Miteam_official786_bd"},
    {"name": "Join Channel 3", "chat_id": "@your_channel_3", "url": "https://t.me/Miteam_official786_bd"},
]

DB_FILE = "bot_data.json"
REFERRAL_REWARD = 10  # প্রতি রেফারে পয়েন্ট/ব্যালেন্স

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# ================= ডেটাবেস হেল্পার =================
def load_db():
    if not os.path.exists(DB_FILE):
        data = {
            "users": {},      # user_id: {"name": ..., "balance": 0, "referrals": 0, "banned": False, "ref_by": None}
            "files": {},      # category_name: {"type": "document"|"video"|"photo", "file_id": ..., "caption": ...}
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
    for ch in FORCE_CHANNELS:
        rows.append([InlineKeyboardButton(f"📢 {ch['name']}", url=ch["url"])])
    rows.append([InlineKeyboardButton("🟢 JOINED", callback_data="check_joined")])
    return InlineKeyboardMarkup(rows)


# ================= কীবোর্ড লেআউট =================
def main_menu_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("💎 GET CODE 💎")],
        [KeyboardButton("👥 Referral"), KeyboardButton("💰 Balance")],
        [KeyboardButton("📖 How To Use")],
        [KeyboardButton("🆔 Chat Id"), KeyboardButton("👤 My Account")],
        [KeyboardButton("💸 Withdraw")],
    ]
    if is_admin(user_id):
        keyboard.append([KeyboardButton("🛠️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def code_categories_keyboard(db) -> ReplyKeyboardMarkup:
    categories = list(db["files"].keys())
    if not categories:
        categories = ["AI Image Generator", "Info Python File", "Camera Hacking", "Screen Capture File"]
    rows = []
    for i in range(0, len(categories), 2):
        row = [KeyboardButton(categories[i])]
        if i + 1 < len(categories):
            row.append(KeyboardButton(categories[i + 1]))
        rows.append(row)
    rows.append([KeyboardButton("🔙 Back To Main Menu")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("📤 Upload File"), KeyboardButton("📢 Broadcast")],
        [KeyboardButton("👥 User List"), KeyboardButton("🚫 Ban/Unban User")],
        [KeyboardButton("🔙 Back To Main Menu")],
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
        await update.message.reply_text("🚫 আপনি এই বট থেকে ব্যান হয়েছেন।")
        return

    if FORCE_CHANNELS and not await check_force_sub(user.id, context):
        await update.message.reply_text(
            f"👋 হ্যালো **{user.first_name}**!\n\n"
            "বট ব্যবহার করতে নিচের সব চ্যানেলে জয়েন করে **JOINED** বাটনে চাপ দিন:",
            reply_markup=force_sub_markup(),
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        f"✨ স্বাগতম **{user.first_name}**!\nনিচের মেনু থেকে অপশন বেছে নিন:",
        reply_markup=main_menu_keyboard(user.id),
        parse_mode="Markdown",
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    db = load_db()
    u_data = get_user(db, user.id, user.first_name)

    if u_data.get("banned"):
        await query.answer("🚫 আপনি ব্যান হয়েছেন!", show_alert=True)
        return

    if data == "check_joined":
        if await check_force_sub(user.id, context):
            await query.message.delete()
            await context.bot.send_message(
                chat_id=user.id,
                text="✅ ভেরিফিকেশন সফল! মূল মেনুতে স্বাগতম:",
                reply_markup=main_menu_keyboard(user.id),
            )
        else:
            await query.answer("❌ এখনো সব চ্যানেলে জয়েন করেননি!", show_alert=True)

    elif data.startswith("req_file|"):
        cat_name = data.split("|", 1)[1]
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"conf_file|{cat_name}"),
                InlineKeyboardButton("🔙 Back", callback_data="cancel_file"),
            ]
        ])
        await query.message.reply_text(
            f"⚡ **{cat_name}**\n\nফাইলটি পেতে নিচের **Confirm** বাটনে চাপ দিন:",
            reply_markup=markup,
            parse_mode="Markdown",
        )
        await query.answer()

    elif data.startswith("conf_file|"):
        cat_name = data.split("|", 1)[1]
        file_info = db["files"].get(cat_name)
        if not file_info:
            await query.message.reply_text("⚠️ এই ক্যাটাগরিতে এখনো কোনো ফাইল আপলোড করা হয়নি।")
            await query.answer()
            return

        ftype = file_info["type"]
        fid = file_info["file_id"]
        cap = file_info.get("caption") or f"📦 {cat_name}"

        if ftype == "document":
            await query.message.reply_document(document=fid, caption=cap)
        elif ftype == "photo":
            await query.message.reply_photo(photo=fid, caption=cap)
        elif ftype == "video":
            await query.message.reply_video(video=fid, caption=cap)
        else:
            await query.message.reply_text(cap)
        await query.answer("✅ ফাইল পাঠানো হয়েছে!")

    elif data == "cancel_file":
        await query.message.delete()
        await query.answer("বাতিল করা হয়েছে।")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user = update.effective_user
    text = update.message.text or ""
    db = load_db()
    u_data = get_user(db, user.id, user.first_name)

    if u_data.get("banned"):
        await update.message.reply_text("🚫 আপনি এই বট থেকে ব্যান হয়েছেন।")
        return

    if FORCE_CHANNELS and not await check_force_sub(user.id, context):
        await update.message.reply_text(
            "⚠️ আগে সব চ্যানেলে জয়েন করুন:",
            reply_markup=force_sub_markup(),
        )
        return

    # ---------- অ্যাডমিন স্টেট প্রসেসিং ----------
    admin_state = context.user_data.get("admin_state")
    if is_admin(user.id) and admin_state:
        if text == "🔙 Back To Main Menu" or text == "/cancel":
            context.user_data.clear()
            await update.message.reply_text("মূল মেনু:", reply_markup=main_menu_keyboard(user.id))
            return

        if admin_state == "upload_cat":
            context.user_data["upload_category"] = text.strip()
            context.user_data["admin_state"] = "upload_media"
            await update.message.reply_text(
                f"ক্যাটাগরি: **{text.strip()}**\nএখন ফাইল (Document), ছবি (Photo) অথবা ভিডিও (Video) পাঠান:",
                parse_mode="Markdown",
            )
            return

        elif admin_state == "upload_media":
            cat = context.user_data.get("upload_category")
            if update.message.document:
                ftype = "document"
                fid = update.message.document.file_id
            elif update.message.photo:
                ftype = "photo"
                fid = update.message.photo[-1].file_id
            elif update.message.video:
                ftype = "video"
                fid = update.message.video.file_id
            else:
                await update.message.reply_text("❌ দয়া করে একটি বৈধ ফাইল, ছবি বা ভিডিও পাঠান।")
                return

            db["files"][cat] = {
                "type": ftype,
                "file_id": fid,
                "caption": update.message.caption or f"📦 {cat}",
            }
            save_db(db)
            context.user_data.clear()
            await update.message.reply_text(
                f"✅ **{cat}** ক্যাটাগরিতে ফাইল সেভ হয়েছে!",
                reply_markup=admin_panel_keyboard(),
                parse_mode="Markdown",
            )
            return

        elif admin_state == "broadcast":
            sent = 0
            failed = 0
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
                f"📢 ব্রডকাস্ট সম্পন্ন!\n✅ সফল: {sent} | ❌ ব্যর্থ: {failed}",
                reply_markup=admin_panel_keyboard(),
            )
            return

        elif admin_state == "ban_toggle":
            target_id = text.strip()
            if target_id in db["users"]:
                current = db["users"][target_id].get("banned", False)
                db["users"][target_id]["banned"] = not current
                save_db(db)
                status = "ব্যান (Banned)" if not current else "আনব্যান (Unbanned)"
                await update.message.reply_text(
                    f"✅ ইউজার `{target_id}` এখন **{status}** অবস্থায় আছে।",
                    reply_markup=admin_panel_keyboard(),
                    parse_mode="Markdown",
                )
            else:
                await update.message.reply_text("❌ এই ইউজার আইডি ডেটাবেসে পাওয়া যায়নি।")
            context.user_data.clear()
            return

    # ---------- ইউজার ও অ্যাডমিন বাটন হ্যান্ডলার ----------
    if text == "💎 GET CODE 💎":
        await update.message.reply_text(
            "🔥 ক্যাটাগরি সিলেক্ট করুন:",
            reply_markup=code_categories_keyboard(db),
        )

    elif text == "🔙 Back To Main Menu":
        context.user_data.clear()
        await update.message.reply_text(
            "🏠 মূল মেনু:",
            reply_markup=main_menu_keyboard(user.id),
        )

    elif text == "👥 Referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        await update.message.reply_text(
            f"🎁 **রেফারেল সিস্টেম**\n\n"
            f"প্রতি সফল রেফারে পাবেন **{REFERRAL_REWARD}** পয়েন্ট!\n"
            f"মোট রেফার: **{u_data['referrals']}**\n\n"
            f"🔗 আপনার রেফার লিংক:\n`{ref_link}`",
            parse_mode="Markdown",
        )

    elif text == "💰 Balance":
        await update.message.reply_text(
            f"💰 আপনার বর্তমান ব্যালেন্স: **{u_data['balance']}** পয়েন্ট",
            parse_mode="Markdown",
        )

    elif text == "🆔 Chat Id":
        await update.message.reply_text(f"🆔 আপনার Chat ID: `{user.id}`", parse_mode="Markdown")

    elif text == "👤 My Account":
        await update.message.reply_text(
            f"👤 **অ্যাকাউন্ট তথ্য**\n\n"
            f"নাম: {user.full_name}\n"
            f"ID: `{user.id}`\n"
            f"ব্যালেন্স: **{u_data['balance']}**\n"
            f"রেফারেল: **{u_data['referrals']}**",
            parse_mode="Markdown",
        )

    elif text == "📖 How To Use":
        await update.message.reply_text(
            "📖 **ব্যবহারবিধি**\n\n"
            "১. সব চ্যানেলে জয়েন করে JOINED চাপুন।\n"
            "২. `💎 GET CODE 💎` থেকে ক্যাটাগরি বেছে নিন।\n"
            "৩. ইনলাইন বাটনে ক্লিক করে **Confirm** চাপলেই ফাইল পাবেন।"
        )

    elif text == "💸 Withdraw":
        if u_data["balance"] <= 0:
            await update.message.reply_text("❌ উইথড্র করার মতো পর্যাপ্ত ব্যালেন্স নেই।")
            return
        amt = u_data["balance"]
        u_data["balance"] = 0
        save_db(db)
        await update.message.reply_text(f"✅ **{amt}** পয়েন্টের উইথড্র রিকোয়েস্ট সাবমিট হয়েছে!", parse_mode="Markdown")
        for adm in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=adm,
                    text=f"💸 **নতুন উইথড্র রিকোয়েস্ট**\nইউজার: {user.full_name} (`{user.id}`)\nপরিমাণ: **{amt}**",
                    parse_mode="Markdown",
                )
            except Exception:
                pass

    elif text == "🛠️ Admin Panel" and is_admin(user.id):
        await update.message.reply_text(
            "🛠️ **অ্যাডমিন কন্ট্রোল প্যানেল**\nমোট ইউজার: " + str(len(db["users"])),
            reply_markup=admin_panel_keyboard(),
            parse_mode="Markdown",
        )

    elif text == "📤 Upload File" and is_admin(user.id):
        context.user_data["admin_state"] = "upload_cat"
        await update.message.reply_text(
            "যে ক্যাটাগরিতে ফাইল আপলোড করতে চান তার নাম লিখুন (যেমন: `AI Image Generator`):",
            parse_mode="Markdown",
        )

    elif text == "📢 Broadcast" and is_admin(user.id):
        context.user_data["admin_state"] = "broadcast"
        await update.message.reply_text(
            "সব ইউজারকে যে মেসেজ, ছবি বা ভয়েস পাঠাতে চান তা এখন পাঠান:"
        )

    elif text == "👥 User List" and is_admin(user.id):
        lines = [f"• `{uid}` — {info.get('name')} (Bal: {info.get('balance')}, Banned: {info.get('banned')})"
                 for uid, info in list(db["users"].items())[:30]]
        await update.message.reply_text(
            "👥 **ইউজার লিস্ট (সর্বোচ্চ ৩০ জন):**\n\n" + ("\n".join(lines) or "কেউ নেই"),
            parse_mode="Markdown",
        )

    elif text == "🚫 Ban/Unban User" and is_admin(user.id):
        context.user_data["admin_state"] = "ban_toggle"
        await update.message.reply_text("যে ইউজারকে ব্যান বা আনব্যান করতে চান তার Chat ID লিখুন:")

    elif text in db["files"] or text in ["AI Image Generator", "Info Python File", "Camera Hacking", "Screen Capture File"]:
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⚡ {text}", callback_data=f"req_file|{text}")]
        ])
        await update.message.reply_text(
            f"📦 **{text}**\n\nNew Update Ready! নিচের বাটনে ক্লিক করুন:",
            reply_markup=markup,
            parse_mode="Markdown",
        )


def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️ দয়া করে BOT_TOKEN এবং ADMIN_IDS সেট করুন।")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()

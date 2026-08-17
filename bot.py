import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)  # ✅ সঠিক

# ==================== BOT TOKEN ====================
TOKEN = "8760909596:AAFU7Um69lCCk_Wuf9kPWO8hQFC2hZ15Nvw"  # এখানে আপনার বট টোকেন দিন

# ==================== DATABASE SETUP ====================
class Database:
    def __init__(self, db_name="bot_database.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        """ডেটাবেস টেবিল তৈরি করুন"""
        # ইউজার টেবিল
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_date TEXT,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0
            )
        ''')
        
        # মেসেজ লগ টেবিল
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                timestamp TEXT
            )
        ''')
        
        # সেটিংস টেবিল
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # প্রোডাক্ট/আইটেম টেবিল
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                price INTEGER,
                stock INTEGER DEFAULT 0
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, last_name):
        """নতুন ইউজার যোগ করুন"""
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, joined_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error adding user: {e}")
    
    def get_user(self, user_id):
        """ইউজার তথ্য নিন"""
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def update_balance(self, user_id, amount):
        """ব্যালেন্স আপডেট করুন"""
        self.cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def update_points(self, user_id, points):
        """পয়েন্ট আপডেট করুন"""
        self.cursor.execute('UPDATE users SET points = points + ? WHERE user_id = ?', (points, user_id))
        self.conn.commit()
    
    def get_all_users(self):
        """সব ইউজার নিন"""
        self.cursor.execute('SELECT * FROM users')
        return self.cursor.fetchall()
    
    def get_user_count(self):
        """মোট ইউজার সংখ্যা"""
        self.cursor.execute('SELECT COUNT(*) FROM users')
        return self.cursor.fetchone()[0]
    
    def set_admin(self, user_id, is_admin):
        """অ্যাডমিন সেট করুন"""
        self.cursor.execute('UPDATE users SET is_admin = ? WHERE user_id = ?', (is_admin, user_id))
        self.conn.commit()
    
    def ban_user(self, user_id, is_banned):
        """ইউজার ব্যান করুন"""
        self.cursor.execute('UPDATE users SET is_banned = ? WHERE user_id = ?', (is_banned, user_id))
        self.conn.commit()
    
    def log_message(self, user_id, message):
        """মেসেজ লগ করুন"""
        self.cursor.execute('INSERT INTO message_logs (user_id, message, timestamp) VALUES (?, ?, ?)',
                           (user_id, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.conn.commit()
    
    def add_product(self, name, description, price, stock):
        """প্রোডাক্ট যোগ করুন"""
        self.cursor.execute('INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)',
                           (name, description, price, stock))
        self.conn.commit()
    
    def get_products(self):
        """সব প্রোডাক্ট নিন"""
        self.cursor.execute('SELECT * FROM products')
        return self.cursor.fetchall()

# ডেটাবেস ইনিশিয়ালাইজ
db = Database()

# ==================== KEYBOARDS ====================
def get_main_keyboard():
    """মেইন কিবোর্ড"""
    keyboard = [
        [InlineKeyboardButton("👤 প্রোফাইল", callback_data='profile')],
        [InlineKeyboardButton("💰 ব্যালেন্স", callback_data='balance'),
         InlineKeyboardButton("🎯 পয়েন্টস", callback_data='points')],
        [InlineKeyboardButton("🛍 প্রোডাক্টস", callback_data='products')],
        [InlineKeyboardButton("📊 স্ট্যাটস", callback_data='stats')],
        [InlineKeyboardButton("ℹ️ হেল্প", callback_data='help')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    """অ্যাডমিন কিবোর্ড"""
    keyboard = [
        [InlineKeyboardButton("👥 ইউজার লিস্ট", callback_data='admin_users')],
        [InlineKeyboardButton("📨 ব্রডকাস্ট", callback_data='admin_broadcast')],
        [InlineKeyboardButton("➕ প্রোডাক্ট যোগ", callback_data='admin_add_product')],
        [InlineKeyboardButton("📊 বট স্ট্যাটস", callback_data='admin_stats')],
        [InlineKeyboardButton("🔙 মেইন মেনু", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_reply_keyboard():
    """রিপ্লাই কিবোর্ড"""
    keyboard = [
        [KeyboardButton("👤 প্রোফাইল"), KeyboardButton("💰 ব্যালেন্স")],
        [KeyboardButton("🛍 প্রোডাক্টস"), KeyboardButton("ℹ️ হেল্প")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ==================== CONVERSATION STATES ====================
WAITING_FOR_BROADCAST = 1
WAITING_FOR_PRODUCT_NAME = 2
WAITING_FOR_PRODUCT_PRICE = 3

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """স্টার্ট কমান্ড"""
    user = update.effective_user
    
    # ইউজার ডেটাবেসে যোগ করুন
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = f"""
╔══════════════════╗
   🤖 স্বাগতম {user.first_name}!
╚══════════════════╝

আমি একটি মাল্টি-ফিচার বট।
নিচের বাটন থেকে আপনার পছন্দ নির্বাচন করুন।

📢 আমাদের চ্যানেল: @YourChannel
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """হেল্প কমান্ড"""
    help_text = """
📚 **কমান্ড লিস্ট:**

👤 **ইউজার কমান্ড:**
/start - বট শুরু করুন
/profile - প্রোফাইল দেখুন
/balance - ব্যালেন্স চেক করুন
/products - প্রোডাক্ট লিস্ট
/help - হেল্প মেনু

👑 **অ্যাডমিন কমান্ড:**
/admin - অ্যাডমিন প্যানেল
/broadcast - সবাইকে মেসেজ
/addproduct - প্রোডাক্ট যোগ
/users - ইউজার লিস্ট
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """প্রোফাইল কমান্ড"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if user_data:
        profile_text = f"""
👤 **প্রোফাইল তথ্য:**

🆔 User ID: `{user_data[0]}`
👤 নাম: {user_data[2] or 'N/A'}
📝 Username: @{user_data[1] or 'N/A'}
📅 যোগদান: {user_data[4]}
💰 ব্যালেন্স: {user_data[6]}
🎯 পয়েন্টস: {user_data[7]}
⭐ স্ট্যাটাস: {"Admin" if user_data[5] else "User"}
        """
        await update.message.reply_text(profile_text, parse_mode='Markdown')

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ব্যালেন্স কমান্ড"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if user_data:
        balance_text = f"""
💰 **আপনার ব্যালেন্স:**

বর্তমান ব্যালেন্স: {user_data[6]} টাকা
মোট পয়েন্টস: {user_data[7]}

📌 ব্যালেন্স বাড়াতে আমাদের চ্যানেলে যুক্ত থাকুন!
        """
        await update.message.reply_text(balance_text, parse_mode='Markdown')

async def products_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """প্রোডাক্টস কমান্ড"""
    products = db.get_products()
    
    if products:
        products_text = "🛍 **আমাদের প্রোডাক্টস:**\n\n"
        for product in products:
            products_text += f"📦 {product[1]}\n"
            products_text += f"📝 {product[2]}\n"
            products_text += f"💰 দাম: {product[3]} টাকা\n"
            products_text += f"📊 স্টক: {product[4]}\n\n"
    else:
        products_text = "❌ এখনো কোনো প্রোডাক্ট যোগ করা হয়নি।"
    
    await update.message.reply_text(products_text, parse_mode='Markdown')

# ==================== ADMIN COMMANDS ====================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অ্যাডমিন প্যানেল"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if user_data and user_data[5]:  # is_admin চেক
        await update.message.reply_text(
            "👑 **অ্যাডমিন প্যানেল**\n\nআপনার পছন্দ নির্বাচন করুন:",
            reply_markup=get_admin_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ আপনি অ্যাডমিন নন!")

async def users_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ইউজার লিস্ট"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if user_data and user_data[5]:
        users = db.get_all_users()
        total_users = len(users)
        
        users_text = f"👥 **মোট ইউজার:** {total_users}\n\n"
        for user in users[:10]:  # প্রথম ১০ জন
            users_text += f"🆔 {user[0]} | 👤 {user[2]} | @{user[1]}\n"
        
        if total_users > 10:
            users_text += f"\n... আরও {total_users - 10} জন ইউজার"
        
        await update.message.reply_text(users_text, parse_mode='Markdown')

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ব্রডকাস্ট মেসেজ"""
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if user_data and user_data[5]:
        await update.message.reply_text(
            "📨 ব্রডকাস্ট মেসেজ লিখুন:\n\n"
            "সবাইকে পাঠানো হবে।"
        )
        return WAITING_FOR_BROADCAST

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ব্রডকাস্ট মেসেজ হ্যান্ডেল"""
    message = update.message.text
    users = db.get_all_users()
    
    sent_count = 0
    failed_count = 0
    
    for user in users:
        try:
            await context.bot.send_message(chat_id=user[0], text=f"📢 **ব্রডকাস্ট:**\n\n{message}", parse_mode='Markdown')
            sent_count += 1
        except:
            failed_count += 1
    
    await update.message.reply_text(
        f"✅ ব্রডকাস্ট সম্পন্ন!\n\n"
        f"📤 পাঠানো হয়েছে: {sent_count}\n"
        f"❌ ব্যর্থ: {failed_count}"
    )
    return ConversationHandler.END

# ==================== CALLBACK HANDLERS ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বাটন ক্লিক হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    if query.data == 'profile':
        await profile_command(update, context)
    
    elif query.data == 'balance':
        await balance_command(update, context)
    
    elif query.data == 'points':
        points_text = f"🎯 আপনার মোট পয়েন্টস: {user_data[7] if user_data else 0}"
        await query.message.reply_text(points_text)
    
    elif query.data == 'products':
        await products_command(update, context)
    
    elif query.data == 'stats':
        total_users = db.get_user_count()
        stats_text = f"""
📊 **বট স্ট্যাটস:**

👥 মোট ইউজার: {total_users}
📅 আজকের তারিখ: {datetime.now().strftime('%Y-%m-%d')}
⏰ সময়: {datetime.now().strftime('%H:%M:%S')}

🛠 ডেভেলপার: @YourUsername
        """
        await query.message.reply_text(stats_text, parse_mode='Markdown')
    
    elif query.data == 'help':
        await help_command(update, context)
    
    elif query.data == 'admin_users':
        await users_list_command(update, context)
    
    elif query.data == 'admin_broadcast':
        await query.message.reply_text("📨 ব্রডকাস্ট মেসেজ লিখুন:")
    
    elif query.data == 'admin_stats':
        total_users = db.get_user_count()
        stats_text = f"""
📊 **অ্যাডমিন স্ট্যাটস:**

👥 মোট ইউজার: {total_users}
📦 মোট প্রোডাক্ট: {len(db.get_products())}
📅 আজকের তারিখ: {datetime.now().strftime('%Y-%m-%d')}
        """
        await query.message.reply_text(stats_text, parse_mode='Markdown')
    
    elif query.data == 'main_menu':
        await query.message.reply_text("🔙 মেইন মেনুতে ফিরে গেলেন", reply_markup=get_main_keyboard())

# ==================== MESSAGE HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সাধারণ মেসেজ হ্যান্ডলার"""
    user = update.effective_user
    text = update.message.text
    
    # ডেটাবেসে ইউজার যোগ করুন
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    # মেসেজ লগ করুন
    db.log_message(user.id, text)
    
    # পয়েন্ট যোগ করুন
    db.update_points(user.id, 1)
    
    # সাধারণ উত্তর
    if text == "👤 প্রোফাইল":
        await profile_command(update, context)
    elif text == "💰 ব্যালেন্স":
        await balance_command(update, context)
    elif text == "🛍 প্রোডাক্টস":
        await products_command(update, context)
    elif text == "ℹ️ হেল্প":
        await help_command(update, context)
    else:
        await update.message.reply_text(
            "আমি আপনার মেসেজ পেয়েছি! ✅\n"
            "নিচের বাটন ব্যবহার করুন অথবা /help দেখুন।",
            reply_markup=get_main_keyboard()
        )

# ==================== ERROR HANDLER ====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """এরর হ্যান্ডলার"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ একটি সমস্যা হয়েছে। পরে আবার চেষ্টা করুন।"
        )

# ==================== MAIN FUNCTION ====================
def main():
    """মেইন ফাংশন"""
    # Application তৈরি
    app = Application.builder().token(TOKEN).build()
    
    # Conversation Handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('broadcast', broadcast_command)],
        states={
            WAITING_FOR_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast)]
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)]
    )
    
    # Command Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("products", products_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("users", users_list_command))
    app.add_handler(conv_handler)
    
    # Callback Handler
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Message Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error Handler
    app.add_error_handler(error_handler)
    
    # Bot চালু করুন
    print("🤖 বট চালু হচ্ছে...")
    print("✅ ডেটাবেস কানেক্টেড!")
    print("🚀 বট এখন চলছে!")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

import logging
import asyncio
import aiosqlite
import g4f
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = '8356590220:AAHbhriXSYBHBPvU34q4YxgmHgHNfdO9780'
ADMIN_ID = 7319857848 
WEATHER_API = "b7280387ca556819616e453c5e89647b"

CHANNELS = [
    {'id': '@buxorobolalari', 'link': 'https://t.me/buxorobolalari'},
    {'id': '@bolalartashkiloti_buxoro', 'link': 'https://t.me/bolalartashkiloti_buxoro'}
]

VILOYATLAR = {
    "tashkent": "Tashkent", "samarkand": "Samarkand", "bukhara": "Bukhara",
    "andijan": "Andijan", "namangan": "Namangan", "fergana": "Fergana",
    "nukus": "Nukus", "karshi": "Karshi", "termez": "Termez",
    "jizzakh": "Jizzakh", "navoi": "Navoiy", "guliston": "Guliston", "urgench": "Urgench"
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class States(StatesGroup):
    waiting_for_ads = State()
    waiting_for_feedback = State()
    waiting_for_name = State()

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, 
            ref_count INTEGER DEFAULT 0, 
            ai_requests INTEGER DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.commit()

def get_main_menu(user_id):
    kb = [
        [InlineKeyboardButton(text="🤖 AI Chat", callback_data="ai_chat"), InlineKeyboardButton(text="🎨 Rasm Chizish", callback_data="ai_image")],
        [InlineKeyboardButton(text="🌤 Ob-havo", callback_data="weather_menu"), InlineKeyboardButton(text="🕋 Namoz Vaqti", callback_data="namoz_menu")],
        [InlineKeyboardButton(text="📖 Ismlar Ma'nosi", callback_data="names_meaning"), InlineKeyboardButton(text="💵 Valyuta", callback_data="currency")],
        [InlineKeyboardButton(text="👤 Profilim", callback_data="my_profile"), InlineKeyboardButton(text="✍️ Adminga yozish", callback_data="feedback")],
        [InlineKeyboardButton(text="🔗 Do'stlarni taklif qilish", callback_data="referral")]
    ]
    if user_id == ADMIN_ID:
        kb.append([InlineKeyboardButton(text="📢 Reklama", callback_data="send_ads"), InlineKeyboardButton(text="📊 Statistika", callback_data="stat")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_back_btn():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="main_menu")]])

async def check_subs(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch['id'], user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except: return False
    return True

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
        await db.commit()
    
    if not await check_subs(message.from_user.id):
        kb = [[InlineKeyboardButton(text="Kanalga a'zo bo'lish", url=ch['link'])] for ch in CHANNELS]
        kb.append([InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_sub")])
        return await message.answer("Botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    
    await message.answer(f"Salom {message.from_user.first_name}! Barcha xizmatlar tayyor. Tanlang:", reply_markup=get_main_menu(message.from_user.id))

@dp.callback_query(F.data == "main_menu")
async def back_home(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Asosiy menyu:", reply_markup=get_main_menu(call.from_user.id))

@dp.callback_query(F.data == "namoz_menu")
async def namoz_menu(call: types.CallbackQuery):
    kb = []
    temp_row = []
    for code, name in VILOYATLAR.items():
        temp_row.append(InlineKeyboardButton(text=name, callback_data=f"n_{name}"))
        if len(temp_row) == 2: kb.append(temp_row); temp_row = []
    kb.append(temp_row)
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="main_menu")])
    await call.message.edit_text("Namoz vaqtlari uchun hududni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("n_"))
async def show_namoz(call: types.CallbackQuery):
    shahar = call.data.split("_")[1]
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://islomapi.uz/api/present/day?region={shahar}") as resp:
            if resp.status == 200:
                d = await resp.json()
                t = d['times']
                text = f"🕋 {shahar} namoz vaqtlari:\n\n🏙 Tong: {t['tong_saharlik']}\n☀️ Quyosh: {t['quyosh']}\n☀️ Peshin: {t['peshin']}\n🌇 Asr: {t['asr']}\n🌆 Shom: {t['shom_iftor']}\n🌃 Xufton: {t['hufton']}"
                await call.message.edit_text(text, reply_markup=get_back_btn())

@dp.callback_query(F.data == "names_meaning")
async def name_start(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_name)
    await call.message.edit_text("Ismni yuboring (Masalan: 'Ali'):", reply_markup=get_back_btn())

@dp.message(States.waiting_for_name)
async def get_name_meaning(message: types.Message, state: FSMContext):
    msg = await message.answer("🔍 Ism ma'nosi qidirilmoqda...")
    res = await g4f.ChatCompletion.create_async(model=g4f.models.gpt_4, messages=[{"role": "user", "content": f"{message.text} ismining o'zbekcha ma'nosini batafsil tushuntirib ber."}])
    await msg.edit_text(str(res), reply_markup=get_back_btn())
    await state.clear()

@dp.callback_query(F.data == "feedback")
async def feedback_start(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_feedback)
    await call.message.edit_text("Adminga xabaringizni yuboring:", reply_markup=get_back_btn())

@dp.message(States.waiting_for_feedback)
async def send_feedback_to_admin(message: types.Message, state: FSMContext):
    await bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    await bot.send_message(ADMIN_ID, f"🆔 User ID: {message.from_user.id}\n👤 User: {message.from_user.full_name}")
    await message.answer("✅ Xabaringiz adminga yuborildi!", reply_markup=get_back_btn())
    await state.clear()

@dp.callback_query(F.data == "my_profile")
async def show_profile(call: types.CallbackQuery):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT ref_count, ai_requests, join_date FROM users WHERE user_id = ?", (call.from_user.id,)) as c:
            u = await c.fetchone()
    text = f"👤 Sizning profilingiz:\n\n🆔 ID: {call.from_user.id}\n📅 A'zo bo'lingan: {u[2]}\n👥 Takliflar: {u[0]} ta\n🤖 AI so'rovlar: {u[1]} ta"
    await call.message.edit_text(text, reply_markup=get_back_btn())

@dp.callback_query(F.data == "referral")
async def referral_link(call: types.CallbackQuery):
    link = f"https://t.me/{(await bot.get_me()).username}?start={call.from_user.id}"
    await call.message.edit_text(f"🔗 Taklif havolangiz:\n`{link}`\n\nHar bir taklif uchun bot imkoniyatlari kengayadi!", reply_markup=get_back_btn())

@dp.callback_query(F.data == "ai_chat")
async def ai_chat_prompt(call: types.CallbackQuery):
    await call.message.edit_text("🤖 Men GPT-4 yordamchisiman. Savolingizni yozing:", reply_markup=get_back_btn())

@dp.callback_query(F.data == "ai_image")
async def ai_image_prompt(call: types.CallbackQuery):
    await call.message.edit_text("🎨 Nimaning rasmini chizay? Batafsil yozing (Masalan: 'Qizil dengizda kema'):", reply_markup=get_back_btn())

@dp.message(F.text, F.chat.type == "private")
async def handle_ai_requests(message: types.Message, state: FSMContext):
    if not await check_subs(message.from_user.id): return
    if await state.get_state() in [States.waiting_for_ads, States.waiting_for_feedback, States.waiting_for_name]: return

    msg = await message.answer("⏳ AI ishlamoqda...")
    try:
        async with aiosqlite.connect("users.db") as db:
            await db.execute("UPDATE users SET ai_requests = ai_requests + 1 WHERE user_id = ?", (message.from_user.id,))
            await db.commit()

        res = await g4f.ChatCompletion.create_async(model=g4f.models.gpt_4, messages=[{"role": "user", "content": message.text}])
        await msg.edit_text(str(res), reply_markup=get_back_btn())
    except:
        await msg.edit_text("❌ AI hozirda band.", reply_markup=get_back_btn())

@dp.callback_query(F.data == "weather_menu")
async def weather_m(call: types.CallbackQuery):
    kb = []
    temp_row = []
    for code, name in VILOYATLAR.items():
        temp_row.append(InlineKeyboardButton(text=name, callback_data=f"w_{name}"))
        if len(temp_row) == 2: kb.append(temp_row); temp_row = []
    kb.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="main_menu")])
    await call.message.edit_text("Viloyatni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("w_"))
async def show_w(call: types.CallbackQuery):
    city = call.data.split("_")[1]
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API}&units=metric&lang=uz"
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            d = await r.json()
            t = f"📍 {city}\n🌡 Harorat: {d['main']['temp']}°C\n☁️ Holat: {d['weather'][0]['description']}"
            await call.message.edit_text(t, reply_markup=get_back_btn())

@dp.callback_query(F.data == "currency")
async def curr(call: types.CallbackQuery):
    async with aiohttp.ClientSession() as s:
        async with s.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/") as r:
            d = await r.json()
            usd = next(x for x in d if x['Ccy'] == 'USD')
            await call.message.edit_text(f"💰 1 USD = {usd['Rate']} so'm", reply_markup=get_back_btn())

@dp.callback_query(F.data == "stat")
async def stats(call: types.CallbackQuery):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            count = await c.fetchone()
    await call.message.answer(f"📊 Jami foydalanuvchilar: {count[0]} ta")

@dp.callback_query(F.data == "send_ads")
async def ad_pr(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_ads)
    await call.message.answer("Reklama yuboring:")

@dp.message(States.waiting_for_ads)
async def broadcast(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            async for row in cursor:
                try: await message.copy_to(row[0])
                except: pass
    await message.answer("📢 Yuborildi.")
    await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

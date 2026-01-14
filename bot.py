import logging
import asyncio
import aiosqlite
import g4f
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp

API_TOKEN = '8356590220:AAHbhriXSYBHBPvU34q4YxgmHgHNfdO9780'
ADMIN_ID = 7319857848  
WEATHER_API = "b7280387ca556819616e453c5e89647b"

CHANNELS = [
    {'id': '@buxorobolalari', 'link': 'https://t.me/buxorobolalari'},
    {'id': '@bolalartashkiloti_buxoro', 'link': 'https://t.me/bolalartashkiloti_buxoro'}
]

VILOYATLAR = {
    "tashkent": "Toshkent", "samarkand": "Samarqand", "bukhara": "Buxoro",
    "andijan": "Andijon", "namangan": "Namangan", "fergana": "Farg'ona",
    "nukus": "Nukus", "karshi": "Qarshi", "termez": "Termiz",
    "jizzakh": "Jizzax", "navoi": "Navoiy", "guliston": "Guliston", "urgench": "Urganch"
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class AdminStates(StatesGroup):
    waiting_for_ads = State()

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
        await db.commit()

async def check_subs(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch['id'], user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except Exception: return False
    return True

async def get_currency():
    try:
        url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                data = await resp.json()
                usd_data = next(item for item in data if item['Ccy'] == 'USD')
                return f"🇺🇿 Markaziy Bank kursi:\n💰 1 USD = {usd_data['Rate']} so'm\n📅 Sana: {usd_data['Date']}"
    except Exception as e:
        return "❌ Valyuta kursini hozircha olib bo'lmadi."

async def get_weather(city_code):
    try:
        city_name = VILOYATLAR.get(city_code, "Toshkent")
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={WEATHER_API}&units=metric&lang=uz"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return f"📍 {city_name}: {data['main']['temp']}°C, {data['weather'][0]['description']}"
                return "❌ Ma'lumot topilmadi."
    except Exception:
        return "❌ Ob-havo xizmati xatosi."

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
        await db.commit()

    if not await check_subs(message.from_user.id):
        kb = [[InlineKeyboardButton(text="Kanalga a'zo bo'lish", url=ch['link'])] for ch in CHANNELS]
        kb.append([InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_sub")])
        return await message.answer("Botdan foydalanish uchun kanallarga a'zo bo'ling:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    kb = [
        [InlineKeyboardButton(text="Ob-havo 🌤", callback_data="weather_menu"), InlineKeyboardButton(text="Valyuta 💵", callback_data="currency")],
        [InlineKeyboardButton(text="AI bilan gaplashish 🤖", callback_data="ai_chat")]
    ]
    if message.from_user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton(text="Reklama 📢", callback_data="send_ads"), InlineKeyboardButton(text="Statistika 📊", callback_data="stat")])
    
    await message.answer("Xush kelibsiz! Bo'limni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "check_sub")
async def check_callback(call: types.CallbackQuery):
    if await check_subs(call.from_user.id):
        await call.message.delete()
        await start_cmd(call.message)
    else:
        await call.answer("A'zo bo'lmadingiz!", show_alert=True)

@dp.callback_query(F.data == "currency")
async def currency_call(call: types.CallbackQuery):
    text = await get_currency()
    await call.message.answer(text)
    await call.answer()

@dp.callback_query(F.data == "weather_menu")
async def weather_menu(call: types.CallbackQuery):
    kb = []
    temp_row = []
    for code, name in VILOYATLAR.items():
        temp_row.append(InlineKeyboardButton(text=name, callback_data=f"w_{code}"))
        if len(temp_row) == 2: kb.append(temp_row); temp_row = []
    if temp_row: kb.append(temp_row)
    await call.message.edit_text("Viloyatni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("w_"))
async def show_weather(call: types.CallbackQuery):
    await call.message.answer(await get_weather(call.data.split("_")[1]))
    await call.answer()

@dp.callback_query(F.data == "ai_chat")
async def ai_info(call: types.CallbackQuery):
    await call.message.answer("🤖 Savolingizni yozing (Masalan: 'Toshkent haqida ma'lumot ber'):")
    await call.answer()

@dp.message(F.text, F.chat.type == "private")
async def chat_ai(message: types.Message, state: FSMContext):
    # Admin reklama yozayotgan bo'lsa AI ishlamasligi kerak
    current_state = await state.get_state()
    if current_state == AdminStates.waiting_for_ads:
        return

    if not await check_subs(message.from_user.id):
        return await message.answer("Avval kanallarga a'zo bo'ling.")

    msg = await message.answer("⏳ AI o'ylamoqda...")
    
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_4, # Barqarorroq model
            messages=[{"role": "user", "content": message.text}],
        )
        
        if response:
            await msg.edit_text(str(response))
        else:
            await msg.edit_text("❌ AI javob bera olmadi. Qayta urinib ko'ring.")
            
    except Exception as e:
        logging.error(f"AI xatosi: {e}")
        await msg.edit_text("❌ AI hozirda band yoki ulanishda xato. Birozdan so'ng urinib ko'ring.")

@dp.callback_query(F.data == "stat")
async def show_stat(call: types.CallbackQuery):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            count = await cursor.fetchone()
    await call.message.answer(f"📊 Jami foydalanuvchilar: {count[0]} ta")

@dp.callback_query(F.data == "send_ads")
async def ads_prompt(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_ads)
    await call.message.answer("📢 Reklama xabarini yuboring (Matn, rasm yoki video):")

@dp.message(AdminStates.waiting_for_ads)
async def broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            users = await cursor.fetchall()
    
    sent = 0
    for row in users:
        try:
            await message.copy_to(row[0])
            sent += 1
            await asyncio.sleep(0.05) # Spamdan himoya
        except: pass
    
    await message.answer(f"✅ Reklama {sent} ta foydalanuvchiga yuborildi.")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

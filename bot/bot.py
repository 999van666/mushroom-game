import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
    PreCheckoutQuery,
)
from dotenv import load_dotenv

from database.database import SessionLocal
from database.models import User, Purchase, UserBoost

from datetime import datetime, timedelta


load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")

if not WEBAPP_URL:
    raise RuntimeError("WEBAPP_URL is not configured")


dp = Dispatcher()


# ============================================================
# ТОВАРЫ TELEGRAM STARS
# ============================================================

STARS_PRODUCTS = {
    "energy_10": {
        "name": "⚡ +10 энергии",
        "description": "Мгновенно восстановить 10 энергии",
        "stars": 5,
    },
    "energy_full": {
        "name": "⚡ Полная энергия",
        "description": "Полностью восстановить энергию",
        "stars": 10,
    },
    "basket_10": {
        "name": "🧺 +10 кг корзины",
        "description": "Навсегда увеличить вместимость корзины",
        "stars": 25,
    },
    "luck_1h": {
        "name": "🍀 Удача на 1 час",
        "description": "+25% к качеству найденных грибов",
        "stars": 15,
    },
    "search_1h": {
        "name": "🔎 Улучшенный поиск на 1 час",
        "description": "+25% к шансу редких грибов",
        "stars": 20,
    },
    "starter_pack": {
        "name": "🎁 Набор грибника",
        "description": "+20 энергии, +5 кг корзины и 1000 монет",
        "stars": 50,
    },
}


# ============================================================
# /START
# ============================================================

@dp.message(CommandStart())
async def start(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🍄 Открыть Грибалку",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ],
        resize_keyboard=True,
    )

    await message.answer(
        "🍄 Добро пожаловать в «Грибалку»!\n\n"
        "Ищи грибы, повышай уровень и собирай коллекцию.",
        reply_markup=kb,
    )


# ============================================================
# PRE-CHECKOUT
# ============================================================

@dp.pre_checkout_query()
async def process_pre_checkout_query(
    pre_checkout_query: PreCheckoutQuery,
):
    """
    Telegram вызывает этот обработчик непосредственно перед оплатой.

    Здесь обязательно проверяем:
    - валюту XTR;
    - payload;
    - пользователя;
    - товар;
    - стоимость.
    """

    payload = pre_checkout_query.invoice_payload

    parts = payload.split(":")

    if len(parts) != 3 or parts[0] != "mushroom":
        await pre_checkout_query.answer(
            ok=False,
            error_message="Некорректный платёж.",
        )
        return

    try:
        telegram_id = int(parts[1])
    except ValueError:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Некорректный идентификатор пользователя.",
        )
        return

    product_id = parts[2]

    product = STARS_PRODUCTS.get(product_id)

    if not product:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Товар больше недоступен.",
        )
        return

    # Проверяем пользователя
    if pre_checkout_query.from_user.id != telegram_id:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Пользователь платежа не совпадает с заказом.",
        )
        return

    # Для Telegram Stars должна использоваться XTR
    if pre_checkout_query.currency != "XTR":
        await pre_checkout_query.answer(
            ok=False,
            error_message="Некорректная валюта платежа.",
        )
        return

    # Проверяем стоимость
    if pre_checkout_query.total_amount != product["stars"]:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Некорректная стоимость товара.",
        )
        return

    await pre_checkout_query.answer(ok=True)


# ============================================================
# УСПЕШНАЯ ОПЛАТА
# ============================================================

@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """
    Начисляем товар ТОЛЬКО после получения successful_payment.
    """

    payment = message.successful_payment

    if not payment:
        return

    # --------------------------------------------------------
    # Проверяем валюту
    # --------------------------------------------------------

    if payment.currency != "XTR":
        await message.answer(
            "⚠️ Получен платёж с неподдерживаемой валютой."
        )
        return

    # --------------------------------------------------------
    # Разбираем payload
    # --------------------------------------------------------

    payload = payment.invoice_payload
    parts = payload.split(":")

    if len(parts) != 3 or parts[0] != "mushroom":
        await message.answer(
            "⚠️ Не удалось определить товар платежа."
        )
        return

    try:
        telegram_id = int(parts[1])
    except ValueError:
        await message.answer(
            "⚠️ Некорректный идентификатор пользователя."
        )
        return

    product_id = parts[2]

    # --------------------------------------------------------
    # Дополнительная проверка пользователя
    # --------------------------------------------------------

    if message.from_user is None:
        return

    if message.from_user.id != telegram_id:
        await message.answer(
            "⚠️ Пользователь платежа не совпадает с заказом."
        )
        return

    # --------------------------------------------------------
    # Получаем товар
    # --------------------------------------------------------

    product = STARS_PRODUCTS.get(product_id)

    if not product:
        await message.answer(
            "⚠️ Товар платежа не найден."
        )
        return

    # --------------------------------------------------------
    # Проверяем сумму
    # --------------------------------------------------------

    if payment.total_amount != product["stars"]:
        await message.answer(
            "⚠️ Некорректная сумма платежа."
        )
        return

    # --------------------------------------------------------
    # Открываем БД
    # --------------------------------------------------------

    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.telegram_id == telegram_id)
            .first()
        )

        if not user:
            await message.answer(
                "⚠️ Игрок не найден."
            )
            return

        # ----------------------------------------------------
        # ЗАЩИТА ОТ ПОВТОРНОГО НАЧИСЛЕНИЯ
        # ----------------------------------------------------

        existing_purchase = (
            db.query(Purchase)
            .filter(
                Purchase.telegram_payment_charge_id
                == payment.telegram_payment_charge_id
            )
            .first()
        )

        if existing_purchase:
            await message.answer(
                "ℹ️ Этот платёж уже был обработан."
            )
            return

        # ----------------------------------------------------
        # СОЗДАЁМ ЗАПИСЬ О ПОКУПКЕ
        # ----------------------------------------------------

        purchase = Purchase(
            user_id=user.id,
            product_id=product_id,
            stars=product["stars"],
            telegram_payment_charge_id=(
                payment.telegram_payment_charge_id
            ),
            status="successful",
        )

        db.add(purchase)

        # ----------------------------------------------------
        # НАЧИСЛЯЕМ ТОВАР
        # ----------------------------------------------------

        if product_id == "energy_10":

            user.energy = min(
                user.max_energy,
                user.energy + 10,
            )

        elif product_id == "energy_full":

            user.energy = user.max_energy

        elif product_id == "basket_10":

            user.basket_capacity += 10

        elif product_id == "luck_1h":

            boost = UserBoost(
                user_id=user.id,
                boost_type="luck",
                value=1.25,
                expires_at=(
                    datetime.utcnow()
                    + timedelta(hours=1)
                ),
            )

            db.add(boost)

        elif product_id == "search_1h":

            boost = UserBoost(
                user_id=user.id,
                boost_type="search",
                value=1.25,
                expires_at=(
                    datetime.utcnow()
                    + timedelta(hours=1)
                ),
            )

            db.add(boost)

        elif product_id == "starter_pack":

            user.energy = min(
                user.max_energy,
                user.energy + 20,
            )

            user.basket_capacity += 5
            user.coins += 1000

        # ----------------------------------------------------
        # СОХРАНЯЕМ
        # ----------------------------------------------------

        db.commit()

    except Exception:
        db.rollback()

        await message.answer(
            "⚠️ Платёж получен, но произошла ошибка "
            "при начислении товара. Обратитесь в поддержку."
        )

        raise

    finally:
        db.close()

    # --------------------------------------------------------
    # УСПЕШНО
    # --------------------------------------------------------

    await message.answer(
        f"⭐ Оплата прошла успешно!\n\n"
        f"Получено: {product['name']}\n"
        f"Стоимость: {product['stars']} ⭐"
    )


# ============================================================
# ПОДДЕРЖКА ПО ПЛАТЕЖАМ
# ============================================================

@dp.message(F.text == "/paysupport")
async def payment_support(message: Message):
    await message.answer(
        "🍄 Поддержка «Грибалки»\n\n"
        "Если у вас возникла проблема с оплатой "
        "или товар не был начислен, сообщите:\n"
        "1. Ваш Telegram ID;\n"
        "2. название товара;\n"
        "3. дату и время платежа;\n"
        "4. по возможности Telegram payment charge ID."
    )


# ============================================================
# TERMS
# ============================================================

@dp.message(F.text == "/terms")
async def terms(message: Message):
    await message.answer(
        "📄 Условия использования «Грибалки»\n\n"
        "Покупки за Telegram Stars используются "
        "для приобретения цифровых игровых товаров "
        "в приложении «Грибалка».\n\n"
        "После успешной оплаты цифровой товар "
        "начисляется автоматически."
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    bot = Bot(TOKEN)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
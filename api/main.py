import os
import random
from datetime import datetime, timedelta

from dotenv import load_dotenv

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from sqlalchemy.orm import Session

from aiogram import Bot
from aiogram.types import LabeledPrice

from database.database import Base, engine, get_db
from database.models import (
    User,
    UserUpgrade,
    UserBoost,
    Purchase,
    Mushroom,
    Location,
    Catch,
)


# ============================================================
# ENV
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")


# ============================================================
# TELEGRAM BOT
# ============================================================

telegram_bot = Bot(BOT_TOKEN)


# ============================================================
# IMAGES
# ============================================================

MUSHROOM_IMAGES = {
    "Сыроежка зелёная": "/images/mushrooms/green_russula.jpg",
    "Сыроежка пищевая": "/images/mushrooms/food_russula.jpg",
    "Опёнок осенний": "/images/mushrooms/autumn_honey_fungus.jpg",
    "Маслёнок обыкновенный": "/images/mushrooms/butter_mushroom.jpg",
    "Моховик": "/images/mushrooms/moss_mushroom.jpg",
    "Дождевик": "/images/mushrooms/puffball.jpg",
    "Навозник": "/images/mushrooms/ink_cap.jpg",
    "Свинушка": "/images/mushrooms/pig_mushroom.jpg",
    "Волнушка": "/images/mushrooms/woolly_milkcap.jpg",
    "Груздь": "/images/mushrooms/milk_mushroom.jpg",
    "Лисичка": "/images/mushrooms/chanterelle.jpg",
    "Подберёзовик": "/images/mushrooms/birch_bolete.jpg",
    "Подосиновик": "/images/mushrooms/aspen_bolete.jpg",
    "Рядовка": "/images/mushrooms/row_mushroom.jpg",
    "Ежовик гребенчатый": "/images/mushrooms/lion_mane.jpg",
    "Козляк": "/images/mushrooms/goat_mushroom.jpg",
    "Шампиньон лесной": "/images/mushrooms/forest_champignon.jpg",
    "Трутовик": "/images/mushrooms/tinder_fungus.jpg",
    "Белый гриб": "/images/mushrooms/porcini.jpg",
    "Польский гриб": "/images/mushrooms/bay_bolete.jpg",
}


# ============================================================
# DATABASE
# ============================================================

Base.metadata.create_all(engine)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="🍄 Грибалка API",
    version="0.4.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# RARITY
# ============================================================

RARITY_NAMES = {
    "common": "🟢 Обычный",
    "uncommon": "🔵 Необычный",
    "rare": "🟣 Редкий",
}


# ============================================================
# QUALITY
# ============================================================

QUALITY = [
    ("🥀 Плохое", 10, 0.60),
    ("⚪ Обычное", 55, 1.00),
    ("🟢 Хорошее", 25, 1.25),
    ("🔵 Отличное", 8, 1.70),
    ("🟣 Идеальное", 2, 3.00),
]


# ============================================================
# COIN UPGRADES
# ============================================================

UPGRADES = {
    "basket": {
        "name": "🧺 Вместимость корзины",
        "description": "+5 кг к вместимости",
        "base_price": 500,
        "multiplier": 1.8,
    },
    "energy": {
        "name": "⚡ Максимальная энергия",
        "description": "+5 к максимальной энергии",
        "base_price": 700,
        "multiplier": 1.8,
    },
    "tool": {
        "name": "🔎 Инструмент поиска",
        "description": "+10% к шансу редких грибов",
        "base_price": 1000,
        "multiplier": 2.0,
    },
    "luck": {
        "name": "🍀 Удача",
        "description": "Повышает шанс хорошего качества",
        "base_price": 1200,
        "multiplier": 2.0,
    },
}


# ============================================================
# TELEGRAM STARS PRODUCTS
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
# REQUEST MODELS
# ============================================================

class SearchRequest(BaseModel):
    telegram_id: int
    first_name: str = "Грибник"
    username: str | None = None
    location_id: int = 1
    mode: str = "quick"


class BuyUpgradeRequest(BaseModel):
    telegram_id: int
    upgrade_type: str


class BuyStarsProductRequest(BaseModel):
    telegram_id: int
    product_id: str


# ============================================================
# ENERGY
# ============================================================

ENERGY_REGEN_SECONDS = 300


def restore_energy(user):
    now = datetime.utcnow()

    elapsed = now - user.last_energy_update

    units = int(
        elapsed.total_seconds()
        // ENERGY_REGEN_SECONDS
    )

    if units <= 0:
        return

    old_energy = user.energy

    user.energy = min(
        user.max_energy,
        user.energy + units,
    )

    restored = user.energy - old_energy

    if restored > 0:
        user.last_energy_update += timedelta(
            seconds=ENERGY_REGEN_SECONDS * restored
        )
    else:
        user.last_energy_update = now


def get_energy_info(user):
    now = datetime.utcnow()

    if user.energy >= user.max_energy:
        return {
            "energy": user.energy,
            "max_energy": user.max_energy,
            "energy_next_in": 0,
        }

    elapsed_seconds = int(
        (now - user.last_energy_update).total_seconds()
    )

    remaining = (
        ENERGY_REGEN_SECONDS
        - (
            elapsed_seconds
            % ENERGY_REGEN_SECONDS
        )
    )

    if remaining <= 0:
        remaining = ENERGY_REGEN_SECONDS

    return {
        "energy": user.energy,
        "max_energy": user.max_energy,
        "energy_next_in": remaining,
    }


# ============================================================
# USER
# ============================================================

def get_user(
    db,
    telegram_id,
    first_name="Грибник",
    username=None,
):
    user = (
        db.query(User)
        .filter(
            User.telegram_id == telegram_id
        )
        .first()
    )

    if not user:
        user = User(
            telegram_id=telegram_id,
            first_name=first_name or "Грибник",
            username=username,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    else:
        if first_name:
            user.first_name = first_name

        if username is not None:
            user.username = username

    restore_energy(user)

    db.commit()

    return user


# ============================================================
# XP
# ============================================================

def add_xp(user, amount):
    user.xp += amount

    while (
        user.level < 100
        and user.xp >= 100 * user.level * user.level
    ):
        user.level += 1


# ============================================================
# UPGRADES
# ============================================================

def get_upgrade_level(
    db,
    user_id,
    upgrade_type,
):
    upgrade = (
        db.query(UserUpgrade)
        .filter(
            UserUpgrade.user_id == user_id,
            UserUpgrade.upgrade_type == upgrade_type,
        )
        .first()
    )

    if not upgrade:
        return 0

    return upgrade.level


def get_upgrade_price(
    level,
    upgrade_type,
):
    config = UPGRADES[upgrade_type]

    return round(
        config["base_price"]
        * (
            config["multiplier"]
            ** level
        )
    )


# ============================================================
# BOOSTS
# ============================================================

def get_active_boost(
    db,
    user_id,
    boost_type,
):
    now = datetime.utcnow()

    boost = (
        db.query(UserBoost)
        .filter(
            UserBoost.user_id == user_id,
            UserBoost.boost_type == boost_type,
            UserBoost.expires_at > now,
        )
        .order_by(
            UserBoost.expires_at.desc()
        )
        .first()
    )

    return boost


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "game": "mushroom-game",
        "version": "0.4.0",
        "stars": True,
    }


# ============================================================
# USER INFO
# ============================================================

@app.get("/api/user/{telegram_id}")
def user_info(
    telegram_id: int,
    db: Session = Depends(get_db),
):
    user = get_user(
        db,
        telegram_id,
    )

    energy_info = get_energy_info(user)

    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "first_name": user.first_name,
        "level": user.level,
        "xp": user.xp,
        "coins": user.coins,
        "energy": energy_info["energy"],
        "max_energy": energy_info["max_energy"],
        "energy_next_in": energy_info["energy_next_in"],
        "basket_capacity": user.basket_capacity,
        "total_weight": round(
            user.total_weight,
            1,
        ),
    }


# ============================================================
# LOCATIONS
# ============================================================

@app.get("/api/locations/{telegram_id}")
def locations(
    telegram_id: int,
    db: Session = Depends(get_db),
):
    user = get_user(
        db,
        telegram_id,
    )

    output = []

    locations_list = (
        db.query(Location)
        .filter(
            Location.active == True
        )
        .order_by(Location.id)
        .all()
    )

    for location in locations_list:

        unlocked = (
            location.id == 1
            or user.level >= location.required_level
        )

        output.append({
            "id": location.id,
            "name": location.name,
            "description": location.description,
            "required_level": location.required_level,
            "unlock_price": location.unlock_price,
            "unlocked": unlocked,
        })

    return output


# ============================================================
# SEARCH
# ============================================================

@app.post("/api/search")
def search(
    req: SearchRequest,
    db: Session = Depends(get_db),
):
    user = get_user(
        db,
        req.telegram_id,
        req.first_name,
        req.username,
    )

    location = (
        db.query(Location)
        .filter(
            Location.id == req.location_id,
            Location.active == True,
        )
        .first()
    )

    if not location:
        raise HTTPException(
            404,
            "Локация не найдена",
        )

    if user.level < location.required_level:
        raise HTTPException(
            400,
            "Локация ещё не открыта",
        )

    search_costs = {
        "quick": 1,
        "careful": 2,
        "expedition": 5,
    }

    search_cost = search_costs.get(
        req.mode
    )

    if search_cost is None:
        raise HTTPException(
            400,
            "Неизвестный режим поиска",
        )

    if user.energy < search_cost:
        raise HTTPException(
            400,
            "Недостаточно энергии",
        )

    if user.total_weight >= user.basket_capacity:
        raise HTTPException(
            400,
            "Корзина заполнена",
        )

    mushrooms = (
        db.query(Mushroom)
        .filter(
            Mushroom.location_id == location.id,
            Mushroom.active == True,
        )
        .all()
    )

    if not mushrooms:
        raise HTTPException(
            500,
            "В локации нет грибов",
        )

    user.energy -= search_cost

    tool_level = get_upgrade_level(
        db,
        user.id,
        "tool",
    )

    rare_multiplier = (
        1.0
        + tool_level * 0.10
    )

    if req.mode == "careful":
        rare_multiplier *= 1.25

    elif req.mode == "expedition":
        rare_multiplier *= 1.50

    search_boost = get_active_boost(
        db,
        user.id,
        "search",
    )

    if search_boost:
        rare_multiplier *= search_boost.value

    weights = []

    for mushroom in mushrooms:

        weight = mushroom.chance

        if mushroom.rarity == "rare":
            weight *= rare_multiplier

        weights.append(weight)

    mushroom = random.choices(
        mushrooms,
        weights=weights,
        k=1,
    )[0]

    weight = random.randint(
        mushroom.min_weight,
        mushroom.max_weight,
    )

    # --------------------------------------------------------
    # QUALITY
    # --------------------------------------------------------

    luck_level = get_upgrade_level(
        db,
        user.id,
        "luck",
    )

    quality_weights = [
        q[1]
        for q in QUALITY
    ]

    if luck_level > 0:

        quality_weights[0] = max(
            1,
            quality_weights[0]
            - luck_level * 2,
        )

        quality_weights[1] = max(
            1,
            quality_weights[1]
            - luck_level,
        )

        quality_weights[2] += (
            luck_level * 2
        )

    luck_boost = get_active_boost(
        db,
        user.id,
        "luck",
    )

    if luck_boost:

        quality_weights[0] = max(
            1,
            quality_weights[0] - 5,
        )

        quality_weights[1] = max(
            1,
            quality_weights[1] - 5,
        )

        quality_weights[2] += 5

    quality, _, multiplier = random.choices(
        QUALITY,
        weights=quality_weights,
        k=1,
    )[0]

    # --------------------------------------------------------
    # BASKET
    # --------------------------------------------------------

    available_grams = max(
        0,
        (
            user.basket_capacity
            - user.total_weight
        ) * 1000,
    )

    weight = min(
        weight,
        available_grams,
    )

    if weight < 1:
        raise HTTPException(
            400,
            "В корзине недостаточно места",
        )

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    price = max(
        1,
        round(
            weight
            / 100
            * mushroom.price_100g
            * multiplier
        ),
    )

    xp = mushroom.xp

    before_count = (
        db.query(Catch)
        .filter(
            Catch.user_id == user.id
        )
        .count()
    )

    user.total_weight += (
        weight / 1000
    )

    add_xp(
        user,
        xp,
    )

    catch = Catch(
        user_id=user.id,
        mushroom_id=mushroom.id,
        location_id=location.id,
        weight=weight,
        quality=quality,
        price=price,
        xp=xp,
    )

    db.add(catch)

    db.commit()

    energy_info = get_energy_info(
        user
    )

    return {
        "mushroom": mushroom.name,
        "image": MUSHROOM_IMAGES.get(
            mushroom.name,
            "",
        ),
        "rarity": RARITY_NAMES.get(
            mushroom.rarity,
            mushroom.rarity,
        ),
        "quality": quality,
        "weight": weight,
        "price": price,
        "xp": xp,
        "level": user.level,
        "energy": energy_info["energy"],
        "max_energy": energy_info["max_energy"],
        "energy_next_in": energy_info["energy_next_in"],
        "total_weight": round(
            user.total_weight,
            1,
        ),
        "new_find": before_count == 0,
    }


# ============================================================
# INVENTORY
# ============================================================

@app.get("/api/inventory/{telegram_id}")
def inventory(
    telegram_id: int,
    db: Session = Depends(get_db),
):
    user = get_user(
        db,
        telegram_id,
    )

    catches = (
        db.query(Catch)
        .filter(
            Catch.user_id == user.id,
            Catch.sold == False,
        )
        .all()
    )

    items = []

    for catch in catches:

        mushroom = (
            db.query(Mushroom)
            .filter(
                Mushroom.id
                == catch.mushroom_id
            )
            .first()
        )

        items.append({
            "id": catch.id,
            "name": mushroom.name,
            "image": MUSHROOM_IMAGES.get(
                mushroom.name,
                "",
            ),
            "rarity": mushroom.rarity,
            "weight": catch.weight,
            "quality": catch.quality,
            "price": catch.price,
        })

    return {
        "items": items,
        "total_weight": round(
            user.total_weight,
            1,
        ),
        "capacity": user.basket_capacity,
    }


# ============================================================
# SELL ALL
# ============================================================

@app.post("/api/sell-all/{telegram_id}")
def sell_all(
    telegram_id: int,
    db: Session = Depends(get_db),
):
    user = get_user(
        db,
        telegram_id,
    )

    catches = (
        db.query(Catch)
        .filter(
            Catch.user_id == user.id,
            Catch.sold == False,
        )
        .all()
    )

    total = sum(
        catch.price
        for catch in catches
    )

    for catch in catches:
        catch.sold = True

    user.coins += total
    user.total_weight = 0

    db.commit()

    return {
        "sold": len(catches),
        "coins": total,
        "balance": user.coins,
    }


# ============================================================
# SHOP
# ============================================================

@app.get("/api/shop/{telegram_id}")
def shop(
    telegram_id: int,
    db: Session = Depends(get_db),
):
    user = get_user(
        db,
        telegram_id,
    )

    # --------------------------------------------------------
    # COIN PRODUCTS
    # --------------------------------------------------------

    coin_products = []

    for upgrade_type, config in UPGRADES.items():

        level = get_upgrade_level(
            db,
            user.id,
            upgrade_type,
        )

        price = get_upgrade_price(
            level,
            upgrade_type,
        )

        coin_products.append({
            "id": upgrade_type,
            "name": config["name"],
            "description": config["description"],
            "level": level,
            "price": price,
            "currency": "coins",
        })

    # --------------------------------------------------------
    # STARS PRODUCTS
    # --------------------------------------------------------

    stars_products = []

    for product_id, product in STARS_PRODUCTS.items():

        stars_products.append({
            "id": product_id,
            "name": product["name"],
            "description": product["description"],
            "price": product["stars"],
            "currency": "stars",
        })

    return {
        "coins": coin_products,
        "stars": stars_products,
        "balance": user.coins,
    }


# ============================================================
# BUY COIN UPGRADE
# ============================================================

@app.post("/api/shop/buy")
def buy_upgrade(
    req: BuyUpgradeRequest,
    db: Session = Depends(get_db),
):
    if req.upgrade_type not in UPGRADES:
        raise HTTPException(
            400,
            "Неизвестное улучшение",
        )

    user = get_user(
        db,
        req.telegram_id,
    )

    level = get_upgrade_level(
        db,
        user.id,
        req.upgrade_type,
    )

    price = get_upgrade_price(
        level,
        req.upgrade_type,
    )

    if user.coins < price:
        raise HTTPException(
            400,
            "Недостаточно монет",
        )

    upgrade = (
        db.query(UserUpgrade)
        .filter(
            UserUpgrade.user_id == user.id,
            UserUpgrade.upgrade_type
            == req.upgrade_type,
        )
        .first()
    )

    if not upgrade:

        upgrade = UserUpgrade(
            user_id=user.id,
            upgrade_type=req.upgrade_type,
            level=0,
        )

        db.add(upgrade)

    user.coins -= price
    upgrade.level += 1

    if req.upgrade_type == "basket":

        user.basket_capacity += 5

    elif req.upgrade_type == "energy":

        user.max_energy += 5
        user.energy += 5

    db.commit()

    return {
        "success": True,
        "upgrade": req.upgrade_type,
        "level": upgrade.level,
        "price": price,
        "coins": user.coins,
        "basket_capacity": user.basket_capacity,
        "energy": user.energy,
        "max_energy": user.max_energy,
    }


# ============================================================
# TELEGRAM STARS — CREATE REAL INVOICE
# ============================================================

@app.post("/api/stars/create-invoice")
async def create_stars_invoice(
    req: BuyStarsProductRequest,
    db: Session = Depends(get_db),
):
    """
    Создание настоящего Telegram Stars invoice.

    Mini App вызывает этот endpoint.
    FastAPI обращается к Telegram Bot API.
    Telegram возвращает invoice_link.
    """

    # --------------------------------------------------------
    # Проверяем товар
    # --------------------------------------------------------

    if req.product_id not in STARS_PRODUCTS:
        raise HTTPException(
            400,
            "Неизвестный товар",
        )

    product = STARS_PRODUCTS[
        req.product_id
    ]

    # --------------------------------------------------------
    # Проверяем / создаём пользователя
    # --------------------------------------------------------

    user = get_user(
        db,
        req.telegram_id,
    )

    # --------------------------------------------------------
    # Payload
    #
    # mushroom:TELEGRAM_ID:PRODUCT_ID
    # --------------------------------------------------------

    payload = (
        f"mushroom:"
        f"{user.telegram_id}:"
        f"{req.product_id}"
    )

    # --------------------------------------------------------
    # Создаём Telegram invoice
    # --------------------------------------------------------

    try:

        invoice_link = (
            await telegram_bot.create_invoice_link(
                title=product["name"],
                description=product["description"],
                payload=payload,
                currency="XTR",
                prices=[
                    LabeledPrice(
                        label=product["name"],
                        amount=product["stars"],
                    )
                ],
            )
        )

    except Exception as e:

        print(
            "Telegram invoice error:",
            repr(e),
        )

        raise HTTPException(
            500,
            "Не удалось создать счёт Telegram Stars",
        )

    return {
        "success": True,
        "product_id": req.product_id,
        "name": product["name"],
        "description": product["description"],
        "stars": product["stars"],
        "invoice_link": invoice_link,
    }


# ============================================================
# TELEGRAM STARS — TEST PURCHASE
#
# Оставляем для разработки.
# В настоящей оплате этот endpoint НЕ используется.
# ============================================================

@app.post("/api/stars/test-buy")
def test_stars_buy(
    req: BuyStarsProductRequest,
    db: Session = Depends(get_db),
):
    if req.product_id not in STARS_PRODUCTS:
        raise HTTPException(
            400,
            "Неизвестный товар",
        )

    product = STARS_PRODUCTS[
        req.product_id
    ]

    user = get_user(
        db,
        req.telegram_id,
    )

    test_charge_id = (
        f"TEST-"
        f"{user.id}-"
        f"{req.product_id}-"
        f"{datetime.utcnow().timestamp()}"
    )

    purchase = Purchase(
        user_id=user.id,
        product_id=req.product_id,
        stars=product["stars"],
        telegram_payment_charge_id=test_charge_id,
        status="test_successful",
    )

    db.add(purchase)

    # --------------------------------------------------------
    # APPLY PRODUCT
    # --------------------------------------------------------

    if req.product_id == "energy_10":

        user.energy = min(
            user.max_energy,
            user.energy + 10,
        )

    elif req.product_id == "energy_full":

        user.energy = user.max_energy

    elif req.product_id == "basket_10":

        user.basket_capacity += 10

    elif req.product_id == "luck_1h":

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

    elif req.product_id == "search_1h":

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

    elif req.product_id == "starter_pack":

        user.energy = min(
            user.max_energy,
            user.energy + 20,
        )

        user.basket_capacity += 5
        user.coins += 1000

    db.commit()

    energy_info = get_energy_info(
        user
    )

    return {
        "success": True,
        "product_id": req.product_id,
        "product_name": product["name"],
        "stars": product["stars"],
        "status": "test_successful",
        "coins": user.coins,
        "energy": energy_info["energy"],
        "max_energy": energy_info["max_energy"],
        "energy_next_in": energy_info["energy_next_in"],
        "basket_capacity": user.basket_capacity,
    }


# ============================================================
# LEADERBOARD
# ============================================================

@app.get("/api/leaderboard")
def leaderboard(
    db: Session = Depends(get_db),
):
    users = (
        db.query(User)
        .order_by(
            User.level.desc(),
            User.xp.desc(),
        )
        .limit(20)
        .all()
    )

    return [
        {
            "place": i + 1,
            "name": user.first_name,
            "level": user.level,
            "xp": user.xp,
        }
        for i, user in enumerate(users)
    ]


# ============================================================
# STATIC WEBAPP
# ============================================================

app.mount(
    "/",
    StaticFiles(
        directory="webapp",
        html=True,
    ),
    name="webapp",
)
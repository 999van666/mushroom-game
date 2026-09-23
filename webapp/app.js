const tg = window.Telegram?.WebApp;

if (tg) {
    tg.ready();
    tg.expand();
}

const API = "";

let telegramId = 100000001;

if (tg?.initDataUnsafe?.user?.id) {
    telegramId = tg.initDataUnsafe.user.id;
}

let energyTimer = null;
let energySeconds = 0;
let currentEnergy = 0;
let currentMaxEnergy = 0;


// ===============================
// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// ===============================

function formatTime(seconds) {
    seconds = Math.max(0, Math.floor(seconds));

    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;

    return (
        String(minutes).padStart(2, "0") +
        ":" +
        String(secs).padStart(2, "0")
    );
}


function updateEnergyDisplay() {
    const energyElement = document.getElementById("energy");
    const maxEnergyElement = document.getElementById("maxEnergy");
    const timerElement = document.getElementById("energy-timer");

    if (energyElement) {
        energyElement.textContent = currentEnergy;
    }

    if (maxEnergyElement) {
        maxEnergyElement.textContent = currentMaxEnergy;
    }

    if (!timerElement) {
        return;
    }

    if (currentEnergy >= currentMaxEnergy) {
        timerElement.textContent = "Энергия восстановлена";
    } else {
        timerElement.textContent =
            "+1 через " + formatTime(energySeconds);
    }
}


function startEnergyTimer(seconds) {
    if (energyTimer) {
        clearInterval(energyTimer);
        energyTimer = null;
    }

    energySeconds = Math.max(0, Number(seconds) || 0);

    updateEnergyDisplay();

    if (energySeconds <= 0 || currentEnergy >= currentMaxEnergy) {
        return;
    }

    energyTimer = setInterval(() => {

        if (energySeconds > 0) {
            energySeconds--;
        }

        updateEnergyDisplay();

        if (energySeconds <= 0) {
            clearInterval(energyTimer);
            energyTimer = null;

            // Получаем актуальное состояние с сервера
            refresh();
        }

    }, 1000);
}


function showMessage(text) {
    alert(text);
}


// ===============================
// ЗАГРУЗКА ДАННЫХ ПОЛЬЗОВАТЕЛЯ
// ===============================

async function refresh() {
    try {
        const response = await fetch(
            `${API}/api/user/${telegramId}`
        );

        if (!response.ok) {
            throw new Error("Ошибка загрузки пользователя");
        }

        const user = await response.json();

        // Шапка
        const hello = document.getElementById("hello");
        const coins = document.getElementById("coins");
        const level = document.getElementById("level");
        const weight = document.getElementById("weight");
        const capacity = document.getElementById("capacity");

        if (hello) {
            hello.textContent = user.first_name || "Грибник";
        }

        if (coins) {
            coins.textContent = user.coins;
        }

        if (level) {
            level.textContent = user.level;
        }

        if (weight) {
            weight.textContent =
                Number(user.total_weight || 0).toFixed(1);
        }

        if (capacity) {
            capacity.textContent =
                Number(user.basket_capacity || 0).toFixed(1);
        }

        // Энергия
        currentEnergy = Number(user.energy || 0);
        currentMaxEnergy = Number(user.max_energy || 0);

        startEnergyTimer(user.energy_next_in || 0);

    } catch (error) {
        console.error(error);
    }
}


// ===============================
// ЛЕС
// ===============================

function showForest() {

    const screen = document.getElementById("screen");

    screen.innerHTML = `
        <div class="card">
            <h2>🌳 Берёзовая роща</h2>

            <p>
                Здесь можно найти обычные и редкие грибы.
            </p>

            <div class="search-buttons">

                <button class="main-btn"
                        onclick="searchMushroom('quick')">
                    👀 Быстрый поиск
                    <small>1 ⚡</small>
                </button>

                <button class="main-btn"
                        onclick="searchMushroom('careful')">
                    🔎 Тщательный поиск
                    <small>2 ⚡ · +25% к редкости</small>
                </button>

                <button class="main-btn"
                        onclick="searchMushroom('expedition')">
                    🧭 Экспедиция
                    <small>5 ⚡ · +50% к редкости</small>
                </button>

            </div>

            <div id="search-result"></div>
        </div>
    `;
}


// ===============================
// ПОИСК ГРИБА
// ===============================

async function searchMushroom(mode) {

    const result = document.getElementById("search-result");

    if (!result) {
        return;
    }

    result.innerHTML = `
        <div class="card">
            🍄 Ищем грибы...
        </div>
    `;

    try {

        const response = await fetch(
            `${API}/api/search`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    telegram_id: telegramId,
                    location_id: 1,
                    mode: mode
                })
            }
        );

        const data = await response.json();

        console.log("Ответ /api/search:", data);

        if (!response.ok) {

            result.innerHTML = `
                <div class="card">
                    ❌ ${data.detail || "Не удалось выполнить поиск"}
                </div>
            `;

            await refresh();

            return;
        }


        // =====================================
        // ОБНОВЛЯЕМ ЭНЕРГИЮ
        // =====================================

        currentEnergy = Number(data.energy || 0);

        if (currentEnergy < currentMaxEnergy) {
            startEnergyTimer(300);
        } else {
            startEnergyTimer(0);
        }


        // =====================================
        // ФОТОГРАФИЯ ГРИБА
        // =====================================

        let mushroomImage = "";

        if (data.image) {

            mushroomImage = `
                <div style="
                    width:100%;
                    max-width:320px;
                    margin:0 auto 15px auto;
                    border-radius:16px;
                    overflow:hidden;
                    background:#f2f2f2;
                ">
                    <img
                        src="${data.image}"
                        alt="${data.mushroom || "Гриб"}"
                        style="
                            display:block;
                            width:100%;
                            height:220px;
                            object-fit:cover;
                        "
                    >
                </div>
            `;

        } else {

            mushroomImage = `
                <div style="
                    font-size:60px;
                    text-align:center;
                    margin-bottom:10px;
                ">
                    🍄
                </div>
            `;
        }


        // =====================================
        // ОТОБРАЖАЕМ НАЙДЕННЫЙ ГРИБ
        // =====================================

        result.innerHTML = `
            <div class="card mushroom-result">

                ${mushroomImage}

                <h2>
                    ${data.mushroom || "Гриб"}
                </h2>

                <p>
                    ${data.rarity || ""}
                </p>

                <p>
                    Качество:
                    <b>
                        ${data.quality || ""}
                    </b>
                </p>

                <p>
                    ⚖️ Вес:
                    <b>
                        ${Number(data.weight || 0)} г
                    </b>
                </p>

                <p>
                    💰 Цена:
                    <b>
                        ${Number(data.price || 0)} 🪙
                    </b>
                </p>

                <p>
                    ⭐ Опыт:
                    <b>
                        +${Number(data.xp || 0)} XP
                    </b>
                </p>

                <button
                    class="main-btn"
                    onclick="showForest()"
                >
                    🍄 Искать ещё
                </button>

            </div>
        `;


        // Получаем актуальные данные пользователя
        await refresh();

    } catch (error) {

        console.error(
            "Ошибка поиска:",
            error
        );

        result.innerHTML = `
            <div class="card">
                ❌ Ошибка соединения с сервером
            </div>
        `;
    }
}

// ===============================
// КОРЗИНА
// ===============================

async function showInventory() {
    const screen = document.getElementById("screen");

    screen.innerHTML = `
        <div class="card">
            <h2>🎒 Корзина</h2>
            <p>Загрузка...</p>
        </div>
    `;

    try {
        const response = await fetch(`${API}/api/inventory/${telegramId}`);

        if (!response.ok) {
            throw new Error("Ошибка загрузки корзины");
        }

        const data = await response.json();

        console.log("Корзина:", data);

        let html = `
            <div class="card">
                <h2>🎒 Корзина</h2>

                <p>
                    Вес:
                    <b>${Number(data.total_weight || 0).toFixed(1)}</b>
                    /
                    ${Number(data.capacity || 0).toFixed(1)} кг
                </p>
        `;

        if (!data.items || data.items.length === 0) {
            html += `
                <p style="text-align:center; padding:20px 0;">
                    🎒 Корзина пуста
                </p>
            `;
        } else {

            html += `
                <div style="margin-top:15px;">
            `;

            data.items.forEach(item => {

    const image = item.image
        ? `
            <img
                src="${item.image}"
                alt="${item.name || "Гриб"}"
                style="
                    width:80px;
                    height:80px;
                    object-fit:cover;
                    border-radius:12px;
                    flex-shrink:0;
                "
            >
        `
        : `
            <div style="
                width:80px;
                height:80px;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:40px;
                flex-shrink:0;
            ">
                🍄
            </div>
        `;

    html += `
        <div
            class="shop-item"
            style="
                display:flex;
                align-items:center;
                gap:12px;
            "
        >

            ${image}

            <div>
                <b>
                    ${item.name}
                </b>

                <br>

                <small>
                    ${item.quality}
                    · ${Number(item.weight || 0).toFixed(0)} г
                    · 💰 ${Number(item.price || 0)}
                </small>
            </div>

        </div>
    `;
});

            html += `
                </div>

                <button
                    class="main-btn"
                    onclick="sellAll()"
                    style="margin-top:15px;"
                >
                    💰 Продать всё
                </button>
            `;
        }

        html += `</div>`;

        screen.innerHTML = html;

    } catch (error) {
        console.error("Ошибка корзины:", error);

        screen.innerHTML = `
            <div class="card">
                <h2>🎒 Корзина</h2>
                <p>❌ Не удалось загрузить корзину</p>
            </div>
        `;
    }
}


// ===============================
// ПРОДАЖА
// ===============================

async function sellAll() {
    try {
        const response = await fetch(
            `${API}/api/sell-all/${telegramId}`,
            {
                method: "POST"
            }
        );

        const data = await response.json();

        console.log("Продажа:", data);

        if (!response.ok) {
            alert(data.detail || "Не удалось продать грибы");
            return;
        }

        alert(
            `💰 Продано грибов: ${data.sold}\n` +
            `Получено: ${data.coins} 🪙\n` +
            `Баланс: ${data.balance} 🪙`
        );

        // Обновляем верхнюю панель
        await refresh();

        // Сразу перерисовываем корзину
        await showInventory();

    } catch (error) {
        console.error("Ошибка продажи:", error);

        alert("❌ Ошибка соединения с сервером");
    }
}


// ===============================
// МАГАЗИН
// ===============================

async function showShop() {

    const screen = document.getElementById("screen");

    screen.innerHTML = `
        <div class="card">
            <h2>🛒 Магазин</h2>
            <p>Загрузка...</p>
        </div>
    `;

    try {

        const response = await fetch(
            `${API}/api/shop/${telegramId}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Ошибка магазина"
            );
        }

        let html = `
            <div class="card">

                <h2>🛒 Магазин</h2>

                <p>
                    💰 Ваш баланс:
                    <b>${Number(data.balance || 0)}</b>
                </p>

                <h3>⚡ Улучшения за монеты</h3>
        `;

        for (const item of data.coins || []) {

            html += `
                <div class="shop-item">

                    <div>

                        <b>
                            ${item.name}
                        </b>

                        <br>

                        <small>
                            ${item.description || ""}
                        </small>

                        <br>

                        <small>
                            Уровень:
                            ${Number(item.level || 0)}
                        </small>

                    </div>

                    <button
                        class="buy-btn"
                        onclick="buyUpgrade('${item.id}')"
                    >
                        💰 ${Number(item.price || 0)}
                    </button>

                </div>
            `;
        }

        html += `
                <h3>⭐ Telegram Stars</h3>
        `;

        for (const item of data.stars || []) {

            html += `
                <div class="shop-item">

                    <div>

                        <b>
                            ${item.name}
                        </b>

                        <br>

                        <small>
                            ${item.description || ""}
                        </small>

                    </div>

                    <button
                        class="buy-btn"
                        onclick="buyStars('${item.id}')"
                    >
                        ⭐ ${Number(item.price || 0)}
                    </button>

                </div>
            `;
        }

        html += `
            </div>
        `;

        screen.innerHTML = html;

    } catch (error) {

        console.error("Ошибка магазина:", error);

        screen.innerHTML = `
            <div class="card">
                <h2>🛒 Магазин</h2>
                <p>❌ Не удалось загрузить магазин</p>
            </div>
        `;
    }
}

// ===============================
// ПОКУПКА УЛУЧШЕНИЯ
// ===============================

async function buyUpgrade(upgradeType) {

    try {

        const response = await fetch(
            `${API}/api/shop/buy`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    telegram_id: telegramId,
                    upgrade_type: upgradeType
                })
            }
        );

        const data = await response.json();

        console.log("Покупка улучшения:", data);

        if (!response.ok) {

            showMessage(
                data.detail || "Покупка не выполнена"
            );

            return;
        }

        showMessage(
            `✅ Улучшение куплено!\n\n` +
            `Уровень: ${data.level}\n` +
            `💰 Потрачено: ${data.price}\n` +
            `💰 Осталось: ${data.coins}`
        );

        await refresh();

        await showShop();

    } catch (error) {

        console.error(
            "Ошибка покупки:",
            error
        );

        showMessage(
            "❌ Ошибка соединения с сервером"
        );
    }
}


// ===============================
// TELEGRAM STARS
// ===============================

async function buyStars(productId) {

    try {

        const response = await fetch(
            `${API}/api/stars/create-invoice`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    telegram_id: telegramId,
                    product_id: productId
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {

            showMessage(
                data.detail || "Не удалось создать платёж"
            );

            return;
        }


        /*
         * Здесь будет открываться настоящий
         * Telegram Stars invoice.
         *
         * Пока backend содержит тестовую
         * реализацию платежей.
         */

        if (data.invoice_link && tg) {

            tg.openInvoice(
                data.invoice_link,
                function(status) {

                    if (status === "paid") {

                        showMessage(
                            "⭐ Покупка успешно оплачена!"
                        );

                        refresh();
                        showShop();
                    }

                }
            );

        } else {

            showMessage(
                data.message ||
                "Платёжная система пока находится в тестовом режиме."
            );
        }

    } catch (error) {

        console.error(error);

        showMessage(
            "Ошибка создания платежа"
        );
    }
}


// ===============================
// ПРОФИЛЬ
// ===============================

async function showProfile() {

    const screen = document.getElementById("screen");

    screen.innerHTML = `
        <div class="card">
            <h2>👤 Профиль</h2>
            <p>Загрузка...</p>
        </div>
    `;


    try {

        const response = await fetch(
            `${API}/api/user/${telegramId}`
        );

        const user = await response.json();

        if (!response.ok) {
            throw new Error("Ошибка профиля");
        }


        screen.innerHTML = `
            <div class="card">

                <h2>👤 ${user.first_name || "Грибник"}</h2>

                <p>
                    ⭐ Уровень:
                    <b>${user.level}</b>
                </p>

                <p>
                    ✨ Опыт:
                    <b>${user.xp}</b>
                </p>

                <p>
                    💰 Монеты:
                    <b>${user.coins}</b>
                </p>

                <p>
                    ⚡ Энергия:
                    <b>
                        ${user.energy}/${user.max_energy}
                    </b>
                </p>

                <p>
                    🎒 Корзина:
                    <b>
                        ${Number(user.total_weight || 0).toFixed(1)}
                        /
                        ${Number(user.basket_capacity || 0).toFixed(1)}
                        кг
                    </b>
                </p>

            </div>
        `;

    } catch (error) {

        console.error(error);

        screen.innerHTML = `
            <div class="card">
                ❌ Не удалось загрузить профиль
            </div>
        `;
    }
}


// ===============================
// ЗАПУСК
// ===============================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        refresh();
        showForest();

    }
);
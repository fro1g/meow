# Telegram Bot (tg_bot_visitka)

Этот проект представляет собой Telegram-бота, написанного на Python с использованием библиотеки `pyTelegramBotAPI`. Бот упакован в Docker для удобного развертывания.

## 📌 Требования
Перед началом убедитесь, что у вас установлены:
- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)
- Telegram-бот и его токен (получить через [BotFather](https://t.me/botfather))

## 🚀 Установка и запуск

### 1️⃣ Клонирование репозитория
Склонируйте этот репозиторий на свой компьютер:
```bash
git clone https://github.com/fro1g/meow.git
cd tg_bot_visitka
```

### 2️⃣ Сборка и запуск контейнера
Соберите и запустите контейнер с ботом:
```bash
docker-compose up --build -d
```
Флаг `-d` запускает контейнер в фоновом режиме.

### 3️⃣ Проверка работы бота
Бот запущен, если он отвечает в Telegram. Вы можете проверить это, перейдя по ссылке:
[🔗 Запустить бота](t.me/anastasiya_mitkina_bot)



## 🔄 Управление контейнером
- **Остановить бота:**
  ```bash
  docker-compose down
  ```
- **Перезапустить бота:**
  ```bash
  docker-compose restart
  ```
- **Запустить контейнер заново:**
  ```bash
  docker-compose up -d
  ```

## 🛠 Разработка и тестирование
Если хотите изменить код бота и протестировать без Docker, установите зависимости вручную:
```bash
pip install -r requirements.txt
python main.py
```
**Важно:** Токен бота должен быть указан в файле `main.py`.

## 📜 Лицензия
Этот проект распространяется под лицензией MIT.

---

Теперь ваш Telegram-бот готов к использованию! 🎉


# Быстрый старт

## Установка

Скачайте установочный скрипт:

```bash
curl -O https://raw.githubusercontent.com/blasterss/vpn_bot/main/install.sh
chmod +x install.sh
```

Запустите установку:

```bash
sudo ./install.sh
```

---

## Что делает установщик

Во время установки автоматически выполняется:

1. Установка системных зависимостей:

   * git
   * python3
   * python3-full

2. Клонирование репозитория проекта

3. Создание Python virtual environment (`.venv`)

4. Установка Python-зависимостей из `requirements.txt`

5. Создание файла `.env`

   * ввод Telegram Bot Token
   * ввод секретного кода администратора

6. Настройка `sudoers`

   * бот получает возможность безопасно выполнять `openvpn-install.sh`
   * пароль sudo для этого скрипта не требуется

7. Создание systemd unit:

   * `vpn_bot.service`

8. Запуск и автозапуск Telegram-бота

---

## Требования

Перед установкой необходимо:

* установленный и настроенный OpenVPN сервер
* файл `openvpn-install.sh` в домашней директории пользователя

Например:

```bash
/home/ubuntu/openvpn-install.sh
```

Скрипт должен быть исполняемым:

```bash
chmod +x ~/openvpn-install.sh
```

---

## Проверка работы бота

Просмотр логов:

```bash
sudo journalctl -u vpn_bot.service -n 200 --no-pager
```

Онлайн просмотр логов:

```bash
sudo journalctl -u vpn_bot.service -f
```

Проверка статуса:

```bash
sudo systemctl status vpn_bot.service
```

---

## Управление ботом

Остановить бота:

```bash
sudo systemctl stop vpn_bot.service
```

Запустить бота:

```bash
sudo systemctl start vpn_bot.service
```

Перезапустить бота:

```bash
sudo systemctl restart vpn_bot.service
```

---

## Telegram команды

### `/start`

Запуск бота и отображение приветственного сообщения.

---

### `/getvpn`

Создание персональной OpenVPN-конфигурации.

Бот:

* создаёт VPN-клиента
* генерирует `.ovpn`
* отправляет конфигурацию пользователю

---

### `/help`

Показывает инструкцию по подключению VPN.

---

### `/__secure_server_activity`

Команда администратора для просмотра активности VPN-сервера.

Требует ввод секретного кода, заданного во время установки.

---

## Архитектура запуска

Бот работает как обычный пользователь через systemd.

Для создания VPN-конфигураций используется:

```bash
sudo openvpn-install.sh
```

Через автоматически настроенный `sudoers`.

Это позволяет:

* не запускать Telegram-бота от root
* безопасно выдавать VPN-конфигурации
* ограничить sudo только одним скриптом

---

## Dev блок 

### 🤖 Смена Telegram-бота

Обновить токен в `.env`:

```bash
sudo nano ~/vpn_bot/.env
```

Измените строку:

```
BOT_TOKEN=NEW_TOKEN
```

Перезапуск бота:

```bash
sudo systemctl restart vpn_bot.service
```

---

### 🔧 Изменение кода бота

Код бота находится в:

```bash
~/vpn_bot/src/bot.py
```

Обновить код:

```bash
sudo nano ~/vpn_bot/src/bot.py
```

После любых изменений в коде необходимо перезапустить бота:

```bash
sudo systemctl restart vpn_bot.service
```

---

## Удаление

Остановка сервиса:

```bash
sudo systemctl stop vpn_bot.service
```

Удаление systemd unit:

```bash
sudo rm /etc/systemd/system/vpn_bot.service
sudo systemctl daemon-reload
```

Удаление проекта:

```bash
rm -rf ~/vpn_bot
```

Удаление sudoers rules:

```bash
sudo rm /etc/sudoers.d/vpn_bot
```

---

## Репозиторий

https://github.com/blasterss/vpn_bot

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

   * бот получает возможность выполнять обнаруженные `openvpn-install.sh` и `wireguard-install.sh`
   * пароль sudo для этого скрипта не требуется

7. Создание systemd unit:

   * `vpn_bot.service`

8. Запуск и автозапуск Telegram-бота

---

## Требования

Перед установкой необходимо:

* установленный и настроенный OpenVPN и/или WireGuard сервер
* исполняемый `openvpn-install.sh` и/или `wireguard-install.sh` в домашней директории пользователя

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

### `/getopenvpn`

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
* ограничить sudo обнаруженными VPN-скриптами

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

## WireGuard и настройки

Поддерживается интерактивный [скрипт angristan](https://github.com/angristan/wireguard-install).
Сначала установите и настройте сервер этим скриптом вручную. Бот добавляет клиентов
через меню уже установленного сервера, принимая предложенные IPv4/IPv6.
Команда `/getwireguard` выдаёт `.conf`, который нужно импортировать в приложение WireGuard.
Запросы создания клиентов выполняются последовательно, чтобы не выделить один IP дважды.
Вывод скрипта с QR-кодом не записывается в журнал.

Установщик обнаруживает оба скрипта независимо. Отсутствующий скрипт не мешает
запуску бота; его команда сообщает о недоступности VPN. `/getvpn` переименована в `/getopenvpn`.
Команда администратора проверяет OpenVPN; без него сообщает, что он не настроен.

Для ручной настройки скопируйте `.env.example` в `.env`:

| Переменная | Значение |
| --- | --- |
| `SCRIPT_PATH` | Путь к OpenVPN-скрипту с командами `client add` и `server status`; можно оставить пустым |
| `WORKING_DIR` | Рабочая директория, по умолчанию домашняя директория пользователя |
| `WIREGUARD_SCRIPT_PATH` | Путь к `wireguard-install.sh`; можно оставить пустым |
| `WIREGUARD_INTERFACE` | Имя интерфейса из `/etc/wireguard/params`, по умолчанию `wg0` |
| `WIREGUARD_CONFIG_DIR` | Каталог файлов `wg0-client-<имя>.conf`, по умолчанию `WORKING_DIR` |

angristan обычно сохраняет конфиги в `/home/$SUDO_USER`. Пользователь бота должен
иметь доступ на чтение и удаление файлов в этом каталоге. Для существующей установки
добавьте путь к WireGuard-скрипту в `/etc/sudoers.d/vpn_bot` через `sudo visudo -f /etc/sudoers.d/vpn_bot`:

```sudoers
ubuntu ALL=(root) NOPASSWD: /home/ubuntu/wireguard-install.sh
```

Замените пользователя и путь своими значениями, заполните `.env` и перезапустите сервис.

## Разработка

Зависимости объявлены в `pyproject.toml`; `requirements.txt` устанавливает проект из него.
Неиспользуемые зависимости прежнего бота убраны. Ruff устанавливается вместе с проектом.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ruff check .
ruff format --check .
python -m unittest discover -s tests -v
```

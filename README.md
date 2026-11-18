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

## Автоматическое обновление AllowedIPs WireGuard

`scripts/update_wireguard_ips.py` загружает [список IPv4](https://gist.githubusercontent.com/iamwildtuna/7772b7c84a11bf6e1385f23096a73a15/raw/gistfile2.txt),
проверяет адреса и подсети, добавляет `/32` одиночным адресам и удаляет дубли.
Затем атомарно заменяет только строку `ALLOWED_IPS` в `/etc/wireguard/params`,
сохраняя права и владельца. Ошибка загрузки, пустой список или некорректный IP
прерывают обновление. Остальные настройки и ключи остаются в файле.

Список заменяет прежний `ALLOWED_IPS`, включая `0.0.0.0/0,::/0`: новые конфиги
направляют через VPN только перечисленные IPv4-сети. IPv6 в список не добавляется.
Уже выданные конфиги не меняются: клиентам нужно самостоятельно обновить AllowedIPs
или получить новый конфиг через `/getwireguard`. Перезапуск WireGuard не требуется.

При наличии `/etc/wireguard/params` установщик подключает systemd-таймер и запускает
первое обновление. Далее обновления выполняются еженедельно, с задержкой до часа.
Пропущенный из-за выключения сервера запуск выполняется после включения.
Без WireGuard таймер не устанавливается.

Для существующей установки выполните из корня репозитория:

```bash
sudo install -d -m 755 /usr/local/libexec/vpn-bot
sudo install -o root -g root -m 644 scripts/update_wireguard_ips.py /usr/local/libexec/vpn-bot/update_wireguard_ips.py
sudo install -o root -g root -m 644 systemd/vpn-bot-update-ips.service systemd/vpn-bot-update-ips.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vpn-bot-update-ips.timer
sudo systemctl start vpn-bot-update-ips.service
```

Источник берётся из переменной окружения `SOURCE_URL`; если она не задана,
используется ссылка выше. Для systemd задайте её в `/etc/default/vpn-bot-update-ips`:

```bash
SOURCE_URL=https://gist.githubusercontent.com/iamwildtuna/7772b7c84a11bf6e1385f23096a73a15/raw/gistfile2.txt
```

Файл настроек необязателен. Новое значение применяется при следующем запуске сервиса.
Для разового запуска можно передать `--url` (имеет приоритет над `SOURCE_URL`):

```bash
sudo python3 scripts/update_wireguard_ips.py --url https://example.org/vpn-ips.txt
```

Путь к файлу настроек WireGuard можно изменить через `--params /path/to/params`.

Проверка расписания и журналов:

```bash
systemctl list-timers vpn-bot-update-ips.timer
sudo journalctl -u vpn-bot-update-ips.service -n 50 --no-pager
```

Чтобы обновлять раз в два дня, выполните `sudo systemctl edit vpn-bot-update-ips.timer`:

```ini
[Timer]
OnCalendar=
OnCalendar=*-*-01/2 04:00:00
```

Это запуск через день в пределах каждого месяца. Для запуска раз в две недели
после предыдущего запуска используйте вместо `OnCalendar=*-*-01/2 04:00:00` строки
`OnBootSec=15min` и `OnUnitActiveSec=14d` (после перезагрузки будет запуск через 15 минут).
После изменения расписания:

```bash
sudo systemctl daemon-reload
sudo systemctl restart vpn-bot-update-ips.timer
```

Отключение автоматического обновления:

```bash
sudo systemctl disable --now vpn-bot-update-ips.timer
```

### Диагностика тайм-аутов при выборочной маршрутизации

Обновляющий скрипт распознаёт строки Windows `route ADD <адрес> MASK <маска> <шлюз>`:
в AllowedIPs попадает только сеть назначения. Маски и шлюзы не добавляются как адреса,
а вложенные и соседние сети объединяются без расширения набора адресов.

Если сервисы не открываются, временно проверьте **копию клиентского конфига**
с `AllowedIPs = 0.0.0.0/0, ::/0`. Если полный туннель работает, проверьте,
покрывает ли выборочный список все A/AAAA-адреса доменов сервиса и его CDN.
IPv4-список не направляет IPv6-трафик через VPN. Добавление `::/0` направит
весь IPv6 через сервер и требует работающего IPv6 на сервере.

DNS-серверы из поля `DNS` также должны быть доступны. Чтобы направить настроенные
`1.1.1.1` и `1.0.0.1` через туннель, добавьте в клиентские AllowedIPs
`1.1.1.1/32,1.0.0.1/32`. Если и полный туннель не работает, проверьте
последний handshake и счётчики передачи в WireGuard, а на сервере —
`sudo wg show`, IP forwarding и правила NAT/FORWARD.
Не заменяйте клиентский `/32` в серверном `[Peer]` списком сервисов.

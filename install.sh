#!/usr/bin/env bash
set -e

REAL_USER=${SUDO_USER:-$USER}
REAL_HOME=$(eval echo "~$REAL_USER")

REPO_URL="https://github.com/blasterss/vpn_bot.git"
INSTALL_DIR="$REAL_HOME/vpn_bot"
SERVICE_NAME="vpn_bot.service"

echo "=== Установка vpn_bot ==="

### Проверка sudo ###
if [ "$EUID" -ne 0 ]; then
    echo "Скрипт будет использовать sudo"
    SUDO="sudo"
else
    SUDO=""
fi

### Определение пакетного менеджера ###
if command -v apt >/dev/null; then
    PKG="apt"
elif command -v dnf >/dev/null; then
    PKG="dnf"
elif command -v yum >/dev/null; then
    PKG="yum"
else
    echo "Неподдерживаемый пакетный менеджер"
    exit 1
fi

### Установка зависимостей ОС ###
install_packages() {
    case "$PKG" in
        apt)
            $SUDO apt update
            $SUDO apt install -y git python3 python3-venv python3-pip
            ;;
        dnf)
            $SUDO dnf install -y git python3 python3-virtualenv python3-pip
            ;;
        yum)
            $SUDO yum install -y git python3 python3-virtualenv python3-pip
            ;;
    esac
}

install_packages

### Клонирование ###
if [ ! -d "$INSTALL_DIR" ]; then
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

### venv ###
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

### Доступные VPN-скрипты (VPN-серверы должны быть установлены заранее) ###
OPENVPN_SCRIPT=""
WIREGUARD_SCRIPT=""
if [ -x "$REAL_HOME/openvpn-install.sh" ]; then
    OPENVPN_SCRIPT="$REAL_HOME/openvpn-install.sh"
fi
if [ -x "$REAL_HOME/wireguard-install.sh" ]; then
    WIREGUARD_SCRIPT="$REAL_HOME/wireguard-install.sh"
fi

### .env ###
echo "==== ВВОД ПАРАМЕТРОВ ===="
echo "Введите параметры конфигурации"
read -s -p "BOT_TOKEN: " BOT_TOKEN
echo ""
read -s -p "SECRET_KEY: " SECRET_KEY


echo "=== ГЕНЕРАЦИЯ .env ==="
cat > .env <<EOF
SCRIPT_PATH=$OPENVPN_SCRIPT
WIREGUARD_SCRIPT_PATH=$WIREGUARD_SCRIPT
WIREGUARD_CONFIG_DIR=$REAL_HOME
WIREGUARD_INTERFACE=wg0
WORKING_DIR=$REAL_HOME

BOT_TOKEN=$BOT_TOKEN
SECRET_KEY=$SECRET_KEY
EOF

chmod 600 .env
chown "$REAL_USER" .env

echo "=== Настройка sudoers ==="

SUDOERS_FILE="/etc/sudoers.d/vpn_bot"

# Разрешаем только обнаруженные скрипты; не выдаём доступ к произвольным командам.
{
    echo "# vpn_bot VPN scripts"
    for script in "$OPENVPN_SCRIPT" "$WIREGUARD_SCRIPT"; do
        if [ -n "$script" ]; then
            echo "$REAL_USER ALL=(root) NOPASSWD: $script"
        fi
    done
} | $SUDO tee "$SUDOERS_FILE" >/dev/null

$SUDO chmod 440 $SUDOERS_FILE

if $SUDO visudo -c >/dev/null 2>&1; then
    echo "sudoers успешно настроен"
else
    echo "Ошибка в sudoers!"
    exit 1
fi

echo "=== ГЕНЕРАЦИЯ vpn_bot.service ==="
cat > vpn_bot.service <<EOF
[Unit]
Description=VPN Telegram Bot
After=network.target

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/src/bot.py
CPUQuota=40%
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF


### systemd ###
$SUDO cp $INSTALL_DIR/$SERVICE_NAME /etc/systemd/system/$SERVICE_NAME
$SUDO systemctl daemon-reload
$SUDO systemctl enable $SERVICE_NAME
$SUDO systemctl restart $SERVICE_NAME

### Обновление списка маршрутов WireGuard ###
if $SUDO test -f /etc/wireguard/params; then
    $SUDO install -d -m 755 /usr/local/libexec/vpn-bot
    $SUDO install -o root -g root -m 644 scripts/update_wireguard_ips.py /usr/local/libexec/vpn-bot/update_wireguard_ips.py
    $SUDO install -o root -g root -m 644 systemd/vpn-bot-update-ips.service systemd/vpn-bot-update-ips.timer /etc/systemd/system/
    $SUDO systemctl daemon-reload
    $SUDO systemctl enable --now vpn-bot-update-ips.timer
    $SUDO systemctl start --no-block vpn-bot-update-ips.service
fi

echo "=== Установка успешно завершена ==="

import os
import asyncio
import logging
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardRemove
from dotenv import load_dotenv
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")      # Токен бота из переменных окружения
WORKING_DIR = os.getenv("WORKING_DIR")  # Рабочая директория
SCRIPT_PATH = os.getenv("SCRIPT_PATH")  # Полный путь к скрипту
SECRET_KEY = os.getenv("SECRET_KEY")  # Секретный код для проверки текущих соединений

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class SecureServerStates(StatesGroup):
    waiting_for_secret = State()

async def create_vpn_user(client_name: str) -> str:
    """
    Функция создания конфигурации VPN пользователя

    Args:
        client_name (str): Имя клиента (имя пользователя tg)

    Raises:
        RuntimeError: 
        FileNotFoundError:

    Returns:
        str: Путь к файлу конфигурации VPN пользователя
    """
    
    output_file = os.path.join(WORKING_DIR, f"{client_name}.ovpn")

    logger.info(f"Запуск создания VPN пользователя: {client_name}")

    process = await asyncio.create_subprocess_exec(
        "sudo",
        SCRIPT_PATH,
        "client",
        "add",
        client_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=WORKING_DIR
    )

    stdout, stderr = await process.communicate()

    # Логирование вывода скрипта
    if stdout:
        logger.info(f"STDOUT: {stdout.decode()}")
    if stderr:
        logger.warning(f"STDERR: {stderr.decode()}")

    if process.returncode != 0:
        error_msg = stderr.decode() if stderr else stdout.decode()
        raise RuntimeError(f"Ошибка при создании VPN пользователя: {error_msg}")

    # Проверка существования файла конфигурации
    if not os.path.exists(output_file):
        # Проверяем возможные альтернативные пути и расширения
        possible_paths = [
            output_file,  # Ожидаемый путь
            os.path.join(WORKING_DIR, f"{client_name}.conf"),
            os.path.join("/root", f"{client_name}.ovpn"),
            os.path.join("/root", f"{client_name}.conf"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Файл найден по альтернативному пути: {path}")
                return path
        
        raise FileNotFoundError(
            f"Файл конфигурации не найден после выполнения скрипта. "
            f"Проверенные пути: {possible_paths}"
        )

    logger.info(f"Файл конфигурации успешно создан: {output_file}")
    return output_file

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    username = message.from_user.username or f"user_{message.from_user.id}"

    await message.answer(
        f"Привет, {username}!👋\n"
        "🤖 Я Бот для создания VPN конфигураций\n\n"
        "Используйте команду /getvpn для создания конфигурации.\n"
    )

@dp.message(Command("__secure_server_activity"))
async def cmd_secure_server_activity(message: types.Message, state: FSMContext):
    logger.info("Запрос проверки активности сервера")

    await state.set_state(SecureServerStates.waiting_for_secret)

    await message.answer(
        "Введите секретный код для проверки активности сервера",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(SecureServerStates.waiting_for_secret)
async def process_secret_code(message: types.Message, state: FSMContext):
    if message.text != SECRET_KEY:
        await message.answer("❌ Доступ запрещен")
        await state.clear()
        return

    logger.info("Секретный код подтверждён")

    process = await asyncio.create_subprocess_exec(
        "sudo",
        SCRIPT_PATH,
        "server",
        "status",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=WORKING_DIR
    )

    stdout, stderr = await process.communicate()

    if stdout:
        logger.info(f"STDOUT: {stdout.decode()}")
    if stderr:
        logger.warning(f"STDERR: {stderr.decode()}")

    if process.returncode != 0:
        error_msg = stderr.decode() if stderr else stdout.decode()
        await state.clear()
        raise RuntimeError(f"Ошибка при проверке активности сервера: {error_msg}")

    await message.answer(
        f"✅ Сервер активен\n\n<pre>{stdout.decode()}</pre>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

    await state.clear()

@dp.message(Command("getvpn"))
async def cmd_vpn(message: types.Message):
    """Обработчик команды создания VPN конфигурации"""

    base_name = message.from_user.username or f"user_{message.from_user.id}"

    output_file = None
    try:
        # Создание VPN пользователя
        client_name = f"{base_name}_{int(time.time())}"
        await message.answer("⏳ Создаю VPN конфигурацию...")
        output_file = await create_vpn_user(client_name)
        
        # Отправка файла пользователю
        vpn_file = FSInputFile(output_file, filename=f"{client_name}.ovpn")
        await message.answer_document(
            vpn_file, 
            caption=f"✅ VPN конфигурация для <code>{client_name}</code> готова!\n\n"
                   "💡 Используйте этот файл в приложении OpenVPN Connect.",
            parse_mode="HTML"
        )
        
        logger.info(f"VPN конфигурация успешно отправлена пользователю {message.from_user.id}")

    except FileNotFoundError as e:
        logger.error(f"FileNotFoundError для клиента {client_name}: {e}")
        await message.answer("❌ Ошибка: файл конфигурации не найден. Попробуйте снова.")
    
    except ValueError as e:
        logger.error(f"ValueError для клиента {client_name}: {e}")
        await message.answer(f"❌ Ошибка в имени клиента: {e}")
    
    except RuntimeError as e:
        logger.error(f"RuntimeError для клиента {client_name}: {e}")
        await message.answer(f"❌ Ошибка при создании VPN: {e}")
    
    except Exception as e:
        logger.error(f"Неожиданная ошибка для клиента {client_name}: {e}")
        await message.answer("⚠️ Произошла непредвиденная ошибка. Попробуйте позже.")
    
    finally:
        if output_file and os.path.exists(output_file):
            try:
                os.remove(output_file)
                logger.info(f"Файл {output_file} успешно удален")
            except Exception as cleanup_err:
                logger.error(f"Ошибка удаления файла {output_file}: {cleanup_err}")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    await message.answer(
        "📖 <b>Помощь по боту</b>\n\n"
        "<b>Доступные команды:</b>\n"
        "• /start — Начать работу с ботом\n"
        "• /getvpn — Создать VPN конфигурацию\n"
        "• /help — Показать эту справку\n\n"
        "🌐 <b>Порядок действий для подключения к VPN:</b>\n"
        "1) Введите команду <code>/getvpn</code> — бот создаст ваш индивидуальный VPN-конфиг.\n"
        "2) Скачайте отправленный файл <code>.ovpn</code>.\n"
        "3) Установите клиент <b>OpenVPN</b>:\n"
        " • Windows — <a href='https://openvpn.net/community-downloads/'>OpenVPN GUI</a>\n"
        " • Android — <a href='https://play.google.com/store/apps/details?id=net.openvpn.openvpn'>OpenVPN Connect</a>\n"
        " • iOS — <a href='https://apps.apple.com/app/openvpn-connect/id590379981'>OpenVPN Connect</a>\n"
        "4) Импортируйте полученный файл <code>.ovpn</code> в приложение OpenVPN.\n"
        "5) Нажмите «Подключиться» — и вы в VPN! 🔐\n\n",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

async def main():
    """Основная функция запуска бота"""
    # Проверка необходимых файлов и директорий
    if not os.path.exists(SCRIPT_PATH):
        logger.error(f"Скрипт {SCRIPT_PATH} не найден!")
        return
    
    if not os.access(SCRIPT_PATH, os.X_OK):
        logger.error(f"Скрипт {SCRIPT_PATH} не исполняемый!")
        return
    
    logger.info("🚀 Бот запущен и готов выдавать VPN-конфиги")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    # Проверка переменных окружения
    if not BOT_TOKEN:
        print("❌ Ошибка: BOT_TOKEN не установлен в переменных окружения")
        exit(1)
    
    asyncio.run(main())
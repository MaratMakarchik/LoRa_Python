from python.help_fnc.terminal_output import print_green, print_red
import os
import subprocess
import sys

def main() -> None:
    try:
        print_green('Starting program')
        
        # Получаем корневую директорию проекта
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        
        # Добавляем корневую директорию в PYTHONPATH
        sys.path.insert(0, project_root)
        
        python_dir = os.path.join(project_root, 'python')
        bdrv_dir = os.path.join(python_dir, 'bdrv')
        bot_dir = os.path.join(python_dir, 'bot')

        start_bdrv_file = os.path.join(bdrv_dir, 'start_bdrv.py')
        start_bot_file = os.path.join(bot_dir, 'start_bot.py')

        if not os.path.exists(start_bdrv_file):
            raise FileNotFoundError(f"File {start_bdrv_file} not found")
        if not os.path.exists(start_bot_file):
            raise FileNotFoundError(f"File {start_bot_file} not found")

        # Запуск скриптов
        print_green("Launching BDRV and BOT scripts...")
        
        # Создаем окружение с правильным PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = project_root + os.pathsep + env.get('PYTHONPATH', '')
        
        # Запуск start_bdrv.py
        bdrv_process = subprocess.Popen(
            [sys.executable, start_bdrv_file],
            cwd=project_root,  # Устанавливаем рабочую директорию в корень проекта
            env=env
        )
        
        # Запуск start_bot.py
        bot_process = subprocess.Popen(
            [sys.executable, start_bot_file],
            cwd=project_root,  # Устанавливаем рабочую директорию в корень проекта
            env=env
        )

        # Ожидание завершения процессов
        bdrv_process.wait()
        bot_process.wait()

    except FileNotFoundError as e:
        print_red(f"File error: {e}")
    except Exception as e:
        print_red(f"Unexpected error: {e}")
    finally:
        # Завершение процессов при выходе
        if 'bdrv_process' in locals():
            bdrv_process.terminate()
        if 'bot_process' in locals():
            bot_process.terminate()
        print_green("Program terminated")

if __name__ == "__main__":
    main()
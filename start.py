from python.help_fnc.terminal_output import print_green, print_red
import os
import subprocess
import sys

def main() -> None:
    try:
        print_green('Starting program')
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        python_dir = os.path.join(current_dir, 'python')
        
        bdrv_dir = os.path.join(python_dir, 'bdrv')
        bot_dir = os.path.join(python_dir, 'bot')

        start_bdrv_file = os.path.join(bdrv_dir, 'start_bdrv.py')
        start_bot_file = os.path.join(bot_dir, 'start_bot.py')

        if not os.path.exists(start_bdrv_file):
            raise FileNotFoundError(f"File {start_bdrv_file} not found")
        if not os.path.exists(start_bot_file):
            raise FileNotFoundError(f"File {start_bot_file} not found")

        print_green("Launching BDRV scripts")
        bdrv_process = subprocess.Popen([sys.executable, start_bdrv_file], 
                                        cwd=bdrv_dir)
        print_green(f"Started C process with PID: {bdrv_process.pid}")

        print_green("Launching BOT scripts")
        bot_process = subprocess.Popen([sys.executable, start_bot_file], 
                                       cwd=bot_dir)
        print_green(f"Started C process with PID: {bot_process.pid}")
    
        bdrv_process.wait()
        bot_process.wait()

    except FileNotFoundError as e:
        print_red(f"File error: {e}")

    except Exception as e:
        print_red(f"Unexpected error: {e}")

    finally:
        if 'bdrv_process' in locals():
            bdrv_process.terminate()
        if 'bot_process' in locals():
            bot_process.terminate()
        print_green("Program terminated")

if __name__ == "__main__":
    main()

from python.help_fnc.terminal_output import print_green, print_red
import os
import subprocess
import sys
import signal
import time


bdrv_process = None
bot_process = None

def signal_handler(sig, frame):
    """Обработчик сигналов для graceful shutdown"""
    print_red("\nReceived interrupt signal. Shutting down...")
    
    if bdrv_process:
        bdrv_process.terminate()
    if bot_process:
        bot_process.terminate()
    
    time.sleep(1)
    
    if bdrv_process and bdrv_process.poll() is None:
        bdrv_process.kill()
    if bot_process and bot_process.poll() is None:
        bot_process.kill()
    
    sys.exit(0)

def main() -> None:
    global bdrv_process, bot_process
    
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print_green('Starting program')
        
        
        project_root = os.path.dirname(os.path.abspath(__file__))
        print_green(f"Project root: {project_root}")
        
        
        start_bdrv_file = os.path.join(project_root, 'python', 'bdrv', 'start_bdrv.py')
        start_bot_file = os.path.join(project_root, 'python', 'bot', 'start_bot.py')

        if not os.path.exists(start_bdrv_file):
            raise FileNotFoundError(f"File {start_bdrv_file} not found")
        if not os.path.exists(start_bot_file):
            raise FileNotFoundError(f"File {start_bot_file} not found")
        
        
        env = os.environ.copy()
        env['PYTHONPATH'] = project_root + os.pathsep + env.get('PYTHONPATH', '')

        print_green("Launching BDRV script")
        bdrv_process = subprocess.Popen(
            [sys.executable, start_bdrv_file],
            cwd=project_root,  
            env=env
        )
        
        print_green(f"Started process with PID: {bdrv_process.pid}")
        
        print_green("Launching BOT script")
        bot_process = subprocess.Popen(
            [sys.executable, start_bot_file],
            cwd=project_root,  
            env=env
        )
        print_green(f"Started process with PID: {bot_process.pid}")

        
        try:
            bdrv_process.wait()
            bot_process.wait()
        except KeyboardInterrupt:
            # При получении Ctrl+C вызываем обработчик сигналов
            signal_handler(signal.SIGINT, None)

    except FileNotFoundError as e:
        print_red(f"File error: {e}")
    except Exception as e:
        print_red(f"Unexpected error: {e}")
    finally:
        
        if bdrv_process and bdrv_process.poll() is None:
            bdrv_process.terminate()
        if bot_process and bot_process.poll() is None:
            bot_process.terminate()
        print_green("Program terminated")

if __name__ == "__main__":
    main()
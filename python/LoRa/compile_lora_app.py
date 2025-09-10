import subprocess
import os
import sys

from python.help_fnc.terminal_output import print_green, print_red

def compile_lora_app():
    """
    Compiles main.c and LoRa.c into lora_app binary using sudo gcc
    """
    # Get the current directory (python folder)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Get the project root directory (one level up from python)
    project_root = os.path.dirname(os.path.dirname(current_dir))
    
    # Define paths to source files in the c directory
    c_dir = os.path.join(project_root, 'file_c')
    main_c = os.path.join(c_dir, 'main.c')
    lora_c = os.path.join(c_dir, 'LoRa.c')
    lora_h = os.path.join(c_dir, 'LoRa.h')
    bin_dir = os.path.join(c_dir, 'bin')
    
    # Check if source files exist
    if not os.path.exists(main_c):
        raise FileNotFoundError(f"File {main_c} not found")
    if not os.path.exists(lora_c):
        raise FileNotFoundError(f"File {lora_c} not found")
    if not os.path.exists(lora_h):
        print_red(f"Warning: Header file {lora_h} not found")
    
    # Create bin directory in c folder if it doesn't exist
    os.makedirs(bin_dir, exist_ok=True)
    
    # Form compilation command
    output_file = os.path.join(bin_dir, 'lora_app')
    command = [
        'sudo', 'gcc',
        '-o', output_file,
        main_c, lora_c,
        '-lwiringPi',
        '-I', c_dir  # Add c directory to include path for header files
    ]
    
    # Execute compilation
    try:
        print("Compiling main.c and LoRa.c...")
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
            timeout=30
        )
        print_green("Compilation completed successfully!")
        print(f"Binary file created: {output_file}")
        return True
        
    except subprocess.CalledProcessError as e:
        print_red(f"Compilation error (exit code: {e.returncode})")
        print(f"STDERR: {e.stderr}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        return False
        
    except subprocess.TimeoutExpired:
        print_red("Error: compilation timed out")
        return False
        
    except Exception as e:
        print_red(f"Unexpected error: {str(e)}")
        return False

# For direct script execution
if __name__ == "__main__":
    success = compile_lora_app()
    sys.exit(0 if success else 1)
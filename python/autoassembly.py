import subprocess
import os
import sys

def compile_lora_app():
    """
    Compiles main.c and LoRa.c into lora_app binary using sudo gcc
    """
    # Define file paths based on actual project structure
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Project root
    bin_dir = os.path.join(project_root, 'bin')  # Binary output directory
    
    # Check if source files exist in root directory
    main_c = os.path.join(project_root, 'main.c')
    lora_c = os.path.join(project_root, 'LoRa.c')
    lora_h = os.path.join(project_root, 'LoRa.h')
    
    if not os.path.exists(main_c):
        raise FileNotFoundError(f"File {main_c} not found")
    if not os.path.exists(lora_c):
        raise FileNotFoundError(f"File {lora_c} not found")
    if not os.path.exists(lora_h):
        print(f"Warning: Header file {lora_h} not found")
    
    # Create bin directory if it doesn't exist
    os.makedirs(bin_dir, exist_ok=True)
    
    # Form compilation command
    output_file = os.path.join(bin_dir, 'lora_app')
    command = [
        'sudo', 'gcc',
        '-o', output_file,
        main_c, lora_c,
        '-lwiringPi',
        '-I', project_root  # Add project root to include path for LoRa.h
    ]
    
    # Execute compilation
    try:
        print(f"Compiling {main_c} and {lora_c}...")
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
            timeout=30  # 30 second timeout
        )
        print("Compilation completed successfully!")
        print(f"Binary file created: {output_file}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Compilation error (exit code: {e.returncode}):")
        print(f"STDERR: {e.stderr}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        return False
        
    except subprocess.TimeoutExpired:
        print("Error: compilation timed out")
        return False
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False

# For direct script execution
if __name__ == "__main__":
    success = compile_lora_app()
    sys.exit(0 if success else 1)
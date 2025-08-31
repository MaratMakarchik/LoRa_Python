MES_LEN = 90

def print_red(text):
    print(f"\033[31m---{text:^{MES_LEN}}---\033[0m")

def print_green(text):
    print(f"\033[32m---{text:^{MES_LEN}}---\033[0m")

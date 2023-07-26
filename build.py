import subprocess


def generate_parser(setup_kwargs):
    print("Generating CMake Parser:")
    subprocess.run(['antlr4', '-o', 'cmake_refactor/parser', 'CMake.g4'])
    return setup_kwargs


if __name__ == "__main__":
    generate_parser({})

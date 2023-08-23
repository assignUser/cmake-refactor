import subprocess


def generate_parser(setup_kwargs):
    print("Generating CMake Parser...")
    cmd = ["poetry", "run", "antlr4", "-o", "cmake_refactor/parser"]
    subprocess.run(cmd + ["CMakeLexer.g4"])
    subprocess.run(cmd + ["CMakeParser.g4"])
    print("Done!")
    return setup_kwargs


if __name__ == "__main__":
    generate_parser({})

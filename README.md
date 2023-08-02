# cmake-refactor

This package was initially created to update around 300 targets in the [Velox](https://github.com/facebookincubator/velox) build system to use `target_link_libraries` with the appropriate keyword (`PRIVAT|PUBLIC|INTERFACE`) to resolve circluar dependencies and align with 'modern CMake' practices.

The package currently contains hardcoded assumptions that are tailored to the Velox directory and code hierarchy. An ongoing goal is to remove these assumptions and make the package usable by other projects.

## Parser
This repo contains a ANTLRv4 grammar for CMake that is used to generate a fast parser that provides listener and visitor classes. This parser will also likely be generalized and extended.

## Contributions
Contributions are welcome, please open an issue to discuss your plans (unless it's a typo ;)).

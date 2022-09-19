### Installation

1. Clone the repo from github
   ```sh
   git clone https://github.com/gzdshn/hoot-toolkit.git
   ```
2. Create a virtual environment in the root of the cloned directory
   ```sh
   cd hoot-toolkit
   python3 -m venv .venv
   ```
3. Enter the virtual environment
   ```sh
   source .venv/bin/activate
   ```
4. Install the hoot-toolkit CLI and dependancies
   ```sh
   pip install -e ./
   ```

## Getting Started

1. View the CLI command listing
   ```sh
   hoot --help
   ```
2. View help for a subcommand
   ```sh
   hoot make-archive --help
   ```

## Example make-archive
   ```sh
   hoot make-archive --dir data/hoot_v1 --dest data/hoot_v1_export --version 1.0 --clean=True
   ```
# arch-updates

Arch Linux package updates, system cleanup, and news checks.

## Development

1. Install required dependencies

    ```sh
    sudo pacman -S --needed python python-colorama python-gobject
    ```

2. Clone the repository

    ```sh
    git clone https://github.com/whisp2424/arch-updates
    cd arch-updates
    ```

3. Set up the virtual environment

    ```sh
    python -m venv --system-site-packages .venv
    source .venv/bin/activate
    pip install -e .
    ```

## Usage

```
arch-updates [--version] <command>
```

| Command   | Description                                                                            |
| --------- | -------------------------------------------------------------------------------------- |
| `update`  | Sync and upgrade official, AUR, and Flatpak packages, then run cleanup                 |
| `cleanup` | Remove orphans, trim pacman cache, wipe AUR build cache, clean unused Flatpak runtimes |
| `check`   | Query all sources for available updates                                                |
| `news`    | Read or get notified about Arch Linux news                                             |

## Configuration

Settings are stored in `~/.config/arch-updates/config.toml`.

You can run `--save` when running any subcommand with flags to persist them to your configuration.

See [docs/configuration.md](docs/configuration.md) for the full reference.

### Terminal emulator

Configuring your terminal emulator is required for the script to launch the interactive update terminal as needed (e.g. update notifications). You can configure your terminal emulator using the following command:

```sh
arch-updates config terminal ghostty
```

### Daily notifications

To get daily update/news notifications, you can setup a systemd timer. See [docs/daily-notifications.md](docs/daily-notifications.md) for instructions.
# Configuration

`arch-updates` reads settings from `~/.config/arch-updates/config.toml`. A configuration file is not required, every option has a sensible default.

The `--save` flag can be used when running any subcommand with flags to persist them to your configuration.

## Terminal

Commands that need to open a terminal window require a terminal emulator to be configured:

```toml
[terminal]
command = "ghostty"
```

If `command` is unset and the `$TERMINAL` environment variable is empty, these commands will fail with a message pointing to this setting.

## AUR helper

By default, the AUR helper is detected automatically, but it can be configured explicitly.

### Auto-detection

```toml
[aur]
helper = "auto"
```

This probes for `paru` and `yay` (in that order) and uses the first one found.

### Custom helper

If you use a different AUR helper or need different flags, set `helper = "custom"` and supply each command as a full command array:

```toml
[aur]
helper = "custom"
check_updates = ["pikaur", "-Qua"]
install_updates = ["pikaur", "-Sua"]
remove_orphans = ["pikaur", "-Rns", "--noconfirm", "-"]
build_cache_dir = "pikaur"
```

Each key is a full command array (program name followed by arguments).

The orphan list from `pacman -Qdtq` is passed on stdin of the `remove_orphans` command, so helpers that accept package names via `-` work naturally.

For `build_cache_dir`, provide the name of the subdirectory under `~/.cache/` where build artifacts are stored.

All four keys are required when using `helper = "custom"`. The commands must match the same interface as the built-in helpers. The output of `check_updates` must list packages in `package current_version -> new_version` format.

## Updates

```toml
[update]
no_cleanup = false
```

When `true`, the post-update cleanup step is skipped.

This is the equivalent of running `arch-updates update` with `--no-cleanup`.

## Cleanup

```toml
[cleanup]
keep = 3
no_orphans = false
no_paccache = false
no_aurcache = false
no_flatpak = false
```

| Key           | Default | Description                                            |
| ------------- | ------- | ------------------------------------------------------ |
| `keep`        | `3`     | Number of package versions to retain in pacman's cache |
| `no_orphans`  | `false` | Skip orphaned package removal                          |
| `no_paccache` | `false` | Skip pacman cache trimming                             |
| `no_aurcache` | `false` | Skip AUR build cache cleanup                           |
| `no_flatpak`  | `false` | Skip unused Flatpak runtime cleanup                    |

## Check

```toml
[check]
no_pacman = false
no_aur = false
no_flatpak = false
```

Controls which update sources are queried when running `arch-updates check`.

## News

```toml
[news]
count = 10
reverse = false
pager = "auto"
read = "ask"
unread = true
```

| Key       | Default   | Description                                                                                                            |
| --------- | --------- | ---------------------------------------------------------------------------------------------------------------------- |
| `count`   | `3`       | Number of news items to display                                                                                        |
| `reverse` | `false`   | Show oldest items first; defaults to `true` when `pager` is `"never"`. Override with `--no-reverse`                    |
| `pager`   | `"never"` | Pager behavior: `"auto"` pages if output exceeds terminal height, `"always"` forces a pager, `"never"` prints directly |
| `read`    | `"ask"`   | When to mark displayed news as read: `"ask"` prompts, `"always"` auto-marks                                            |
| `unread`  | `true`    | Show only unread news items when `true`; show all items when `false`                                                   |

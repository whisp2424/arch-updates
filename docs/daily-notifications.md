# Daily notifications

To get daily update and news notifications, you can set up a systemd user timer that runs `check --notify` and `news --notify` once a day.

## Prerequisites

Notifications require `libnotify` to be installed:

```sh
sudo pacman -S --needed libnotify
```

Make sure a terminal emulator is configured, so that `arch-updates` can open the interactive update terminal for you:

```sh
arch-updates config terminal ghostty
```

## 1. Create the service

```
# ~/.config/systemd/user/arch-updates.service

[Unit]
Description=Arch Updates

[Service]
Type=oneshot
ExecStart=%h/.local/bin/arch-updates check --notify
ExecStart=%h/.local/bin/arch-updates news --notify
```

## 2. Create the timer

```
# ~/.config/systemd/user/arch-updates.timer

[Unit]
Description=Daily Arch updates check

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

## 3. Enable and start

```sh
systemctl --user daemon-reload
systemctl --user enable --now arch-updates.timer
```

The timer fires once a day. If the system was powered off at the scheduled time, `Peristent=true` will fire the notifications once you're back.
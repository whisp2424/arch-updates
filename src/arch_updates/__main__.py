from arch_updates.cli import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        import sys
        sys.exit(130)

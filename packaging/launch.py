"""PyInstaller and source-launch entry point."""
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from autumn.main import main

    raise SystemExit(main())

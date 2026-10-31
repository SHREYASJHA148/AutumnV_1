"""The installer has no automatic action unless explicit validation CLI flags are supplied."""

from autumn.setup.installer_app import main

if __name__ == "__main__":
    raise SystemExit(main())

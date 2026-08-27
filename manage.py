#!/usr/bin/env python
"""Django's command-line utility — arrived with the map page (the first slice
that needs `runserver` to look at). Tests never use it (pytest-django)."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "carbon_atlas.web.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

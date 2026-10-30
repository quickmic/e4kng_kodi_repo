
#!/usr/bin/env python3

import html
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Public testing"
SITE = ROOT / "_site"
DESTINATION = SITE / SOURCE.name


def generate_index(directory):
    output = DESTINATION / directory.relative_to(SOURCE)
    output.mkdir(parents=True, exist_ok=True)

    lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '<meta charset="UTF-8">',
        f"<title>{html.escape(directory.name)}</title>",
        "</head>",
        "<body>",
        "<table>",
        "<tbody>",
    ]

    if directory != SOURCE:
        lines.append('<tr><td><a href="../">Parent Directory</a></td></tr>')

    entries = sorted(
        (entry for entry in directory.iterdir()
         if not entry.is_symlink() and entry.name != "index.html"),
        key=lambda p: (not p.is_dir(), p.name.casefold())
    )

    for entry in entries:
        if entry.is_dir():
            name = entry.name + "/"
            href = quote(entry.name, safe="") + "/"
        elif entry.is_file():
            name = entry.name
            href = quote(entry.name, safe="")
        else:
            continue

        lines.append(
            f'<tr><td><a href="{html.escape(href, quote=True)}">'
            f'{html.escape(name)}</a></td></tr>'
        )

    lines.extend([
        "</tbody>",
        "</table>",
        "</body>",
        "</html>",
    ])

    index_file = output / "index.html"
    index_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated: {index_file.relative_to(SITE)}")


def main():
    if not SOURCE.is_dir():
        raise RuntimeError(f"Source directory not found: {SOURCE}")

    if not SITE.is_dir():
        raise RuntimeError(f"Site directory not found: {SITE}")

    directories = [SOURCE]
    directories.extend(
        sorted(
            (p for p in SOURCE.rglob("*") if p.is_dir() and not p.is_symlink()),
            key=lambda p: p.as_posix().casefold()
        )
    )

    for directory in directories:
        generate_index(directory)

    expected = DESTINATION / "index.html"
    if not expected.is_file():
        raise RuntimeError(f"Directory index was not generated: {expected}")

    print(f"Verified: {expected.relative_to(SITE)}")


if __name__ == "__main__":
    main()

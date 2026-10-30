
#!/usr/bin/env python3

import html
from pathlib import Path
from urllib.parse import quote

SOURCE = Path("Public testing")
DESTINATION = Path("_site/Public testing")


def generate_index(directory):
    output = DESTINATION / directory.relative_to(SOURCE)
    output.mkdir(parents=True, exist_ok=True)

    index_file = output / "index.html"

    if index_file.exists():
        raise RuntimeError(f"Refusing to overwrite existing index.html: {index_file}")

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
        lines.append(
            '<tr><td><a href="../">Parent Directory</a></td></tr>'
        )

    entries = sorted(
        directory.iterdir(),
        key=lambda p: (not p.is_dir(), p.name.lower())
    )

    for entry in entries:
        if entry.is_symlink():
            continue

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

    index_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated: {index_file}")


if not SOURCE.is_dir():
    raise RuntimeError(f"Source directory not found: {SOURCE}")

for directory in [SOURCE] + sorted(
    (p for p in SOURCE.rglob("*") if p.is_dir()),
    key=lambda p: str(p).lower()
):
    generate_index(directory)

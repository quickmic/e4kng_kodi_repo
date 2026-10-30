#!/usr/bin/env python3

import hashlib
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_URL = "https://quickmic.github.io/e4kng_kodi_repo"
REPOSITORIES = {
    "repo": {
        "id": "repository.e4kng_kodi_repo.stable",
        "name": "E4KNG Kodi Stable Addons",
        "description": "This repository contains stable Emby for Kodi Next Gen add-ons.",
        "zip": "repository.e4kng_kodi_repo-stable.zip",
    },
    "repo-beta": {
        "id": "repository.e4kng_kodi_repo.beta",
        "name": "E4KNG Kodi Beta Addons",
        "description": "This repository contains beta Emby for Kodi Next Gen add-ons.",
        "zip": "repository.e4kng_kodi_repo-beta.zip",
    },
}
REQUIRED_RESOURCE_FILES = ("icon.png", "fanart.jpg")


def get_kodi_directories(repository):
    directories = []
    for directory in repository.iterdir():
        match = re.fullmatch(r"v(\d+)", directory.name)
        if directory.is_dir() and not directory.is_symlink() and match:
            directories.append((int(match.group(1)), directory))

    return sorted(directories, key=lambda item: item[0], reverse=True)


def get_addon_xml(addon_directory):
    addon_xml = addon_directory / "addon.xml"
    if not addon_xml.is_file():
        raise RuntimeError(f"Missing addon.xml: {addon_xml.relative_to(ROOT)}")

    content = addon_xml.read_text(encoding="utf-8")
    root = ElementTree.fromstring(content)
    if root.tag != "addon":
        raise RuntimeError(f"Invalid addon.xml root element: {addon_xml.relative_to(ROOT)}")

    addon_id = root.attrib.get("id")
    if not addon_id:
        raise RuntimeError(f"Missing addon id: {addon_xml.relative_to(ROOT)}")
    if addon_id != addon_directory.name:
        raise RuntimeError(
            f"Addon directory '{addon_directory.name}' does not match addon id '{addon_id}'"
        )

    content = re.sub(r"^\s*<\?xml[^?]*\?>", "", content, count=1).strip()
    return addon_id, content


def generate_addons_xml(version_directory):
    addons = []
    addon_directories = sorted(
        (directory for directory in version_directory.iterdir()
         if directory.is_dir() and not directory.is_symlink()),
        key=lambda directory: directory.name.casefold()
    )

    for addon_directory in addon_directories:
        addon_xml = addon_directory / "addon.xml"
        if not addon_xml.is_file():
            continue
        addon_id, content = get_addon_xml(addon_directory)
        addons.append((addon_id, content))

    if not addons:
        raise RuntimeError(f"No add-ons found in {version_directory.relative_to(ROOT)}")

    output = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        "<addons>",
    ]
    output.extend(content for _, content in addons)
    output.extend(["</addons>", ""])

    addons_xml = version_directory / "addons.xml"
    addons_xml.write_text("\n".join(output), encoding="utf-8")

    checksum = hashlib.md5(addons_xml.read_bytes()).hexdigest()
    (version_directory / "addons.xml.md5").write_text(
        f"{checksum}  addons.xml\n", encoding="ascii"
    )

    print(f"Generated: {addons_xml.relative_to(ROOT)} ({len(addons)} add-ons)")
    print(f"Generated: {(version_directory / 'addons.xml.md5').relative_to(ROOT)}")


def generate_repository_addon_xml(repository_name, configuration, kodi_directories):
    repository_id = configuration["id"]
    repository_display_name = configuration["name"]
    repository_base = f"{REPOSITORY_URL}/{repository_name}"

    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<addon id="{repository_id}" name="{repository_display_name}" version="1.0.0" provider-name="">',
        "    <requires>",
        '        <import addon="xbmc.addon" version="12.0.0"/>',
        "    </requires>",
        f'    <extension point="xbmc.addon.repository" name="{repository_display_name}">',
    ]

    for kodi_version, directory in kodi_directories:
        minversion = f"{kodi_version - 1}.999.0"
        directory_url = f"{repository_base}/{directory.name}/"
        lines.extend([
            f'        <dir minversion="{minversion}">',
            f'            <info compressed="false">{directory_url}addons.xml</info>',
            f'            <checksum>{directory_url}addons.xml.md5</checksum>',
            f'            <datadir zip="true">{directory_url}</datadir>',
            "        </dir>",
        ])

    lines.extend([
        "    </extension>",
        '    <extension point="xbmc.addon.metadata">',
        f"        <summary>{repository_display_name} Repository</summary>",
        f"        <description>{configuration['description']}</description>",
        "        <disclaimer></disclaimer>",
        "        <platform>all</platform>",
        "        <assets>",
        "            <icon>resources/icon.png</icon>",
        "            <fanart>resources/fanart.jpg</fanart>",
        "        </assets>",
        "    </extension>",
        "</addon>",
        "",
    ])

    return "\n".join(lines)


def write_repository_zip(repository_name, configuration, addon_xml):
    repository_id = configuration["id"]
    zip_path = ROOT / configuration["zip"]
    resources_directory = ROOT / "resources"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        addon_info = zipfile.ZipInfo(f"{repository_id}/addon.xml", (1980, 1, 1, 0, 0, 0))
        addon_info.compress_type = zipfile.ZIP_DEFLATED
        addon_info.external_attr = 0o100644 << 16
        archive.writestr(addon_info, addon_xml.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

        for resource_name in REQUIRED_RESOURCE_FILES:
            if not (resources_directory / resource_name).is_file():
                print(f"Not yet included in {zip_path.name}: resources/{resource_name} not found")

        if resources_directory.is_dir():
            for resource in sorted(
                (path for path in resources_directory.rglob("*") if path.is_file() and not path.is_symlink()),
                key=lambda path: path.relative_to(resources_directory).as_posix().casefold()
            ):
                relative_path = resource.relative_to(resources_directory).as_posix()
                resource_info = zipfile.ZipInfo(
                    f"{repository_id}/resources/{relative_path}", (1980, 1, 1, 0, 0, 0)
                )
                resource_info.compress_type = zipfile.ZIP_DEFLATED
                resource_info.external_attr = 0o100644 << 16
                archive.writestr(
                    resource_info,
                    resource.read_bytes(),
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )

    print(f"Generated: {zip_path.relative_to(ROOT)}")


def main():
    for repository_name, configuration in REPOSITORIES.items():
        repository = ROOT / repository_name
        if not repository.is_dir():
            raise RuntimeError(f"Repository directory not found: {repository_name}")

        kodi_directories = get_kodi_directories(repository)
        if not kodi_directories:
            raise RuntimeError(f"No Kodi version directories found in {repository_name}")

        for _, version_directory in kodi_directories:
            generate_addons_xml(version_directory)

        addon_xml = generate_repository_addon_xml(
            repository_name, configuration, kodi_directories
        )
        ElementTree.fromstring(addon_xml)
        write_repository_zip(repository_name, configuration, addon_xml)


if __name__ == "__main__":
    main()

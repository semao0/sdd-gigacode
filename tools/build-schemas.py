#!/usr/bin/env python3
"""Собирает схемы OpenSpec компании из встроенной схемы spec-driven + наших overlay.

Инструкции артефактов берутся из установленного OpenSpec (они знают нюансы CLI
текущей версии), поверх дописываются корпоративные правила из overlay.yaml.
После обновления OpenSpec достаточно перезапустить скрипт.

Использование:
    tools/build-schemas.py [--openspec-dir DIR] [--out DIR]
"""
import argparse
import pathlib
import shutil
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "schemas-src"


def find_openspec_pkg() -> pathlib.Path:
    npm_root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, check=True).stdout.strip()
    pkg = pathlib.Path(npm_root) / "@fission-ai" / "openspec"
    if not pkg.exists():
        sys.exit(f"OpenSpec не найден в {pkg}; укажите --openspec-dir")
    return pkg


class Literal(str):
    pass


def literal_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(Literal, literal_representer)


def build(base_dir: pathlib.Path, overlay_dir: pathlib.Path, out_dir: pathlib.Path) -> None:
    base = yaml.safe_load((base_dir / "schema.yaml").read_text())
    overlay = yaml.safe_load((overlay_dir / "overlay.yaml").read_text())
    by_id = {a["id"]: a for a in base["artifacts"]}

    artifacts = []
    for art_id, ov in overlay["artifacts"].items():
        ov = ov or {}
        if "define" in ov:
            # Артефакт, которого нет в spec-driven: описан в overlay целиком.
            art = {"id": art_id, **ov["define"]}
            art["instruction"] = Literal(art["instruction"].rstrip() + "\n")
            artifacts.append(art)
            continue
        art = dict(by_id[art_id])
        if "requires" in ov:
            art["requires"] = ov["requires"]
        if "description" in ov:
            art["description"] = ov["description"]
        instruction = art.get("instruction", "").rstrip()
        if ov.get("instruction_prefix"):
            instruction = ov["instruction_prefix"].rstrip() + "\n\n" + instruction
        if ov.get("instruction_suffix"):
            instruction += "\n\n" + ov["instruction_suffix"].rstrip()
        art["instruction"] = Literal(instruction + "\n")
        artifacts.append(art)

    schema = {
        "name": overlay["name"],
        "version": overlay.get("version", 1),
        "description": overlay["description"],
        "artifacts": artifacts,
    }
    if overlay.get("apply", True):
        schema["apply"] = base["apply"]

    if out_dir.exists():
        shutil.rmtree(out_dir)
    tpl_out = out_dir / "templates"
    tpl_out.mkdir(parents=True)
    for art in artifacts:
        tpl = art["template"]
        own = overlay_dir / "templates" / tpl
        src = own if own.exists() else base_dir / "templates" / tpl
        (tpl_out / tpl).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, tpl_out / tpl)
    with open(out_dir / "schema.yaml", "w") as f:
        f.write(f"# СГЕНЕРИРОВАНО tools/build-schemas.py из spec-driven + schemas-src/{overlay['name']}. Не править руками.\n")
        yaml.dump(schema, f, allow_unicode=True, sort_keys=False, width=1000)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--openspec-dir", type=pathlib.Path)
    p.add_argument("--out", type=pathlib.Path, default=ROOT / "schemas")
    args = p.parse_args()
    pkg = args.openspec_dir or find_openspec_pkg()
    base_dir = pkg / "schemas" / "spec-driven"
    version = yaml.safe_load((pkg / "package.json").read_text())["version"]
    for overlay_dir in sorted(SRC.iterdir()):
        if (overlay_dir / "overlay.yaml").exists():
            build(base_dir, overlay_dir, args.out / overlay_dir.name)
            print(f"built {overlay_dir.name} (base: spec-driven from openspec {version})")


if __name__ == "__main__":
    main()

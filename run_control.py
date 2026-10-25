#!/usr/bin/env python3
"""Controle externo de execução: status observável + pause/resume/cancel.

Arquivos no ``run_dir`` (tmp+rename atômico, sem escrita parcial):

- ``status.json``: fase, rodada, contadores, elapsed, stop, run_id, pid, UTC.
- ``control.json``: comando pendente ({pause,resume,cancel}); consumo único
  (vira ``control.taken.json``). JSON inválido vira ``control.invalid-*.json``
  (nunca apagado em silêncio).

PONTO DE INTEGRAÇÃO NO COORDENADOR (fase seguinte): instanciar
``RunControl(run_dir)`` e chamar ``poll()`` no início de cada rodada e entre
operações. ``pause`` -> persistir estado e encerrar com stop reason
``"paused"``; ``cancel`` -> stop reason ``"cancelled"``. A retomada usa
``--resume`` (o estado persistido é a fonte da verdade, não este módulo).

CLI: ``python run_control.py --run-dir DIR status|pause|resume|cancel``
Exit: 0 sucesso; 2 erro de uso/arquivo.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

COMMANDS = ("pause", "resume", "cancel")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


class RunControl:
    """Controle de UM run dir; sem estado global e sem apagar o run dir."""

    def __init__(self, run_dir, run_id=None):
        self.run_dir = Path(run_dir)
        self.status_path = self.run_dir / "status.json"
        self.control_path = self.run_dir / "control.json"
        self.taken_path = self.run_dir / "control.taken.json"
        self.run_id = run_id or self.run_dir.name

    # -- status ---------------------------------------------------------
    def write_status(self, *, phase: str, round_no: int | None = None,
                     counters: dict | None = None, elapsed_s: float | None = None,
                     stop: str | None = None, detail: str | None = None) -> dict:
        payload: dict = {"run_id": self.run_id, "phase": str(phase),
                         "updated_at": _utc_now(), "pid": os.getpid()}
        if round_no is not None:
            payload["round"] = round_no
        if counters is not None:
            payload["counters"] = counters
        if elapsed_s is not None:
            payload["elapsed_s"] = elapsed_s
        if stop is not None:
            payload["stop"] = stop
        if detail is not None:
            payload["detail"] = detail
        _atomic_write(self.status_path, payload)
        return payload

    def read_status(self) -> dict | None:
        try:
            data = json.loads(self.status_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    # -- controle -------------------------------------------------------
    def request(self, command: str) -> dict:
        command = str(command or "").strip().lower()
        if command not in COMMANDS:
            raise ValueError(f"invalid command {command!r} (expected {COMMANDS})")
        payload = {"command": command, "requested_at": _utc_now(),
                   "pid": os.getpid()}
        _atomic_write(self.control_path, payload)
        return payload

    def _quarantine(self) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = self.run_dir / f"control.invalid-{stamp}.json"
        try:
            os.replace(self.control_path, target)
        except OSError:
            pass
        return target

    def poll(self) -> str | None:
        """Comando pendente ou None; consome uma única vez."""
        try:
            raw = self.control_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError:
            return None
        try:
            data = json.loads(raw)
        except ValueError:
            self._quarantine()
            return None
        command = str(data.get("command") or "").strip().lower() \
            if isinstance(data, dict) else ""
        if command not in COMMANDS:
            self._quarantine()
            return None
        try:
            os.replace(self.control_path, self.taken_path)
        except FileNotFoundError:  # outro consumidor venceu a corrida
            return None
        return command

    def clear(self) -> None:
        """Remove status/controle do run dir; nunca o run dir em si."""
        paths = [self.control_path, self.taken_path, self.status_path]
        paths.extend(self.run_dir.glob("control.invalid-*.json"))
        for path in paths:
            try:
                path.unlink()
            except FileNotFoundError:
                continue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_control.py")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("command", choices=("status",) + COMMANDS)
    args = parser.parse_args(argv)
    control = RunControl(args.run_dir)
    if args.command == "status":
        status = control.read_status()
        if status is None:
            print(f"no status.json in {control.run_dir}", file=sys.stderr)
            return 2
        print(json.dumps(status, ensure_ascii=False, sort_keys=True))
        return 0
    control.request(args.command)
    print(f"{args.command} requested in {control.control_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

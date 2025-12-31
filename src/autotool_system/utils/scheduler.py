from __future__ import annotations


class Scheduler:
    def start(self) -> None:
        raise NotImplementedError("Scheduler is not implemented yet")

    def stop(self) -> None:
        raise NotImplementedError("Scheduler stop is not implemented yet")

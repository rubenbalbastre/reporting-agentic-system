from datetime import datetime, timezone


def main() -> None:
    # Local time (no external dependencies)
    now_local = datetime.now()

    # Readable ISO-like format without microseconds
    formatted = now_local.isoformat(timespec="seconds")

    print(formatted)


if __name__ == "__main__":
    main()

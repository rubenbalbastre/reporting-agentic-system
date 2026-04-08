from datetime import datetime


def main() -> None:
    now = datetime.now()
    formatted = now.strftime("%Y-%m-%d %H:%M:%S")
    print(f"Current date and time: {formatted}")


if __name__ == "__main__":
    main()

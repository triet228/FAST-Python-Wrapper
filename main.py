# main.py
from wrapper import FastWrapper


def main():
    with FastWrapper() as fast:
        result = fast.run()

    print(result)


if __name__ == "__main__":
    main()

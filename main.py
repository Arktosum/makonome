# main.py
from brain import chat
from config import ASSISTANT_NAME, USER_NAME


def main():
    print(f"\n{'='*40}")
    print(f"  {ASSISTANT_NAME} is online. Type 'quit' to exit.")
    print(f"{'='*40}\n")

    while True:
        try:
            user_input = input(f"{USER_NAME}: ").strip()

            if not user_input:
                continue
            if user_input.lower() in ["quit", "exit", "bye"]:
                print(f"\n{ASSISTANT_NAME}: Later. I'll remember everything.\n")
                break

            response = chat(user_input)
            print(f"\n{ASSISTANT_NAME}: {response}\n")

        except KeyboardInterrupt:
            print(f"\n\n{ASSISTANT_NAME}: Shutting down. See you soon.\n")
            break


if __name__ == "__main__":
    main()

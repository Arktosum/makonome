# main.py
from brain import chat
from config import ASSISTANT_NAME, USER_NAME
from voice.ears import listen
from voice.mouth import speak

def main():
    print(f"\n{'='*40}")
    print(f"  {ASSISTANT_NAME} is online.")
    print(f"  Speak to talk, say 'goodbye' to exit.")
    print(f"{'='*40}\n")

    # startup message
    startup = f"Hey {USER_NAME}! I'm here. What's up?"
    print(f"{ASSISTANT_NAME}: {startup}")
    speak(startup)

    while True:
        try:
            # listen for user input
            user_input = listen()

            if not user_input:
                continue

            # check for exit commands
            if any(word in user_input.lower() for word in ["goodbye", "bye mako", "shut down", "exit"]):
                farewell = f"Okay, talk soon {USER_NAME}! I'll remember everything."
                print(f"\n{ASSISTANT_NAME}: {farewell}\n")
                speak(farewell)
                break

            print(f"\n{USER_NAME}: {user_input}")

            # get response from brain
            response = chat(user_input)
            print(f"\n{ASSISTANT_NAME}: {response}\n")
            speak(response)

        except KeyboardInterrupt:
            print(f"\n\n{ASSISTANT_NAME}: Shutting down. See you soon!\n")
            break

if __name__ == "__main__":
    main()
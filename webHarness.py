from camoufox.sync_api import Camoufox
import time
from playwright.sync_api import TimeoutError
import subprocess
import sys

LAST_TEXT = ""
PROFILE_DIR = "./camoufox_profile"

def exec(command):
    print("executing......")
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )

    stdout = result.stdout
    stderr = result.stderr
    return_code = result.returncode

    print("Done executing")
    if return_code != 0:
        return stderr

    else:
        return stdout
    
def sys2web(page, prompt):
    page.locator("#prompt-textarea").click()

    page.evaluate("""
    (text) => navigator.clipboard.writeText(text)
    """, "exec() function call output: " + prompt)

    page.keyboard.press("Control+V")   # Windows/Linux
    # page.keyboard.press("Meta+V")    # macOS

    page.keyboard.press("Enter")


def wait_for_chatgpt_response(
    page,
    start_timeout=15,          # Wait for generation to start
    completion_timeout=300,    # Max total generation time
    stable_seconds=3           # Text must stop changing for N polls
):
    """
    Strategy:
    1. Wait for Stop button to appear.
    2. Wait for Stop button to disappear.
    3. If that fails, fall back to response-text stability detection.
    4. Hard timeout after completion_timeout seconds.
    """
    global LAST_TEXT
    print("Waiting for generation to start...")

    stop_button = page.get_by_test_id("stop-button")

    try:
        # STEP 1: Wait for generation to start
        stop_button.wait_for(
            state="visible",
            timeout=start_timeout * 1000
        )

        print("Generation started.")

        # STEP 2: Preferred path
        stop_button.wait_for(
            state="hidden",
            timeout=completion_timeout * 1000
        )

        print("Generation finished (stop button disappeared).")
        return True

    except TimeoutError:
        print("Stop button strategy failed.")
        print("Switching to text stability detection.")

    # STEP 3: Fallback strategy
    start_time = time.time()

    # last_text = ""
    stable_count = 0

    while True:

        # STEP 4: Global timeout
        if time.time() - start_time > completion_timeout:
            raise TimeoutError(
                f"Generation did not finish within "
                f"{completion_timeout} seconds."
            )

        current_text = page.locator("body").inner_text()

        if current_text == LAST_TEXT:
            stable_count += 1
        else:
            stable_count = 0
            LAST_TEXT = current_text

        if stable_count >= stable_seconds:
            print(
                "Generation finished "
                "(response text became stable)."
            )
            return True

        time.sleep(1)

with open("SystemPrompt.md", "r", encoding="utf-8") as file:
    content = file.read()

with open("Skills/SKILL.md", "r", encoding="utf-8") as file:
    skill = file.read()

with Camoufox(
    headless=False,
    humanize=True,
    persistent_context=True,
    user_data_dir=PROFILE_DIR
) as browser:

    page = browser.new_page()

    page.goto(
        "https://chatgpt.com/",
        wait_until="domcontentloaded",
        timeout=60000
    )

    editor = page.get_by_role(
        "textbox",
        name="Chat with ChatGPT"
    )

    editor.wait_for(
        state="visible",
        timeout=120000
    )

    input("select the session")
    user_input = input("How can I help you? ")

    page.locator("#prompt-textarea").click()

    page.evaluate("""
    (text) => navigator.clipboard.writeText(text)
    """, "System-Prompt:" + content + " User Task: " + user_input)

    page.keyboard.press("Control+V")   # Windows/Linux
    # page.keyboard.press("Meta+V")    # macOS

    page.keyboard.press("Enter")
    wait_for_chatgpt_response(page)

    generated_code = page.locator("pre code").last.inner_text()


    while generated_code != "END-OF-OPERATION":
        sys2web(page,exec(generated_code))
        wait_for_chatgpt_response(page)
        generated_code = page.locator("pre code").last.inner_text()

        
    # with open(
    #     "generated_script.py",
    #     "w",
    #     encoding="utf-8"
    # ) as f:
    #     f.write(generated_code)

    print("End-of-operation")
    input("Press Enter to close browser...")
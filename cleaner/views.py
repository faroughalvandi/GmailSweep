# cleaner/views.py
import imaplib
import email
from email.header import decode_header
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse

# دسته‌بندی‌های جیمیل
GMAIL_CATEGORIES = {
    "social": {"label": "Social", "raw": "category:social", "folder": "[Gmail]/Social"},
    "promotions": {"label": "Promotions", "raw": "category:promotions", "folder": "[Gmail]/Promotions"},
    "updates": {"label": "Updates", "raw": "category:updates", "folder": "[Gmail]/Updates"},
    "forums": {"label": "Forums", "raw": "category:forums", "folder": "[Gmail]/Forums"},
    "primary": {"label": "Primary (Inbox)", "raw": "category:primary", "folder": "INBOX"},
}

def decode_subject(subject):
    if not subject:
        return "(No Subject)"
    try:
        decoded = decode_header(subject)[0]
        if decoded[1]:
            return decoded[0].decode(decoded[1], errors="replace")
        return str(decoded[0])
    except:
        return str(subject)[:100]

# صفحه لاگین
def login_view(request):
    if request.method == "POST":
        email_addr = request.POST.get("email", "").strip()
        app_pass = request.POST.get("app_password", "")

        try:
            imap = imaplib.IMAP4_SSL("imap.gmail.com")
            imap.login(email_addr, app_pass)
            imap.logout()

            # ذخیره اطلاعات در سشن
            request.session["gmail_email"] = email_addr
            request.session["gmail_app_pass"] = app_pass
            request.session["authenticated"] = True
            request.session.modified = True  # این خط خیلی مهمه!

            messages.success(request, "Login successful! Welcome.")
            return redirect("dashboard")

        except Exception as e:
            messages.error(request, "Invalid email or App Password.")

    return render(request, "login.html")

# صفحه خروج
def logout_view(request):
    request.session.flush()
    messages.info(request, "You have been logged out.")
    return redirect("login")

# داشبورد اصلی
def dashboard(request):
    if not request.session.get("authenticated"):
        return redirect("login")
    
    return render(request, "index.html", {
        "categories": GMAIL_CATEGORIES,
        "user_email": request.session.get("gmail_email")
    })

# پیش‌نمایش و حذف
def preview_and_delete(request, category_key):
    if not request.session.get("authenticated"):
        return redirect("login")

    if category_key not in GMAIL_CATEGORIES:
        messages.error(request, "Invalid category.")
        return redirect("dashboard")

    cat = GMAIL_CATEGORIES[category_key]
    email_addr = request.session["gmail_email"]
    app_pass = request.session["gmail_app_pass"]

    # تعداد دلخواه (پیش‌فرض 100)
    try:
        count = int(request.GET.get("count", 100))
        count = max(1, min(count, 10000))
    except:
        count = 100

    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(email_addr, app_pass)

        # تلاش برای انتخاب فولدر یا استفاده از فیلتر X-GM-RAW
        try:
            folder = cat["folder"]
            select_folder = f'"{folder}"' if folder != "INBOX" else "INBOX"
            imap.select(select_folder)
            status, data = imap.search(None, "ALL")
        except:
            imap.select("INBOX")
            status, data = imap.search(None, f'X-GM-RAW "{cat["raw"]}"')

        all_ids = data[0].split()
        if not all_ids:
            imap.logout()
            messages.info(request, f"No emails found in {cat['label']}.")
            return redirect("dashboard")

        # فقط تعداد درخواستی از آخر (جدیدترین‌ها)
        latest_ids = all_ids[-count:]
        total_before = len(all_ids)

        # جمع‌آوری عنوان و فرستنده
        emails = []
        for msg_id in latest_ids:
            typ, msg_data = imap.fetch(msg_id, '(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])')
            if typ != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            subject = decode_subject(msg.get("Subject"))
            sender = (msg.get("From") or "Unknown").split("<")[0].strip()
            emails.append({"subject": subject, "sender": sender})

        # حذف واقعی
        if request.method == "POST" and request.POST.get("confirm") == "yes":
            ids_str = [mid.decode() for mid in latest_ids]
            imap.store(",".join(ids_str), "+FLAGS", "\\Deleted")
            imap.expunge()
            imap.logout()
            messages.success(request, f"Successfully deleted {len(latest_ids)} emails from {cat['label']}!")
            return redirect("dashboard")

        imap.logout()

        return render(request, "preview.html", {
            "category": cat["label"],
            "emails": emails,
            "count": len(emails),
            "requested_count": count,
            "before_count": total_before,
        })

    except Exception as e:
        messages.error(request, f"Connection failed: {str(e)}")
        return redirect("dashboard")
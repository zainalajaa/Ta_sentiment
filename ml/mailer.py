import os
import ssl
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

# Muat variabel dari file .env (bila ada)
load_dotenv()

# =========================================
# KONFIGURASI EMAIL (Gmail SMTP)
# =========================================
# Set kredensial lewat environment variable agar tidak hardcode:
#   export MAIL_USERNAME="emailkamu@gmail.com"
#   export MAIL_PASSWORD="app-password-16-digit"   (App Password, bukan password gmail biasa)
#   export MAIL_FROM_NAME="Sentiment App"          (opsional)
#
# Cara membuat App Password:
#   Akun Google -> Security -> 2-Step Verification (aktifkan) -> App passwords

SMTP_HOST = os.environ.get("MAIL_HOST", "live.smtp.mailtrap.io")
SMTP_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "Sentiment App")
# Alamat pengirim. Di Mailtrap sandbox boleh email apa saja (mis. no-reply@demo.com),
# karena username Mailtrap bukan alamat email asli.
MAIL_FROM = os.environ.get("MAIL_FROM", "no-reply@sentiment.app")


def send_reset_email(to_email, reset_link):
    """
    Kirim email berisi link reset password.
    Return (True, None) jika sukses, (False, pesan_error) jika gagal.
    """

    if not MAIL_USERNAME or not MAIL_PASSWORD:
        return (
            False,
            "Konfigurasi email belum di-set "
            "(MAIL_USERNAME / MAIL_PASSWORD)."
        )

    msg = EmailMessage()
    msg["Subject"] = "Reset Password - Sentiment App"
    msg["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
    msg["To"] = to_email

    # Versi teks polos (fallback)
    msg.set_content(
        "Halo,\n\n"
        "Kami menerima permintaan reset password untuk akun Anda.\n"
        f"Klik link berikut untuk mengatur password baru:\n\n{reset_link}\n\n"
        "Link ini berlaku selama 1 jam.\n"
        "Jika Anda tidak meminta reset password, abaikan email ini.\n\n"
        "Salam,\nSentiment App"
    )

    # Versi HTML
    msg.add_alternative(
        f"""\
<html>
  <body style="font-family: Arial, sans-serif; background:#f1f5f9; padding:24px;">
    <div style="max-width:480px; margin:auto; background:#fff; border-radius:16px; padding:32px;">
      <h2 style="color:#1e293b; margin-top:0;">Reset Password</h2>
      <p style="color:#475569;">Halo,</p>
      <p style="color:#475569;">
        Kami menerima permintaan reset password untuk akun Anda.
        Klik tombol di bawah untuk mengatur password baru.
      </p>
      <p style="text-align:center; margin:28px 0;">
        <a href="{reset_link}"
           style="background:#2563eb; color:#fff; text-decoration:none;
                  padding:12px 28px; border-radius:12px; font-weight:600;">
          Reset Password
        </a>
      </p>
      <p style="color:#94a3b8; font-size:13px;">
        Atau salin link berikut ke browser:<br>
        <a href="{reset_link}" style="color:#2563eb;">{reset_link}</a>
      </p>
      <p style="color:#94a3b8; font-size:13px;">
        Link ini berlaku selama 1 jam. Jika Anda tidak meminta reset
        password, abaikan email ini.
      </p>
    </div>
  </body>
</html>
""",
        subtype="html",
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
        return (True, None)

    except Exception as e:
        return (False, str(e))

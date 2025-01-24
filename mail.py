import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from models import db, Kartinas, KartinasISTiesibas, sis, Tiesibas
from flask import flash

def send_email(subject, recipient, message):
    """
    Izsūta e-pastu ar norādīto tēmu un saturu.
    """
    smtp_server = "smtp.example.com"  # Norādiet SMTP serveri
    smtp_port = 587  # Parasti 587 vai 465
    smtp_user = "your_email@example.com"  # Jūsu e-pasta adrese
    smtp_password = "your_password"  # Jūsu e-pasta parole

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        print(f"E-pasts veiksmīgi nosūtīts uz {recipient}")
    except Exception as e:
        print(f"Kļūda e-pasta izsūtīšanas laikā: {e}")


def notify_user_about_new_permissions(user_id, new_permissions):
    """
    Izsūta paziņojumu lietotājam par pievienotajām tiesībām.
    """
    user = Kartinas.query.filter_by(id=user_id).first()

    if not user or not user.epasts:
        print("Lietotājam nav norādīts e-pasts vai lietotājs neeksistē.")
        return

    # Esošās tiesības
    existing_permissions = db.session.query(sis.is_name, Tiesibas.t_name).join(KartinasISTiesibas, KartinasISTiesibas.is_id == sis.id).join(Tiesibas, KartinasISTiesibas.tiesibas_id == Tiesibas.id).filter(KartinasISTiesibas.user_id == user_id).all()

    # Formatē esošās un jaunās tiesības
    message = "<h3>Tava profila tiesību atjauninājumi</h3>"
    message += "<p><strong>Esošās tiesības:</strong></p><ul>"

    for is_name, t_name in existing_permissions:
        if (is_name, t_name) in new_permissions:
            message += f"<li><strong>{is_name} - {t_name} (Jauns)</strong></li>"
        else:
            message += f"<li>{is_name} - {t_name}</li>"

    message += "</ul>"

    # Sūtīt e-pastu
    send_email(
        subject="Tavas tiesības ir atjauninātas",
        recipient=user.epasts,
        message=message
    )

# Funkcija, kas jāizsauc, pievienojot tiesības
def on_permissions_added(user_id, new_permissions):
    """
    Automātiski izsūta paziņojumus, kad tiek pievienotas jaunas tiesības.
    """
    try:
        notify_user_about_new_permissions(user_id, new_permissions)
        flash("Lietotājs tika informēts par jaunajām tiesībām.", "success")
    except Exception as e:
        print(f"Kļūda paziņojuma izsūtīšanā: {e}")
        flash("Kļūda paziņojuma izsūtīšanā.", "danger")

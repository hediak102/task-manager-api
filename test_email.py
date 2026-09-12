from app.tasks.email import send_email

send_email(
    to="hediakaichi2@gmail.com",
    subject="Test SMTP",
    body="Si tu reçois ça, la config Gmail fonctionne."
)
print("Email envoyé (ou pas d'erreur en tout cas)")
from django.forms import Form, TextInput, EmailField, CharField, Textarea


class ContactForm(Form):
    from_email = EmailField(
        required=True,
        widget=TextInput(attrs={"class": "form-control", "placeholder": "Votre email", "autocomplete": "email"})
    )
    subject = CharField(
        required=True,
        widget=TextInput(attrs={"class": "form-control", "placeholder": "Objet"})
    )
    message = CharField(
        required=True,
        widget=Textarea(attrs={"class": "form-control", "rows": 6, "placeholder": "Votre message"})
    )

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Activity, Customer


class BootstrapFormMixin:
    """Adds Bootstrap classes to every widget, so templates stay simple."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.RadioSelect, forms.CheckboxInput)):
                continue
            css = "form-select" if isinstance(widget, forms.Select) else "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def full_clean(self):
        super().full_clean()
        # Highlight fields that failed validation.
        for name in self.errors:
            if name in self.fields:
                attrs = self.fields[name].widget.attrs
                attrs["class"] = f"{attrs.get('class', '')} is-invalid".strip()


class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, user):
        return user.get_full_name() or user.username


class SignUpForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class CustomerForm(BootstrapFormMixin, forms.ModelForm):
    owner = UserChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("first_name", "username"),
        required=False,
        empty_label="Unassigned",
    )

    class Meta:
        model = Customer
        fields = (
            "first_name",
            "last_name",
            "company",
            "job_title",
            "status",
            "owner",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "zipcode",
            "notes",
        )
        widgets = {
            "phone": forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


class ActivityForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Activity
        fields = ("kind", "subject", "details")
        widgets = {
            "kind": forms.RadioSelect,
            "subject": forms.TextInput(attrs={"placeholder": "e.g. Intro call about pricing"}),
            "details": forms.Textarea(attrs={"rows": 3, "placeholder": "What was discussed? Any next steps?"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Status changes are logged automatically, not by hand.
        self.fields["kind"].choices = [
            choice for choice in Activity.Kind.choices if choice[0] != Activity.Kind.STATUS
        ]

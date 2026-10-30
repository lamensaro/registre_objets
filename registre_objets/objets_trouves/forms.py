from django import forms
from django.utils import timezone

from .models import ObjetTrouve, Reclamation


class ObjetTrouveForm(forms.ModelForm):
    class Meta:
        model = ObjetTrouve
        fields = ["categorie", "description", "image", "lieu_decouverte", "date_decouverte"]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "date_decouverte": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_date_decouverte(self):
        date = self.cleaned_data["date_decouverte"]
        if date > timezone.localdate():
            raise forms.ValidationError("La date de découverte ne peut pas être dans le futur.")
        return date


class ReclamationForm(forms.ModelForm):
    class Meta:
        model = Reclamation
        fields = ["description_complementaire"]
        widgets = {
            "description_complementaire": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Décrivez des détails que seul le propriétaire peut connaître."}
            ),
        }


class NoteDecisionForm(forms.Form):
    note_decision = forms.CharField(
        label="Note (facultative)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

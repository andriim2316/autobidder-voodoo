from django import forms
from django.core.exceptions import ValidationError

from autobidder_app.models import Domain, Bet


class ClaimBetForm(forms.Form):
    domain_id = forms.IntegerField(widget=forms.HiddenInput())
    expiration_date = forms.DateField(widget=forms.HiddenInput())
    max_bet = forms.IntegerField(
        label="Max Bet",
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
            'style': 'width: 70px; font-size: 12px;',
            'required': True,
            'value': 900  # Default value
        })
    )

    def clean_domain_name(self):
        domain_name = self.cleaned_data.get('domain_name')
        if not Domain.objects.filter(name=domain_name).exists():
            raise forms.ValidationError("Domain does not exist.")
        return domain_name

    def save(self, commit=True):
        domain_name = self.cleaned_data.get('domain_name')
        max_bet = self.cleaned_data.get('max_bet')

        domain = Domain.objects.get(name=domain_name)
        bet, created = Bet.objects.get_or_create(domain_id=domain.id, defaults={'max_bet': max_bet})

        if not created:
            bet.max_bet = max_bet
            if commit:
                bet.save()
        return bet



class BetForm(forms.ModelForm):
    class Meta:
        model = Bet
        fields = ['max_bet']
        widgets = {
            'max_bet': forms.NumberInput(attrs={'min': '900', 'step': '50', 'oninput': 'validateInput(this)'})
        }


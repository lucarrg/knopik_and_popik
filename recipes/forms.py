from django import forms


class RecipeNoteForm(forms.Form):
    text = forms.CharField()

    def clean_text(self):
        text = self.cleaned_data['text'].strip()
        if not text:
            raise forms.ValidationError('Введите текст заметки.')
        return text

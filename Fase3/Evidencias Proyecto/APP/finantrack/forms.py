from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegistroUsuarioForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, label="Nombre")
    last_name = forms.CharField(max_length=30, required=True, label="Apellido")
    email = forms.EmailField(max_length=254, required=True, label="Correo electrónico")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

class PerfilUsuarioForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, label="Nombre")
    last_name = forms.CharField(max_length=30, required=True, label="Apellido")
    email = forms.EmailField(max_length=254, required=True, label="Correo electrónico")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(), required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password']

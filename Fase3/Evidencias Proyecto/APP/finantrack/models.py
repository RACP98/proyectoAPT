from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Transaccion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    fecha = models.DateField()
    detalle = models.TextField()
    categoria = models.CharField(max_length=100, blank=True, null=True)
    banco = models.CharField(max_length=100, blank=True, null=True)
    cargo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    abono = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.fecha} - {self.detalle}"

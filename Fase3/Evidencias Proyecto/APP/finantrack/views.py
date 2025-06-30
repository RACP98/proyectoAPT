from django.shortcuts import render, redirect
from django.contrib import messages
import pandas as pd
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from .models import Transaccion
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from finantrack.forms import RegistroUsuarioForm, PerfilUsuarioForm
import json
from django.core.serializers.json import DjangoJSONEncoder

def login(request):
    context = {}
    return render(request, 'finantrack/login.html', context)

def base(request):
    context = {}
    return render(request, 'finantrack/base.html', context)

def custom_logout(request):
    logout(request)
    return redirect('index')

def categorizar(descripcion):
    descripcion = descripcion.lower()
    if 'supermercado' in descripcion or 'líder' in descripcion or 'jumbo' in descripcion or 'tottus' in descripcion:
        return 'Supermercado'
    if any(palabra in descripcion for palabra in ['farmacia', 'salcobrand', 'sb', ' ino ', 'cruz verde', 'clinica']):
        return 'Salud/Farmacia'
    if any(palabra in descripcion for palabra in ['uber', 'cabify', 'buses']):
        return 'Transporte'
    if any(palabra in descripcion for palabra in ['starbucks', 'domino','donalds', 'dg', 'carne', 'jireh', 'papa john']):
        return 'Comida'
    if any(palabra in descripcion for palabra in ['agua', 'enel', 'movistar', 'wom', 'telefonica', 'claro']):
        return 'Servicios Básicos'
    if any(palabra in descripcion for palabra in ['cajero']):
        return 'Giro'
    if any(palabra in descripcion for palabra in ['crédito','hipotecario']):
        return 'Credito'
    if any(palabra in descripcion for palabra in ['transf','tef']):
        return 'Transferencias'
    if 'komax' in descripcion:
        return 'Sueldo'
    return 'Otros'

def index(request):
    context = {}
    if request.method == 'POST' and 'archivo' in request.FILES:
        archivo = request.FILES['archivo']
        try:
            if archivo.name.endswith('.xlsx'):
                preview = pd.read_excel(archivo, engine='openpyxl', nrows=1, header=None) # Elimina separadores de miles
                # Extraer las 10 primeras celdas de la primera columna
                primeras_celdas = preview.iloc[:, 0].astype(str).str.strip().str.lower().tolist()
                print("Primeras celdas leídas:", primeras_celdas)

                # Detectar por contenido en las primeras celdas
                if any("fecha" in celda for celda in primeras_celdas):
                    df = pd.read_excel(archivo, engine='openpyxl', skiprows=0, dtype=str)
                    bco = "Falabella"
                    print("Archivo detectado: Falabella")

                elif any("últimos movimientos" in celda for celda in primeras_celdas):
                    df = pd.read_excel(archivo, engine='openpyxl', skiprows=7, dtype=str)
                    bco = "BCI"
                    print("Archivo detectado: BCI")

                elif any("rodrigo andres concha pezoa" in celda for celda in primeras_celdas):
                    df = pd.read_excel(archivo, engine='openpyxl', skiprows=2, dtype=str)
                    bco = "Santander"
                    print("Archivo detectado: Santander",bco)

                elif any("cartola cuentarut" in celda for celda in primeras_celdas):
                    df = pd.read_excel(archivo, engine='openpyxl', skiprows=13, dtype=str)
                    bco = "Estado"
                    print("Archivo detectado: Banco Estado")
                else:
                    raise ValueError("No se pudo detectar el formato de la cartola. Revisa el archivo.")

            elif archivo.name.endswith('.xls'):
                preview = pd.read_excel(archivo, engine='xlrd', nrows=1, header=None)
                primeras_celdas = preview.iloc[:, 0].astype(str).str.strip().str.lower().tolist()
                print("Primeras celdas leídas:", primeras_celdas)
                
                # Aquí detectas el banco
                if any("id" in celda for celda in primeras_celdas):
                    df = pd.read_excel(archivo, engine='xlrd', skiprows=10, dtype=str)
                    bco = "ITAU"
                    print("Archivo detectado: ITAU")


            elif archivo.name.endswith('.csv'):
                df = pd.read_csv(archivo)
            else:
                messages.error(request, 'Formato no soportado. Sube un archivo .xls, .xlsx o .csv.')
                return redirect('index')

            # Limpiar nombres de columnas
            df.columns = df.columns.str.strip()
            df.columns = df.columns.str.replace(r'[^\w\s]', '', regex=True)  # Quita $ y símbolos
            df.columns = df.columns.str.replace(r'\s+', ' ', regex=True)  # Espacios múltiples
            df.columns = df.columns.str.lower().str.strip()

            # Renombrar columnas clave
            df.rename(columns={
                'fecha transacción': 'Fecha',
                'fecha': 'Fecha',
                'descripción': 'Descripción',
                'descripcion': 'Descripción',
                'detalle': 'Descripción',
                'movimientos': 'Descripción',
                'cargo': 'Cargo',
                'abono': 'Abono',
                'cargos': 'Cargo',
                'abonos': 'Abono'
            }, inplace=True)

            # Verificación mínima
            if 'Descripción' not in df.columns:
                raise Exception("Columna requerida no encontrada: 'Descripción'")
            if 'Cargo' not in df.columns:
                raise Exception("Columna requerida no encontrada: 'Cargo'")
            if 'Abono' not in df.columns:
                raise Exception("Columna requerida no encontrada: 'Abono'")

            # Limpiar y convertir montos
            for col in ['Cargo', 'Abono']:
                df[col] = (
                    df[col].astype(str)
                        .str.replace('.', '', regex=False)    # Elimina separadores de miles
                        .str.replace(',', '.', regex=False)   # Cambia coma decimal por punto
                        .str.replace(r'\s+', '', regex=True) 
                        .str.replace(r'[^\w\s]', '', regex=True) # Elimina espacios en blanco
                        .replace('nan', '0')                     # Vacíos a cero
                        .astype(float)                        # Convierte a float
                )

            # Procesar fechas si existe
            if 'Fecha' in df.columns:
                df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')

            # Categorizar movimientos
            df['Categoría'] = df['Descripción'].apply(categorizar)

            # Guardar en base de datos si usuario está autenticado
            if request.user.is_authenticated:
                for _, row in df.iterrows():
                    # Verifica si la transacción ya existe para ese usuario
                    existe = Transaccion.objects.filter(
                        usuario=request.user,
                        fecha=row['Fecha'],
                        detalle=row['Descripción'],
                        banco=bco,
                        cargo=row['Cargo'],
                        abono=row['Abono']
                    ).exists()

                    if not existe:
                        Transaccion.objects.create(
                            usuario=request.user,
                            fecha=row['Fecha'],
                            detalle=row['Descripción'],
                            categoria=row['Categoría'],
                            banco=bco,
                            cargo=row['Cargo'],
                            abono=row['Abono']
                        )


            # Agrupar gastos
            gastos = df[df['Cargo'] > 0].groupby('Categoría')['Cargo'].sum().sort_values(ascending=False).to_dict()
            abono = df[df['Abono'] > 0].groupby('Categoría')['Abono'].sum().sort_values(ascending=False).to_dict()
            gastos_labels = list(gastos.keys())
            gastos_values = list(gastos.values())
            ingresos_labels = list(abono.keys())
            ingresos_values = list(abono.values())
            context = {
                'datos': df.to_dict(orient='records'),
                'saldo_actual': df['Abono'].sum() - df['Cargo'].sum(),
                'total_abonos': df['Abono'].sum(),
                'total_cargos': df['Cargo'].sum(),
                'fechas': df['Fecha'].tolist() if 'Fecha' in df.columns else [],
                'saldos': [],
                'gastos_categoria': gastos,
                'abonos_categoria': abono,
                'bco' : bco,
                'gastos_labels': json.dumps(gastos_labels),
                'gastos_values': json.dumps(gastos_values, cls=DjangoJSONEncoder),
                'ingresos_labels': json.dumps(ingresos_labels),
                'ingresos_values': json.dumps(ingresos_values, cls=DjangoJSONEncoder),
            }
            print("Gastos Labels:", gastos_labels)
            print("Gastos Values:", gastos_values)
            print("Ingresos Labels:", ingresos_labels)
            print("Ingresos Values:", ingresos_values)

            messages.success(request, '¡Cartola cargada exitosamente!', )

        except Exception as e:
            messages.error(request, f'Ocurrió un error al procesar el archivo: {str(e)}')

    return render(request, 'finantrack/index.html', context)

def registro(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request)  # Inicia sesión automáticamente
            return redirect('login')  # Redirige al perfil
    else:
        form = RegistroUsuarioForm()
    return render(request, 'finantrack/registro.html', {'form': form})

@login_required
def dashboard(request):
    transacciones = Transaccion.objects.filter(usuario=request.user)

    total_abonos = transacciones.aggregate(Sum('abono'))['abono__sum'] or 0
    total_cargos = transacciones.aggregate(Sum('cargo'))['cargo__sum'] or 0
    saldo_actual = total_abonos - total_cargos

    # Totales por banco
    bancos_data = transacciones.values('banco').annotate(
        total_cargos=Sum('cargo'),
        total_abonos=Sum('abono')
    )

    resumen_por_banco = []
    for banco in bancos_data:
        resumen_por_banco.append({
            'banco': banco['banco'],
            'ingresos': banco['total_abonos'] or 0,
            'egresos': banco['total_cargos'] or 0,
            'saldo': (banco['total_abonos'] or 0) - (banco['total_cargos'] or 0)
        })

    # Agrupar gastos e ingresos por categoría
    gastos_categoria = transacciones.filter(cargo__gt=0).values('categoria').annotate(total=Sum('cargo')).order_by('-total')
    ingresos_categoria = transacciones.filter(abono__gt=0).values('categoria').annotate(total=Sum('abono')).order_by('-total')

    # Datos para Chart.js
    gastos_labels = [g['categoria'] for g in gastos_categoria if g['total'] > 0]
    gastos_values = [float(g['total']) for g in gastos_categoria if g['total'] > 0]

    ingresos_labels = [i['categoria'] for i in ingresos_categoria if i['total'] > 0]
    ingresos_values = [float(i['total']) for i in ingresos_categoria if i['total'] > 0]

    detalles_categoria = {}
    tipos_categoria = {}

    categorias = set(transacciones.values_list('categoria', flat=True))

    for cat in categorias:
        trans_list = transacciones.filter(categoria=cat)
        detalles_categoria[cat] = trans_list
        tipos_categoria[cat] = "gasto" if trans_list.filter(cargo__gt=0).exists() else "ingreso"

    # Transacciones separadas por tipo
    transacciones_ingresos = list(transacciones.filter(abono__gt=0).values())
    transacciones_egresos = list(transacciones.filter(cargo__gt=0).values())

    
    context = {
        'total_abonos': total_abonos,
        'total_cargos': total_cargos,
        'saldo_actual': saldo_actual,
        'gastos_categoria': gastos_categoria,
        'ingresos_categoria': ingresos_categoria,
        'detalles_categoria': detalles_categoria,
        'tipos_categoria': tipos_categoria,
        'resumen_por_banco': resumen_por_banco,
        'gastos_labels': json.dumps(gastos_labels),
        'gastos_values': json.dumps(gastos_values, cls=DjangoJSONEncoder),
        'ingresos_labels': json.dumps(ingresos_labels),
        'ingresos_values': json.dumps(ingresos_values, cls=DjangoJSONEncoder),
    }
    return render(request, 'finantrack/dashboard.html', context)

@login_required
def ver_transacciones(request, tipo):
    transacciones = Transaccion.objects.filter(usuario=request.user).order_by('-fecha')
    if tipo == 'gastos':
        transacciones = transacciones.filter(cargo__gt=0)
        titulo = "Detalle de Gastos"
        categorias = (
            transacciones
            .values_list('categoria', flat=True)
            .distinct()
            .order_by('categoria')
        )
    else:
        transacciones = transacciones.filter(abono__gt=0)
        titulo = "Detalle de Ingresos"
        categorias = (
            transacciones
            .values_list('categoria', flat=True)
            .distinct()
            .order_by('categoria')
        )
    return render(request, 'finantrack/detalle_transacciones.html', {
        'transacciones': transacciones,
        'categorias': categorias,
        'titulo': titulo
    })

@login_required
def perfil(request):
    user = request.user
    if request.method == 'POST':
        form = PerfilUsuarioForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()
            messages.success(request, 'Perfil actualizado exitosamente.')
            return redirect('login')  # Asegúrate de tener la URL 'perfil'
    else:
        form = PerfilUsuarioForm(instance=user)
    return render(request, 'finantrack/perfil.html', {
        'form': form,
        'username': user.username
    })
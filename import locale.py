import locale

try:
    locale.setlocale(locale.LC_ALL, 'es_CO.UTF-8')
    print("El locale es válido.")
except locale.Error:
    print("El locale no está disponible.")

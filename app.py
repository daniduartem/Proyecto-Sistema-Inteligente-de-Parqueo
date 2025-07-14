from flask import Flask, render_template, request, redirect, flash
import pyodbc
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'clave_segura'

# Parámetros del sistema
TARIFA_HORA = 10.0
MAX_HORAS_PERMITIDAS = 10

# Conexión a base de datos
class BaseDatos:
    def __init__(self):
        self.con = pyodbc.connect(
            r'DRIVER={SQL Server};SERVER=EV\SQLEXPRESS;DATABASE=ParqueoDB;Trusted_Connection=yes;'
        )
        self.cursor = self.con.cursor()

    def ejecutar(self, sql, params=()):
        self.cursor.execute(sql, params)
        self.con.commit()

    def consultar(self, sql, params=()):
        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

# Clase Persona
class Persona(BaseDatos):
    def registrar(self, cedula, nombre, apellido, telefono, direccion):
        consulta = "SELECT FechaRegistro FROM Persona WHERE Cedula=?"
        resultado = self.consultar(consulta, (cedula,))
        if resultado and datetime.now() - resultado[0][0] < timedelta(hours=24):
            return "Esta persona ya está registrada y aún no ha transcurrido el tiempo permitido."
        sql = ("INSERT INTO Persona (Cedula, Nombre, Apellido, Telefono, Direccion, FechaRegistro) "
               "VALUES (?, ?, ?, ?, ?, GETDATE());")
        self.ejecutar(sql, (cedula, nombre, apellido, telefono, direccion))
        return "Persona registrada correctamente."

# Clase Vehiculo con validación estricta
class Vehiculo(BaseDatos):
    def registrar(self, placa, marca, modelo, cedula):
        existe_propietario = self.consultar("SELECT 1 FROM Persona WHERE Cedula=?", (cedula,))
        if not existe_propietario:
            return f"Error: La cédula '{cedula}' no está registrada."

        existe_placa = self.consultar("SELECT 1 FROM Vehiculo WHERE Placa=?", (placa,))
        if existe_placa:
            return f"Error: La placa '{placa}' ya está registrada en el sistema."

        sql = ("INSERT INTO Vehiculo (Placa, Marca, Modelo, PropietarioCedula, FechaRegistro) "
               "VALUES (?, ?, ?, ?, GETDATE());")
        self.ejecutar(sql, (placa, marca, modelo, cedula))
        return "Vehículo registrado correctamente."

# Clase Espacio
class Espacio(BaseDatos):
    def obtener_matriz(self):
        resultado = self.consultar("SELECT IDEspacio, Ocupado FROM Espacio ORDER BY IDEspacio")
        matriz = [[None for _ in range(5)] for _ in range(5)]
        for i in range(5):
            for j in range(5):
                index = i * 5 + j
                if index < len(resultado):
                    matriz[i][j] = resultado[index]
        return matriz

    def espacio_disponible(self, id_espacio):
        resultado = self.consultar("SELECT Ocupado FROM Espacio WHERE IDEspacio=?", (id_espacio,))
        return resultado and resultado[0][0] == 0

    def marcar_ocupado(self, id_espacio, placa):
        self.ejecutar("UPDATE Espacio SET Ocupado=1, VehiculoPlaca=? WHERE IDEspacio=?", (placa, id_espacio))

    def hay_espacio_libre(self):
        resultado = self.consultar("SELECT COUNT(*) FROM Espacio WHERE Ocupado=0")
        return resultado[0][0] > 0

# Clase Reservacion
class Reservacion(BaseDatos):
    def registrar(self, cedula, placa, id_espacio, fecha, hora_entrada):
        espacio = Espacio()
        persona = self.consultar("SELECT 1 FROM Persona WHERE Cedula=?", (cedula,))
        if not persona:
            return f"Error: La cédula '{cedula}' no está registrada."

        vehiculo = self.consultar("SELECT 1 FROM Vehiculo WHERE Placa=?", (placa,))
        if not vehiculo:
            return f"Error: La placa '{placa}' no está registrada."

        if not espacio.espacio_disponible(id_espacio):
            if not espacio.hay_espacio_libre():
                self.ejecutar("INSERT INTO ColaEspera (Cedula, Placa) VALUES (?, ?)", (cedula, placa))
                return "Todos los espacios están ocupados. Se agregó a la cola de espera. Intente de nuevo mas tarde"
            else:
                return f"Espacio '{id_espacio}' está ocupado. Elija otro."

        espacio.marcar_ocupado(id_espacio, placa)
        sql = ("INSERT INTO Reservacion (CedulaPropietario, IDEspacio, Placa, Fecha, HoraEntrada) "
               "VALUES (?, ?, ?, ?, ?)")
        self.ejecutar(sql, (cedula, id_espacio, placa, fecha, hora_entrada))
        return "Reservación registrada correctamente."

# Clase Factura
class Factura(BaseDatos):
    def generar(self, id_reservacion, hora_salida):
        resultado = self.consultar("SELECT Fecha, HoraEntrada FROM Reservacion WHERE IDReservacion=?", (id_reservacion,))
        if not resultado:
            return f"Error: El ID de reservación '{id_reservacion}' no está registrado."

        fecha, hora_entrada = resultado[0]
        try:
            entrada = datetime.strptime(f"{fecha} {hora_entrada}", "%Y-%m-%d %H:%M")
            salida = datetime.strptime(hora_salida, "%Y-%m-%dT%H:%M")
        except ValueError:
            return "Error: Formato de hora inválido."

        duracion = max((salida - entrada).total_seconds() / 3600, 0.01)
        if duracion > MAX_HORAS_PERMITIDAS:
            return f"Error: Excede el límite de uso del parque (máximo {MAX_HORAS_PERMITIDAS} horas)."

        total = duracion * TARIFA_HORA
        self.ejecutar("UPDATE Reservacion SET HoraSalida=? WHERE IDReservacion=?", (hora_salida.split("T")[1], id_reservacion))
        self.ejecutar("INSERT INTO Factura (IDReservacion, HorasUsadas, TotalPagar) VALUES (?, ?, ?)",
                      (id_reservacion, duracion, total))
        return f"Factura generada por ${total:.2f} por {duracion:.2f} horas."

# Rutas de Flask
@app.route('/')
def inicio():
    return redirect('/estado_parqueo')

@app.route('/estado_parqueo')
def estado_parqueo():
    matriz = Espacio().obtener_matriz()
    return render_template('index.html', matriz=matriz)

@app.route('/registrar_persona', methods=['POST'])
def registrar_persona():
    datos = request.form
    mensaje = Persona().registrar(datos['cedula'], datos['nombre'], datos['apellido'], datos['telefono'], datos['direccion'])
    flash(mensaje)
    return redirect('/estado_parqueo')

@app.route('/registrar_vehiculo', methods=['POST'])
def registrar_vehiculo():
    datos = request.form
    mensaje = Vehiculo().registrar(datos['placa'], datos['marca'], datos['modelo'], datos['cedula_propietario'])
    flash(mensaje)
    return redirect('/estado_parqueo')

@app.route('/reservar', methods=['POST'])
def reservar():
    datos = request.form
    mensaje = Reservacion().registrar(datos['cedula_reserva'], datos['placa_reserva'], datos['espacio'], datos['fecha'], datos['hora_entrada'])
    flash(mensaje)
    return redirect('/estado_parqueo')

@app.route('/facturar', methods=['POST'])
def facturar():
    datos = request.form
    mensaje = Factura().generar(datos['id_reservacion'], datos['hora_salida'])
    flash(mensaje)
    return redirect('/estado_parqueo')

if __name__ == '__main__':
    app.run(debug=True)
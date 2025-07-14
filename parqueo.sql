-- Crear la base de datos
CREATE DATABASE ParqueoDB;
GO
USE ParqueoDB;
GO

-- Tabla Persona
CREATE TABLE Persona (
    Cedula VARCHAR(20) NOT NULL PRIMARY KEY,
    Nombre NVARCHAR(50) NOT NULL,
    Apellido NVARCHAR(50) NOT NULL,
    Telefono VARCHAR(20),
    Direccion NVARCHAR(100),
    FechaRegistro DATETIME NOT NULL DEFAULT GETDATE()
);

-- Tabla Vehiculo
CREATE TABLE Vehiculo (
    Placa VARCHAR(10) NOT NULL PRIMARY KEY,
    Marca NVARCHAR(50) NOT NULL,
    Modelo NVARCHAR(50) NOT NULL,
    PropietarioCedula VARCHAR(20) NOT NULL,
    FechaRegistro DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_Vehiculo_Persona FOREIGN KEY (PropietarioCedula) REFERENCES Persona(Cedula)
);

-- Tabla Espacio
CREATE TABLE Espacio (
    IDEspacio VARCHAR(10) NOT NULL PRIMARY KEY,
    Ocupado BIT NOT NULL DEFAULT 0,
    VehiculoPlaca VARCHAR(10),
    CONSTRAINT FK_Espacio_Vehiculo FOREIGN KEY (VehiculoPlaca) REFERENCES Vehiculo(Placa)
);

-- Insertar 25 espacios
DECLARE @i INT = 1;
WHILE @i <= 25
BEGIN
    INSERT INTO Espacio (IDEspacio, Ocupado)
    VALUES (CONCAT('P', RIGHT('0' + CAST(@i AS VARCHAR), 2)), 0);
    SET @i += 1;
END;

-- Tabla Reservacion con hora de entrada/salida
CREATE TABLE Reservacion (
    IDReservacion INT PRIMARY KEY IDENTITY(1,1),
    CedulaPropietario VARCHAR(20) NOT NULL,
    IDEspacio VARCHAR(10) NOT NULL,
    Placa VARCHAR(10) NOT NULL,
    Fecha DATE NOT NULL,
    HoraEntrada VARCHAR(5) NOT NULL, -- Formato HH:MM
    HoraSalida VARCHAR(5),
    CONSTRAINT FK_Reservacion_Persona FOREIGN KEY (CedulaPropietario) REFERENCES Persona(Cedula),
    CONSTRAINT FK_Reservacion_Espacio FOREIGN KEY (IDEspacio) REFERENCES Espacio(IDEspacio),
    CONSTRAINT FK_Reservacion_Vehiculo FOREIGN KEY (Placa) REFERENCES Vehiculo(Placa)
);

-- Tabla Factura
CREATE TABLE Factura (
    IDFactura INT PRIMARY KEY IDENTITY(1,1),
    IDReservacion INT NOT NULL,
    FechaGeneracion DATETIME NOT NULL DEFAULT GETDATE(),
    HorasUsadas DECIMAL(6,2) NOT NULL,
    TotalPagar MONEY NOT NULL,
    CONSTRAINT FK_Factura_Reservacion FOREIGN KEY (IDReservacion) REFERENCES Reservacion(IDReservacion)
);

-- Tabla ColaEspera
CREATE TABLE ColaEspera (
    ID INT PRIMARY KEY IDENTITY(1,1),
    Cedula VARCHAR(20) NOT NULL,
    Placa VARCHAR(10) NOT NULL,
    FechaIngreso DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_Cola_Persona FOREIGN KEY (Cedula) REFERENCES Persona(Cedula),
    CONSTRAINT FK_Cola_Vehiculo FOREIGN KEY (Placa) REFERENCES Vehiculo(Placa)
);

-- Tabla para pilas de estacionamiento en fila
CREATE TABLE PilaEstacionamiento (
    IDFila INT NOT NULL,
    IDEspacio VARCHAR(10) NOT NULL,
    Placa VARCHAR(10) NOT NULL,
    PosicionEnPila INT NOT NULL,
    PRIMARY KEY (IDFila, PosicionEnPila),
    CONSTRAINT FK_Pila_Vehiculo FOREIGN KEY (Placa) REFERENCES Vehiculo(Placa),
    CONSTRAINT FK_Pila_Espacio FOREIGN KEY (IDEspacio) REFERENCES Espacio(IDEspacio)
);

-- MERGE ejemplo para procesar vehículo
DECLARE @Placa VARCHAR(10) = 'ABC123';
DECLARE @Marca NVARCHAR(50) = 'Toyota';
DECLARE @Modelo NVARCHAR(50) = 'Corolla';
DECLARE @CedulaPropietario VARCHAR(20) = '123456789';

IF EXISTS (SELECT 1 FROM Persona WHERE Cedula = @CedulaPropietario)
BEGIN
    MERGE Vehiculo AS target
    USING (SELECT @Placa AS Placa, @Marca AS Marca, @Modelo AS Modelo, @CedulaPropietario AS PropietarioCedula) AS source
    ON target.Placa = source.Placa
    WHEN MATCHED THEN 
        UPDATE SET 
            Marca = source.Marca,
            Modelo = source.Modelo,
            PropietarioCedula = source.PropietarioCedula,
            FechaRegistro = GETDATE()
    WHEN NOT MATCHED THEN
        INSERT (Placa, Marca, Modelo, PropietarioCedula, FechaRegistro)
        VALUES (source.Placa, source.Marca, source.Modelo, source.PropietarioCedula, GETDATE());

    PRINT 'Vehículo procesado correctamente.';
END
ELSE
BEGIN
    PRINT 'Error: El propietario con la cédula proporcionada no está registrado.';
END;
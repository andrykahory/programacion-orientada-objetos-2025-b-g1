import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

# ===================== Configuración =====================
ARCHIVO_SOCIOS = Path("socios.json")
ARCHIVO_MATERIALES = Path("materiales.json")
ARCHIVO_PRESTAMOS = Path("prestamos.json")

DIAS_LIMITE = 7
MULTA_DIA = 1500


# ===================== Modelos =====================
@dataclass
class Socio:
    documento: str
    nombre: str


@dataclass
class Material:
    titulo: str
    categoria: str
    stock: int


@dataclass
class Prestamo:
    doc: str
    titulo: str
    fecha: str   # guardamos como string para JSON


# ===================== Persistencia =====================
class BaseDatos:
    def __init__(self):
        self.socios: list[Socio] = []
        self.materiales: list[Material] = []
        self.prestamos: list[Prestamo] = []
        self.cargar_datos()

    def cargar_datos(self):
        if ARCHIVO_SOCIOS.exists():
            self.socios = [Socio(**d) for d in json.loads(ARCHIVO_SOCIOS.read_text())]
        if ARCHIVO_MATERIALES.exists():
            self.materiales = [Material(**d) for d in json.loads(ARCHIVO_MATERIALES.read_text())]
        if ARCHIVO_PRESTAMOS.exists():
            self.prestamos = [Prestamo(**d) for d in json.loads(ARCHIVO_PRESTAMOS.read_text())]

    def guardar_datos(self):
        ARCHIVO_SOCIOS.write_text(json.dumps([asdict(s) for s in self.socios], indent=2, ensure_ascii=False))
        ARCHIVO_MATERIALES.write_text(json.dumps([asdict(m) for m in self.materiales], indent=2, ensure_ascii=False))
        ARCHIVO_PRESTAMOS.write_text(json.dumps([asdict(p) for p in self.prestamos], indent=2, ensure_ascii=False))


# ===================== Lógica de negocio =====================
class GestorPrestamos:
    def __init__(self, db: BaseDatos):
        self.db = db

    def registrar_socio(self, nombre, doc):
        if any(s.documento == doc for s in self.db.socios):
            raise ValueError("Ya existe un socio con ese documento.")
        self.db.socios.append(Socio(doc, nombre))
        self.db.guardar_datos()

    def registrar_material(self, titulo, categoria, stock):
        if any(m.titulo == titulo for m in self.db.materiales):
            raise ValueError("Ese material ya existe.")
        self.db.materiales.append(Material(titulo, categoria, stock))
        self.db.guardar_datos()

    def prestar(self, doc, titulo):
        socio = next((s for s in self.db.socios if s.documento == doc), None)
        if not socio:
            raise ValueError("El socio no existe.")

        material = next((m for m in self.db.materiales if m.titulo == titulo), None)
        if not material:
            raise ValueError("El material no existe.")
        if material.stock <= 0:
            raise ValueError("Sin ejemplares disponibles.")

        material.stock -= 1
        self.db.prestamos.append(Prestamo(doc, titulo, datetime.now().isoformat()))
        self.db.guardar_datos()

    def devolver(self, doc, titulo):
        prestamo = next((p for p in self.db.prestamos if p.doc == doc and p.titulo == titulo), None)
        if not prestamo:
            raise ValueError("Ese préstamo no existe.")

        self.db.prestamos.remove(prestamo)
        material = next(m for m in self.db.materiales if m.titulo == titulo)
        material.stock += 1
        self.db.guardar_datos()

        return self.calcular_multa(prestamo)

    def calcular_multa(self, prestamo: Prestamo):
        fecha_prestamo = datetime.fromisoformat(prestamo.fecha)
        limite = fecha_prestamo + timedelta(days=DIAS_LIMITE)
        hoy = datetime.now()
        if hoy <= limite:
            return 0
        atraso = (hoy - limite).days
        return atraso * MULTA_DIA

    def prestamos_activos(self):
        return self.db.prestamos

    def prestamos_vencidos(self):
        vencidos = []
        for p in self.db.prestamos:
            multa = self.calcular_multa(p)
            if multa > 0:
                vencidos.append((p, multa))
        return vencidos


# ===================== Interfaz CLI =====================
def pedir_texto(msg):
    return input(msg).strip()


def pedir_numero(msg):
    while True:
        try:
            return int(input(msg))
        except ValueError:
            print("Debe ser un número válido.")


def menu():
    print("""
====== Biblioteca Persistente ======
1. Registrar socio
2. Listar socios
3. Registrar material
4. Listar materiales
5. Prestar
6. Devolver
7. Reporte: Activos
8. Reporte: Vencidos
0. Salir
====================================
""")


def main():
    db = BaseDatos()
    gestor = GestorPrestamos(db)

    while True:
        menu()
        op = pedir_texto("Opción: ")

        try:
            if op == "1":
                nombre = pedir_texto("Nombre: ")
                doc = pedir_texto("Documento: ")
                gestor.registrar_socio(nombre, doc)
                print("✔ Socio agregado.")
            elif op == "2":
                for s in db.socios:
                    print(f"- {s.nombre} (doc {s.documento})")
            elif op == "3":
                titulo = pedir_texto("Título: ")
                cat = pedir_texto("Categoría (Libro/Revista): ")
                stock = pedir_numero("Cantidad: ")
                gestor.registrar_material(titulo, cat, stock)
                print("✔ Material registrado.")
            elif op == "4":
                for m in db.materiales:
                    print(f"- {m.categoria}: {m.titulo} (stock: {m.stock})")
            elif op == "5":
                doc = pedir_texto("Documento socio: ")
                titulo = pedir_texto("Título: ")
                gestor.prestar(doc, titulo)
                print("✔ Préstamo realizado.")
            elif op == "6":
                doc = pedir_texto("Documento socio: ")
                titulo = pedir_texto("Título: ")
                multa = gestor.devolver(doc, titulo)
                print(f"✔ Devolución registrada. Multa: ${multa}")
            elif op == "7":
                if not db.prestamos:
                    print("(sin préstamos)")
                for p in db.prestamos:
                    socio = next(s for s in db.socios if s.documento == p.doc)
                    print(f"- {socio.nombre} tiene '{p.titulo}' desde {p.fecha[:10]}")
            elif op == "8":
                vencidos = gestor.prestamos_vencidos()
                if not vencidos:
                    print("(sin vencidos)")
                for p, multa in vencidos:
                    socio = next(s for s in db.socios if s.documento == p.doc)
                    print(f"- {socio.nombre} debe '{p.titulo}' con multa de ${multa}")
            elif op == "0":
                print("¡Sesion finalizada!")
                break
            else:
                print("Opción inválida.")
        except Exception as e:
            print(f"✖ Error: {e}")


if __name__ == "__main__":
    main()

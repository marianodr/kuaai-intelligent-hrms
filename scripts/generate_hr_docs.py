#!/usr/bin/env python3
"""
Genera PDFs de RRHH enriquecidos para mejorar la calidad del agente RAG.
Sprint 4 — #10: Más contenido en PDFs de RRHH.

Requiere: pip install reportlab
Uso:     python scripts/generate_hr_docs.py

Los PDFs se generan en docs/hr-pdfs/. Subir manualmente desde la UI de Kuaai.
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from reportlab.lib import colors

OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "hr-pdfs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    "CustomTitle", parent=styles["Title"], fontSize=16, spaceAfter=12,
)
h2_style = ParagraphStyle(
    "H2", parent=styles["Heading2"], fontSize=12, spaceBefore=12, spaceAfter=6,
)
body_style = styles["BodyText"]
body_style.leading = 16


def build_pdf(filename: str, title: str, sections: list[dict]) -> None:
    path = OUTPUT_DIR / filename
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        topMargin=2.5 * cm, bottomMargin=2.5 * cm,
    )
    story = [Paragraph(title, title_style), HRFlowable(width="100%"), Spacer(1, 0.3 * cm)]

    for section in sections:
        story.append(Paragraph(section["heading"], h2_style))
        for para in section["paragraphs"]:
            story.append(Paragraph(para, body_style))
            story.append(Spacer(1, 0.2 * cm))
        if "table" in section:
            t = Table(section["table"], hAlign="LEFT")
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.3 * cm))

    doc.build(story)
    print(f"Generado: {path}")


def gen_vacaciones():
    build_pdf(
        "RRHH-01-Politica-Vacaciones.pdf",
        "Política de Vacaciones y Descanso Anual",
        [
            {
                "heading": "1. Alcance",
                "paragraphs": [
                    "Esta política aplica a todos los empleados en relación de dependencia de la empresa, "
                    "independientemente de su categoría, departamento o modalidad de trabajo (presencial, "
                    "híbrido o remoto).",
                ],
            },
            {
                "heading": "2. Días de vacaciones por antigüedad",
                "paragraphs": [
                    "El derecho a vacaciones se calcula según la antigüedad en la empresa, conforme a la "
                    "Ley de Contrato de Trabajo N° 20.744 y el convenio colectivo aplicable:",
                ],
                "table": [
                    ["Antigüedad", "Días hábiles de vacaciones"],
                    ["Menos de 5 años", "14 días"],
                    ["5 años o más y menos de 10", "21 días"],
                    ["10 años o más y menos de 20", "28 días"],
                    ["20 años o más", "35 días"],
                ],
            },
            {
                "heading": "3. Período de goce",
                "paragraphs": [
                    "Las vacaciones deben tomarse entre el 1° de octubre y el 30 de abril del año siguiente. "
                    "Queda prohibido acumular vacaciones de dos períodos consecutivos, salvo autorización "
                    "escrita de la Gerencia de Recursos Humanos.",
                    "El trabajador debe comunicar su preferencia de fecha con un mínimo de 30 días de anticipación. "
                    "La empresa confirmará o propondrá fechas alternativas dentro de los 5 días hábiles siguientes.",
                ],
            },
            {
                "heading": "4. Fraccionamiento",
                "paragraphs": [
                    "Las vacaciones pueden fraccionarse en hasta dos períodos, siempre que uno de ellos no sea "
                    "inferior a 14 días corridos. El fraccionamiento requiere acuerdo entre el empleado y "
                    "su responsable directo, con aprobación de RRHH.",
                ],
            },
            {
                "heading": "5. Pago de vacaciones",
                "paragraphs": [
                    "El empleado recibirá el pago correspondiente a los días de vacaciones antes del inicio "
                    "del período de descanso. El cálculo se realiza sobre el sueldo diario, incluyendo todas "
                    "las remuneraciones habituales.",
                ],
            },
            {
                "heading": "6. Solicitud y aprobación",
                "paragraphs": [
                    "El proceso de solicitud es el siguiente:",
                    "1. El empleado completa el formulario digital en el sistema HRMS con las fechas deseadas.",
                    "2. El responsable directo aprueba o rechaza dentro de 3 días hábiles.",
                    "3. RRHH valida la disponibilidad y confirma por correo electrónico.",
                    "4. El empleado recibe la notificación de aprobación con al menos 15 días de anticipación.",
                ],
            },
        ],
    )


def gen_contratacion():
    build_pdf(
        "RRHH-05-Procedimientos-de-Contratacion.pdf",
        "Procedimientos de Contratación de Personal",
        [
            {
                "heading": "1. Objetivo",
                "paragraphs": [
                    "Establecer el proceso estándar para la incorporación de nuevo personal, garantizando "
                    "el cumplimiento legal, la equidad en la selección y la integración efectiva del "
                    "candidato a la organización.",
                ],
            },
            {
                "heading": "2. Requisición de personal",
                "paragraphs": [
                    "Toda incorporación debe iniciarse con una Requisición de Personal aprobada por:",
                    "• El responsable directo del área solicitante",
                    "• La Gerencia del área",
                    "• La Gerencia de Recursos Humanos",
                    "• La Dirección General (para posiciones de categoría Senior o superior)",
                    "La requisición debe incluir: descripción del puesto, perfil requerido, rango salarial "
                    "autorizado, fecha estimada de incorporación y justificación del requerimiento.",
                ],
            },
            {
                "heading": "3. Proceso de selección",
                "paragraphs": [
                    "El proceso consta de las siguientes etapas:",
                ],
                "table": [
                    ["Etapa", "Responsable", "Plazo máximo"],
                    ["Publicación de búsqueda", "RRHH", "3 días hábiles"],
                    ["Revisión de CVs y preselección", "RRHH + Área", "5 días hábiles"],
                    ["Entrevista inicial (RRHH)", "RRHH", "2 días por candidato"],
                    ["Entrevista técnica", "Responsable del área", "3 días por candidato"],
                    ["Evaluación psicotécnica", "Proveedor externo", "5 días hábiles"],
                    ["Verificación de referencias", "RRHH", "3 días hábiles"],
                    ["Oferta y negociación", "RRHH + Gerencia", "2 días hábiles"],
                ],
            },
            {
                "heading": "4. Documentación requerida al ingreso",
                "paragraphs": [
                    "El candidato seleccionado debe presentar ANTES del primer día laboral:",
                    "• DNI original y fotocopia (frente y dorso)",
                    "• CUIL",
                    "• Constancia de CUIL/CUIT de AFIP",
                    "• Título o certificado de estudios (original y copia)",
                    "• Antecedentes penales (vigencia máxima 90 días)",
                    "• Certificado de domicilio",
                    "• CBU para acreditación de haberes",
                    "• Carnet de obra social (si posee grupo familiar a cargo)",
                    "• Referencias laborales de los últimos 2 empleadores",
                ],
            },
            {
                "heading": "5. Período de prueba",
                "paragraphs": [
                    "Conforme al Art. 92 bis de la LCT, el período de prueba es de 3 meses para todos los "
                    "ingresos. Durante este período:",
                    "• Ambas partes pueden rescindir el vínculo sin expresión de causa ni preaviso",
                    "• El empleado tiene iguales derechos y obligaciones que el resto del personal",
                    "• RRHH realizará una evaluación de desempeño al finalizar el mes 2",
                    "• La confirmación del ingreso se notifica por escrito antes del vencimiento del período",
                ],
            },
            {
                "heading": "6. Inducción",
                "paragraphs": [
                    "El primer día de trabajo incluye:",
                    "• Bienvenida con el equipo de RRHH (duración: 2 horas)",
                    "• Entrega de equipamiento y accesos al sistema",
                    "• Recorrida por las instalaciones",
                    "• Presentación con el equipo de trabajo",
                    "• Entrega del kit de bienvenida con políticas y reglamentos de la empresa",
                    "Durante las primeras dos semanas se realizarán reuniones diarias de 15 minutos "
                    "entre el nuevo empleado y su responsable directo para seguimiento de la integración.",
                ],
            },
            {
                "heading": "7. Alta en AFIP y sistemas internos",
                "paragraphs": [
                    "RRHH es responsable de:",
                    "• Alta en AFIP (F-931) antes del primer día laboral",
                    "• Alta en la obra social dentro de las 24 horas del ingreso",
                    "• Alta en el sistema de control de asistencia (RFID) el primer día",
                    "• Alta en los sistemas informáticos internos dentro de los 2 días hábiles",
                ],
            },
        ],
    )


def gen_licencias():
    build_pdf(
        "RRHH-03-Politica-Licencias.pdf",
        "Política de Licencias y Ausencias",
        [
            {
                "heading": "1. Licencias especiales pagas",
                "paragraphs": [
                    "El empleado tiene derecho a las siguientes licencias especiales con goce de sueldo:",
                ],
                "table": [
                    ["Motivo", "Días corridos", "Documentación requerida"],
                    ["Matrimonio", "10 días", "Acta de matrimonio"],
                    ["Nacimiento de hijo", "2 días (padre)", "Acta de nacimiento"],
                    ["Fallecimiento de cónyuge/hijo", "3 días", "Acta de defunción"],
                    ["Fallecimiento de padres/hermanos", "3 días", "Acta de defunción"],
                    ["Fallecimiento de abuelos/suegros", "1 día", "Acta de defunción"],
                    ["Mudanza", "2 días", "Contrato/escritura"],
                    ["Examen universitario", "2 días por examen, máx. 10/año", "Comprobante de examen"],
                    ["Donación de sangre", "1 día", "Comprobante del banco de sangre"],
                ],
            },
            {
                "heading": "2. Licencia por enfermedad",
                "paragraphs": [
                    "El empleado que no pueda concurrir al trabajo por razones de salud debe:",
                    "1. Comunicar la ausencia a su responsable directo ANTES del horario de ingreso",
                    "2. Notificar a RRHH por el canal oficial (sistema HRMS o correo rrhh@empresa.com)",
                    "3. Presentar certificado médico dentro de las 48 horas de la ausencia",
                    "La empresa se reserva el derecho de verificar la enfermedad mediante médico propio "
                    "(Art. 210 LCT). El médico de control puede presentarse en el domicilio declarado.",
                    "Plazos de licencia paga por enfermedad según antigüedad:",
                ],
                "table": [
                    ["Antigüedad", "Sin cargas de familia", "Con cargas de familia"],
                    ["Menos de 5 años", "3 meses", "6 meses"],
                    ["5 años o más", "6 meses", "12 meses"],
                ],
            },
            {
                "heading": "3. Licencia por maternidad",
                "paragraphs": [
                    "La empleada en estado de gravidez tiene derecho a 90 días de licencia paga, "
                    "distribuida en:",
                    "• 45 días antes del parto (obligatorios)",
                    "• 45 días después del parto",
                    "La empleada puede optar por acumular hasta 30 días del período pre-parto al "
                    "período post-parto. RRHH debe ser notificado con un mínimo de 30 días de anticipación.",
                ],
            },
            {
                "heading": "4. Ausencias injustificadas",
                "paragraphs": [
                    "Se considera ausencia injustificada cuando el empleado:",
                    "• No concurre al trabajo sin comunicación previa o posterior",
                    "• No presenta documentación respaldatoria en el plazo establecido",
                    "Consecuencias de las ausencias injustificadas:",
                    "• 1 ausencia: apercibimiento verbal",
                    "• 2 ausencias en 30 días: apercibimiento escrito",
                    "• 3 ausencias en 30 días: suspensión de 1 a 5 días sin goce de sueldo",
                    "• 4 ausencias o más: puede constituir injuria grave y habilitar el despido con causa",
                ],
            },
            {
                "heading": "5. Trabajo remoto y permisos especiales",
                "paragraphs": [
                    "El empleado puede solicitar trabajo remoto puntual (hasta 3 días por trimestre) "
                    "en situaciones excepcionales debidamente justificadas. La solicitud debe realizarse "
                    "con 48 horas de anticipación y requiere aprobación del responsable directo.",
                ],
            },
        ],
    )


def gen_beneficios():
    build_pdf(
        "RRHH-06-Beneficios-y-Compensaciones.pdf",
        "Guía de Beneficios y Compensaciones",
        [
            {
                "heading": "1. Estructura de remuneración",
                "paragraphs": [
                    "La remuneración está compuesta por los siguientes elementos:",
                ],
                "table": [
                    ["Componente", "Descripción", "Periodicidad"],
                    ["Sueldo básico", "Según categoría del CCT", "Mensual"],
                    ["Adicional por antigüedad", "1% del básico por año cumplido", "Mensual"],
                    ["Adicional por presentismo", "8% del básico (sin ausencias injust.)", "Mensual"],
                    ["Horas extra 50%", "Días hábiles: 1.5x del valor hora", "Mensual"],
                    ["Horas extra 100%", "Sábados tarde, domingos y feriados: 2x", "Mensual"],
                    ["Bono anual", "Hasta 1 sueldo según evaluación de desempeño", "Anual (dic.)"],
                ],
            },
            {
                "heading": "2. Beneficios adicionales",
                "paragraphs": [
                    "La empresa ofrece los siguientes beneficios no remunerativos:",
                    "• Cobertura médica: obra social OSDE Plan 210 para empleado y grupo familiar",
                    "• Seguro de vida: 2x el sueldo anual",
                    "• Tickets alimentación: $45.000 mensuales (no remunerativo)",
                    "• Capacitación: hasta $200.000 anuales en cursos y certificaciones relevantes",
                    "• Día de cumpleaños libre: jornada libre en el mes de cumpleaños",
                    "• Día del trabajador libre: 1° de mayo libre y pago",
                ],
            },
            {
                "heading": "3. Evaluación de desempeño y ajustes salariales",
                "paragraphs": [
                    "El proceso de evaluación de desempeño se realiza dos veces por año (junio y diciembre). "
                    "Los ajustes salariales por desempeño se aplican en marzo y julio, según la siguiente escala:",
                ],
                "table": [
                    ["Calificación", "Ajuste adicional (sobre inflación)"],
                    ["Supera expectativas (A)", "+5%"],
                    ["Cumple expectativas (B)", "0% (solo ajuste inflacionario)"],
                    ["Cumple parcialmente (C)", "-2% (ajuste diferido 3 meses)"],
                    ["No cumple expectativas (D)", "Sin ajuste, plan de mejora obligatorio"],
                ],
            },
            {
                "heading": "4. Préstamos y adelantos",
                "paragraphs": [
                    "Los empleados con más de 6 meses de antigüedad pueden solicitar:",
                    "• Adelanto de sueldo: hasta el 50% del sueldo neto, una vez por trimestre",
                    "• Préstamo de emergencia: hasta 3 sueldos netos, con descuento en 6 cuotas",
                    "Las solicitudes se gestionan a través del sistema HRMS y requieren aprobación de RRHH.",
                ],
            },
        ],
    )


if __name__ == "__main__":
    print(f"Generando PDFs en {OUTPUT_DIR}/")
    gen_vacaciones()
    gen_contratacion()
    gen_licencias()
    gen_beneficios()
    print("\nListo. Subí los PDFs desde la sección Documentos en la UI de Kuaai.")

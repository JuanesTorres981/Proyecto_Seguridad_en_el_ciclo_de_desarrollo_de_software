# 🫧 Bubbles :p.
Bubbles es un sistema diseñado para blindar el proceso de pagos mediante el análisis inteligente de transacciones simuladas. El proyecto se enfoca en integrar la seguridad desde la raíz, creando una "burbuja" de protección que identifica patrones sospechosos y comportamientos anómalos en tiempo real. Al procesar los datos de manera proactiva, Bubbles permite detectar posibles riesgos antes de que se conviertan en un problema, asegurando que la prevención de fraude sea una parte natural y fluida del ciclo de vida del software.

## 2. Activos Clave
- Datos de las transacciones
- Identidad de los usuarios
- Lógica de cálculo de riesgo
- Disponibilidad del sistema

## 3. Metodología
Se utiliza el modelo STRIDE para identificar amenazas de seguridad.

## 4. Análisis de Amenazas
| Tipo de Amenaza | Descripción | Impacto | Mitigación |
|----------------|------------|---------|-----------|
| Suplantación (Spoofing) | Un atacante se hace pasar por un usuario legítimo | Transacciones no autorizadas | Validación de identidad y de entradas |
| Manipulación (Tampering) | Alteración de datos de la transacción | Evaluación incorrecta del riesgo | Validación de datos e integridad |
| Repudio (Repudiation) | Un usuario niega haber realizado una transacción | Falta de trazabilidad | Registro de logs auditables |
| Divulgación de Información | Exposición de datos sensibles | Pérdida de privacidad | Protección y manejo seguro de datos |
| Denegación de Servicio (DoS) | Saturación del sistema con múltiples solicitudes | Indisponibilidad del servicio | Limitación de tasa (rate limiting) |
| Elevación de Privilegios | Un usuario obtiene más permisos de los permitidos | Compromiso del sistema | Validación de roles y permisos |

## 5. Consideraciones de Riesgo
Las amenazas más críticas identificadas son:
- Suplantación de identidad, debido a la naturaleza de las transacciones
- Manipulación de datos, ya que afecta directamente la detección de fraude
- Denegación de servicio, por su impacto en la disponibilidad del sistema

Estas amenazas se priorizan por su impacto potencial tanto financiero como operativo.

## 6. Mejoras Futuras
- Implementar mecanismos de autenticación más robustos
- Integrar modelos de detección de anomalías
- Mejorar el monitoreo y generación de alertas
# Ejercicio 01 — Composition Root y lifecycle de FastAPI

Esta branch conserva un checkpoint de aprendizaje sobre la fundación actual
del backend. No mergees estos documentos a `main`; usalos para implementar,
anotar decisiones y comparar tu solución contra los tests.

## Punto de partida

`alkem-api` expone una app factory:

```python
app = create_app(engine)
```

La API recibe un `GenerationService` prestado y no conoce adapters ni
configuración de proveedores. `AIEngine`, por su parte, construye y cierra
los adapters que posee.

El proyecto todavía no tiene un proceso ejecutable configurado por entorno.

## Objetivo

Implementá un composition root de producción que lea configuración validada,
construya un `AIEngine`, lo posea durante el ciclo de vida de FastAPI y lo
cierre correctamente al apagar la aplicación.

La forma concreta de representar una o varias configuraciones de modelo es
parte del ejercicio. Elegí y defendé la opción que tenga mejor relación entre
claridad operativa y complejidad actual.

## Restricciones de diseño

- Conservá `create_app(engine)` para tests y consumidores que inyectan un
  servicio prestado.
- El transporte HTTP no debe construir adapters directamente.
- La configuración, secretos y ownership viven en el composition root.
- No hagas llamadas reales a proveedores en los tests.
- No agregues routing automático, fallback, RAG, streaming ni un contenedor
  de DI genérico.
- No registres API keys, prompts completos ni headers de autorización.

## Criterios de aceptación

1. Una configuración faltante o inválida impide iniciar la aplicación con un
   error accionable y sin filtrar secretos.
2. Un modelo configurado se transforma explícitamente en `ModelConfig`.
3. El `AIEngine` creado por el composition root se cierra exactamente una vez
   durante shutdown.
4. Un engine inyectado mediante `create_app(engine)` no es cerrado por la API.
5. La suite cubre startup, shutdown, configuración inválida y ownership, sin
   red real.
6. La aplicación puede ejecutarse con Uvicorn usando una entry point clara.

## Decisiones que tenés que tomar

### Forma de configuración

¿Usarías una sola configuración de modelo para este corte vertical, JSON en
una variable de entorno, o variables indexadas para varios modelos? Compará:

- validación y mensajes de error;
- operabilidad en Docker/CI/plataformas cloud;
- rotación de secretos;
- compatibilidad con varios proveedores;
- cuánto diseño especulativo introduce hoy.

### Ownership y lifespan

¿Dónde crearías el engine y cómo probarías que el recurso que la app crea es
el único que la app cierra? Explicá por qué cerrar un engine inyectado sería
un bug de ownership.

## Debilidad intencional para el siguiente ejercicio

La API transforma por ahora cualquier `ProviderError` en HTTP 502. Eso evita
filtrar detalles de infraestructura, pero es una política demasiado gruesa:
un rate limit, un fallo de autenticación, una respuesta malformada y una
conexión caída tienen acciones operativas distintas.

No la arregles dentro de este ejercicio salvo que primero termines el
composition root y puedas justificar el cambio de scope.

También observá que `max_tokens` controla salida, no el tamaño del prompt. La
API acepta mensajes válidos que podrían exceder la ventana de contexto o el
presupuesto de costo.

## Quiz

Respondé estas preguntas en `NOTES.md` antes de mirar cualquier solución:

1. ¿Por qué Pydantic encaja en el borde HTTP/configuración mientras que los
   dataclasses congelados siguen siendo útiles en los contratos internos?
2. ¿Por qué `ModelNotConfiguredError` es más seguro que capturar un
   `ValueError` genérico en la API?
3. ¿Quién debe cerrar un `AIEngine` inyectado en `create_app(engine)` y por
   qué?
4. ¿Cuándo expondrías 429, 502 o 503 ante un rate limit del proveedor?
5. ¿Qué aporta `GenerationService` frente a tipar la dependencia directamente
   como `AIEngine`?
6. ¿Dónde deberían vivir los retries y qué cambia al incorporar operaciones no
   idempotentes o tool execution?
7. ¿Cómo limitarías mensajes grandes sin convertir esta API en un contador de
   tokens específico de proveedor?

## Verificación

```powershell
.\.venv\Scripts\python -m pytest -p no:cacheprovider ai-provider-gateway\tests alkem-core\tests alkem-api\tests -q
```

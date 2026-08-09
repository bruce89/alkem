# ALKEM — Bitácora de producto y arquitectura

**Estado:** documento vivo  
**Última actualización:** 2026-08-08  
**Alcance de esta entrada:** Foundation / primer cambio de Provider Gateway

---

## Cómo leer esta bitácora

El \`SPEC\` dice qué queremos construir y cuáles son las reglas de diseño vigentes. Esta bitácora explica cómo llegamos a ellas: el problema observado, la decisión, las alternativas descartadas y las consecuencias.

- **Implementado**: confirmado en el código actual.
- **Acordado / próximo**: decisión tomada, aún no necesariamente codificada.
- **Futuro**: dirección del producto descrita en el \`SPEC\`; no representa una capacidad presente.

Esto evita presentar una intención como estado técnico real.

# Parte I — El tipo de producto

## 1. Un portfolio defendible, no un monolito de utilería

ALKEM es un producto de aprendizaje y portfolio. La meta no es acumular features ni simular infraestructura enterprise: es construir un sistema pequeño, coherente y defendible de punta a punta.

Cada abstracción debe existir porque un problema concreto la justificó. Si no hay todavía un caso real, la idea puede quedar registrada como futuro, pero el código no debe anticiparse a ella. La ambición es seria; el alcance es deliberadamente pequeño.

**Para defender en entrevista:** el criterio no se mide por cantidad de capas, sino por la claridad de los límites, razones de cambio y trade-offs.

## 2. Provider Gateway: cimiento neutral

El \`SPEC\` separa la arquitectura en clientes, aplicación/Core, Provider Gateway y proveedores.

\`\`\`text
Clientes
  ↓
Aplicación / Core de orquestación
  ↓
Provider Gateway
  ↓
OpenAI · Anthropic · Ollama
\`\`\`

El gateway traduce contratos independientes de proveedor a protocolos vendor-specific y normaliza las respuestas que el resto de ALKEM consume. No elige modelos por política de producto, no ensambla prompts de aplicación y no contiene memoria, RAG, herramientas ni routing.

**Rationale:** separar infraestructura de proveedor del valor de producto permite que el gateway sea reutilizable y que el Core aparezca sólo cuando haya una operación de aplicación que realmente requiera orquestación.

# Parte II — Decisiones cronológicas

## 3. Alcance deliberadamente recortado

**Decisión:** RAG, vector stores, memoria, agent loops, prompt templates, workflows, model routing y políticas de retry/fallback están fuera del Provider Gateway.

**Rationale:** esas responsabilidades cambian por razones distintas. Un adapter no debería modificarse porque cambia una estrategia de retrieval; una política de negocio no debe parsear SSE de un proveedor.

**Alternativas descartadas:**

- Un framework de agentes genérico desde el inicio.
- Model registry, routing automático o fallbacks antes de tener un consumidor real.
- RAG y memoria dentro del paquete que traduce llamadas a proveedores.

**Consecuencia:** ALKEM avanza por verticales pequeñas y el gateway permanece útil independientemente.

## 4. Protocolos de capacidad, no un proveedor monolítico

**Estado:** implementado y validado localmente: suite completa con **5 tests verdes** el 2026-08-08.

El contrato original \`AIProviderPort\` agrupaba chat, streaming, embeddings y costo. Era cómodo, pero afirmaba que todos los proveedores soportaban todo. Anthropic expuso el problema: su adapter ofrecía \`embed()\` solamente para lanzar \`NotImplementedError\`.

El problema no era Anthropic: el contrato estaba prometiendo algo falso.

La primera refactorización eliminó \`AIProviderPort\` y dejó tres protocolos estructurales, comprobables en runtime:

\`\`\`text
ChatProvider       → complete(request), stream(request)
EmbeddingProvider  → embed(...)
CostEstimator      → estimate_cost(request)
\`\`\`

OpenAI y Ollama pueden ofrecer varias capacidades. Anthropic ofrece chat y costo, pero no embeddings. Tener chat no implica tener embeddings.

**Rationale:** la segregación de interfaces representa capacidades reales, evita métodos imposibles de implementar y permite que cada consumidor dependa sólo de lo que necesita.

**Alternativas descartadas:**

- Un único \`AIProviderPort\` con excepciones para capacidades no soportadas.
- Un alias deprecated de \`AIProviderPort\`.
- Registry, flags de capability o plugin system desde ahora.

No hay consumidores externos de una API ya establecida; el alias deprecated sólo agregaría dos nombres para el mismo concepto. Los registries se difieren hasta que exista selección o descubrimiento dinámico real.

**Consecuencia:** los tipos de las dependencias se vuelven precisos: chat depende de \`ChatProvider\`, embeddings de \`EmbeddingProvider\`. El runtime check se usa hoy para tests, no para conducir la arquitectura mediante reflexión.

**Para defender en entrevista:** no se aplicó Interface Segregation por dogma. Un \`NotImplementedError\` en un adapter fue la evidencia de que la interfaz original mentía.

## 5. Anthropic no debe fingir embeddings

**Estado:** implementado como parte del cambio anterior.

Quitar \`embed()\` de Anthropic no elimina una feature; elimina una promesa inexistente. Un adapter sólo debe exponer las capacidades que puede realizar.

**Consecuencia:** falla antes y de manera más clara en el diseño: un consumidor que requiera embeddings no puede recibir Anthropic por accidente como si fuera un \`EmbeddingProvider\`.

## 6. Streaming: normalizar lo mínimo útil

**Estado:** acordado para un ticket posterior; no implementado.

Hoy el streaming conserva el wire format: OpenAI y Anthropic emiten SSE; Ollama, líneas JSON. El consumidor no debería tener que comprenderlos.

El próximo límite mínimo es:

\`\`\`python
@dataclass(frozen=True)
class TextDelta:
    text: str
\`\`\`

El futuro \`stream()\` devolverá texto incremental normalizado, no payloads crudos.

**Alternativas descartadas por ahora:** \`UsageUpdate\`, \`Completed\`, eventos de reasoning, eventos de tools y una jerarquía amplia \`StreamEvent\`.

**Rationale:** \`TextDelta\` resuelve la necesidad real sin diseñar eventos para datos que ningún consumidor necesita todavía.

## 7. Embeddings: solicitud y resultado explícitos

**Estado:** próximo paso acordado; no implementado.

El \`SPEC\` detecta modelos de embeddings hardcodeados en adapters de OpenAI/Ollama y resultados que sólo devuelven vectores. El caller no expresa el modelo elegido ni conserva metadata suficiente.

El próximo ticket introducirá contratos equivalentes a:

\`\`\`text
EmbeddingRequest
  model
  inputs

EmbeddingResult
  embeddings
  model
  provider
  usage?     # si el proveedor lo informa
\`\`\`

**Rationale:** elegir modelo es una decisión del caller o la configuración superior, no del adapter. El adapter traduce una solicitud; no incorpora silenciosamente una política de producto.

**Alternativas descartadas:** hardcodear modelos en adapters o construir antes un Model Registry completo.

# Parte III — Producto futuro y límites

## 8. Side Chat es producto; Ephemeral Branch es arquitectura

**Estado:** conceptos futuros del \`SPEC\`; no implementados.

**Side Chat** es la experiencia visible: hacer una pregunta secundaria, explorar una alternativa o pedir una aclaración sin desviar la conversación principal.

**Ephemeral Branch** es la primitiva interna posible: una rama parte de un punto del hilo, hereda el contexto relevante hasta allí, mantiene sus propios mensajes y puede descartarse sin cambiar al padre. A futuro podría promover una conclusión seleccionada.

\`\`\`text
Conversación principal: A → B → C → D
                              │
                              └→ Side Chat: pregunta → respuesta
\`\`\`

La distinción evita acoplar el dominio a una UI. Side Chat es una presentación; Ephemeral Branch puede servir a más de un flujo.

## 9. Historial de conversación ≠ contexto del modelo

**Estado:** principio futuro, derivado del Context Builder y de Ephemeral Branches.

Que una sesión guarde mensajes no significa que todos viajen en cada invocación. El historial registra lo ocurrido. El Context Builder decide qué instrucciones, mensajes, memorias, documentos y resultados de tools entran en el contexto, sujeto al presupuesto de tokens.

\`\`\`text
Conversation history  ≠  Model context
\`\`\`

**Rationale:** sin esta separación, una rama temporal no sería realmente temporal y las decisiones de contexto quedarían ocultas en persistencia.

## 10. Recortes de scope que también son arquitectura

Durante los primeros hitos no construiremos:

- RAG, vector store o memoria dentro del gateway.
- Routing automático, fallbacks o registry de modelos.
- Tool calling, structured output o eventos de streaming ricos.
- Más proveedores, un framework de agentes o un DSL de workflows.
- Infraestructura distribuida, Kubernetes, benchmarking o pricing sofisticado.

No son features olvidadas. Son decisiones negativas que preservan foco: contratos correctos, límites claros y un vertical slice usable. Cuando aparezcan, pertenecerán a límites propios: RAG como pipeline separado; memoria/branches en sesiones o Core; tools tras una frontera de seguridad; routing en el Core.

# Parte IV — Método de construcción

## 11. Diseño humano, ejecución acotada

El flujo de trabajo actual es:

\`\`\`text
Humano + ChatGPT
  producto, arquitectura, alcance, revisión y rationale
      ↓
Codex
  inspección, ticket acotado, implementación y pruebas
      ↓
Humano
  lectura del diff, cotejo con la bitácora y defensa de la decisión
\`\`\`

Codex recibe tickets pequeños con scope explícito. El objetivo no es delegar comprensión: mirar el diff antes de leer la explicación permite reconstruir la decisión desde el código.

## 12. Tests verdes cierran un ticket

Un diff razonable no alcanza. Todo ticket debe incluir pruebas significativas y terminar con la suite relevante verde. El primer ticket quedó validado con **5 passed**.

La regla futura es que Codex pueda ejecutar el ciclo editar → probar → corregir → probar en el entorno del proyecto. Advertencias de consola no bloqueantes se registran, pero nunca reemplazan un test exitoso.

## 13. Próxima secuencia

1. Consolidar y comprender los capability protocols ya implementados.
2. Introducir \`EmbeddingRequest\` / \`EmbeddingResult\` y sacar el modelo hardcodeado del adapter.
3. Normalizar streaming con \`TextDelta\` y fixtures de los tres proveedores.
4. Definir lifecycle HTTP mínimo y errores normalizados sólo cuando el comportamiento lo requiera.
5. Revisar unidades de costo y modelos desconocidos, sin construir un servicio de pricing.

Cada paso debe respetar su propio alcance, sumar tests y actualizar esta bitácora si cambia una decisión o aparece nueva evidencia.

# Apéndice — Preguntas para defender cada cambio

1. ¿Qué problema concreto resolvió?
2. ¿Qué contrato cambió y quién queda más simple o seguro?
3. ¿Qué alternativa fue descartada y qué costo evitó?
4. ¿Qué quedó fuera del alcance?
5. ¿Qué test demuestra el comportamiento o límite relevante?
6. ¿Qué puede cambiar después sin romper esta decisión?

Si las respuestas son concretas, el cambio es buen material de portfolio: muestra código y juicio técnico.


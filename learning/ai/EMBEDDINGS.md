# Embeddings

## What they are

An embedding is a numeric vector that represents the semantic meaning of an input, such as a sentence, document chunk, or source-code fragment. Inputs with similar meaning should be located near one another in vector space.

## Why ALKEM may use them

Embeddings are a building block for later retrieval workflows:

```text
document
→ chunks
→ embeddings
→ vector search
→ relevant context
→ model request
```

They are not required for the current Provider Gateway milestone, and do not imply that ALKEM needs a vector database yet.

## Current gateway contract

The gateway uses explicit, provider-neutral data:

```python
EmbeddingRequest(model, inputs)
EmbeddingResult(embeddings, model, provider)
```

The caller selects the model. An adapter translates that request to its provider protocol; it must not hardcode an embedding model. OpenAI and Ollama currently implement `EmbeddingProvider`; Anthropic does not.

## Questions to study

- How are embeddings produced and compared?
- Cosine similarity versus dot product and Euclidean distance.
- How chunking affects retrieval quality.
- Why an embedding model must be used consistently for indexed documents and queries.
- The trade-offs between local and hosted embedding models.

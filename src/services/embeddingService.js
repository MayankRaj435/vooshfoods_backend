// src/services/embeddingService.js

const { CohereClient } = require('cohere-ai');
require('dotenv').config({ path: '../../.env' });

const cohere = new CohereClient({
  token: process.env.COHERE_API_KEY,
});

const getEmbedding = async (text) => {
  const response = await cohere.embed({
    texts: [text],
    model: 'embed-english-v3.0',
    inputType: 'search_query',
  });
  return response.embeddings[0];
};

module.exports = { getEmbedding };
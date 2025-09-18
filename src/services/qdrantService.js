const { QdrantClient } = require('@qdrant/js-client-rest');
require('dotenv').config({ path: '../../.env' });

const client = new QdrantClient({ url: process.env.QDRANT_URL });
const COLLECTION_NAME = 'news_articles';

const searchForContext = async (vector) => {
  const results = await client.search(COLLECTION_NAME, {
    vector,
    limit: 3, // Retrieve top 3 most relevant passages
    with_payload: true,
  });
  return results.map((result) => result.payload.text);
};

module.exports = { searchForContext };
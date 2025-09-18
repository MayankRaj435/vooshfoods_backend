const { GoogleGenerativeAI } = require('@google/generative-ai');
require('dotenv').config({ path: '../../.env' });

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' });

const generatePrompt = (context, query) => {
  return `Based on the following news context, please provide a concise answer to the user's question. If the context is not sufficient, say you don't have enough information.

Context:
---
${context.join('\n---\n')}
---

Question: ${query}
`;
};

async function* generateResponseStream(context, query) {
  const prompt = generatePrompt(context, query);
  const result = await model.generateContentStream(prompt);

  for await (const chunk of result.stream) {
    const chunkText = chunk.text();
    yield chunkText;
  }
}

module.exports = { generateResponseStream };
// src/socket/handler.js (Final Version)

const { getEmbedding } = require('../services/embeddingService');
const { generateResponseStream } = require('../services/geminiService');
const { searchForContext } = require('../services/qdrantService');
const { addMessageToHistory } = require('../services/redisService');

module.exports = (io) => {
  io.on('connection', (socket) => {
    console.log(`Socket connected: ${socket.id}`);

    socket.on('join_session', (sessionId) => {
      socket.join(sessionId);
      console.log(`Socket ${socket.id} joined session ${sessionId}`);
    });

    socket.on('chat_message', async ({ sessionId, message }) => {
      try {
        await addMessageToHistory(sessionId, 'user', message);

        const queryVector = await getEmbedding(message);
        const context = await searchForContext(queryVector);

        const stream = generateResponseStream(context, message);
        let fullResponse = '';

        for await (const chunk of stream) {
          fullResponse += chunk;
          io.to(sessionId).emit('bot_response_chunk', { chunk });
        }

        await addMessageToHistory(sessionId, 'bot', fullResponse);
        io.to(sessionId).emit('bot_response_end');
      } catch (error) {
        console.error('Error processing chat message:', error);
        io.to(sessionId).emit('error_message', {
          message: 'Sorry, something went wrong.',
        });
      }
    });

    socket.on('disconnect', () => {
      console.log(`Socket disconnected: ${socket.id}`);
    });
  });
};











































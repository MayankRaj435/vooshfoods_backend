const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const { getHistory } = require('./services/redisService');
const socketHandler = require('./socket/handler');

const app = express();
const server = http.createServer(app);

const io = new Server(server, {
  cors: {
    origin: process.env.FRONTEND_URL,
    methods: ['GET', 'POST'],
  },
});

app.use(cors({ origin: process.env.FRONTEND_URL }));

// REST API for session and history
app.post('/session', (req, res) => {
  const sessionId = uuidv4();
  res.json({ sessionId });
});

app.get('/history/:sessionId', async (req, res) => {
  const { sessionId } = req.params;
  try {
    const history = await getHistory(sessionId);
    res.json(history);
  } catch (error) {
    console.error(`Error fetching history for session ${sessionId}:`, error);
    res.status(500).json({ error: 'Failed to fetch history' });
  }
});

// Handle Socket.IO connections
socketHandler(io);

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
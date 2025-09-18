const { createClient } = require('redis');
require('dotenv').config({ path: '../../.env' });

const client = createClient({ url: process.env.REDIS_URL });
client.on('error', (err) => console.log('Redis Client Error', err));
client.connect();

const SESSION_TTL = 3600; 

const addMessageToHistory = async (sessionId, role, content) => {
  const key = `session:${sessionId}`;
  const message = JSON.stringify({ role, content });
  await client.rPush(key, message);
  await client.expire(key, SESSION_TTL); 
};

const getHistory = async (sessionId) => {
  const key = `session:${sessionId}`;
  const history = await client.lRange(key, 0, -1);
  return history.map((item) => JSON.parse(item));
};

module.exports = { addMessageToHistory, getHistory };
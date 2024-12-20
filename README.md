# Chat Backend API with WebSockets

Welcome to the Chat Backend Project! This project provides a FastAPI-based backend for a chat application that supports real-time messaging, user presence updates, and bot responses. The purpose of this task is to evaluate your ability to create a front-end chat application that communicates with this backend.

## Expectations for the Interviewee

### What We Expect:
1. **Frontend Implementation:**
   - Build a chat interface that can send and receive messages using the REST API and optionally integrate with WebSockets for real-time updates.
   - Design is highly important; we expect a visually appealing and user-friendly interface.
   - Animations are optional but very welcome.

2. **Code Structure:**
   - Clean, modular, and well-documented code will be highly valued.
   - Use a modern framework (e.g., React, Next.js).

3. **Features to Implement:**
   - **Core Features:**
     - Ability to create chats and display messages.
     - Sending text, images, and audio messages.
     - Display user presence (online, offline, typing).
   - **Optional Features:**
     - Group chat support.
     - WebSocket integration for real-time updates.
     - Animations and additional UI/UX enhancements.

4. **Delivery:**
   - Provide a GitHub repository with your code.
   - Include a detailed README file with:
     - Instructions to run the application locally.
     - Any additional notes or assumptions made during the implementation.
   - Ensure the application is easy to set up and test on a different machine.
   - Send the GitHub link with the project to daniel@mysailer.com, and include your name in the email.

---

## Features
- Create chat rooms with participants.
- Send messages (text, image, audio).
- Real-time updates for user presence, read receipts, and new messages using WebSockets.
- Bot responses with randomized delay and content.

---

## Installation and Setup

### Prerequisites
1. Install [Docker](https://www.docker.com/) on your system.
2. Clone this repository:
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

### Build and Run with Docker

1. Build the Docker image:
   ```bash
   docker build -t chat-backend .
   ```

2. Run the Docker container:
   ```bash
   docker run -p 8000:8000 chat-backend
   ```

3. The backend will be available at `http://localhost:8000`.

---

## API Documentation

### REST Endpoints

#### 1. Create a Chat
**Endpoint**: `POST /chats`

**Request Body**:
```json
{
  "participants": ["user1", "user2"]
}
```

**Response**:
```json
{
  "chat_id": "<generated_chat_id>",
  "participants": ["user1", "user2"]
}
```

#### 2. List Chats
**Endpoint**: `GET /chats`

**Response**:
```json
[
  {
    "chat_id": "<chat_id>",
    "participants": ["user1", "user2", "bot_user"]
  }
]
```

#### 3. Get Messages for a Chat
**Endpoint**: `GET /chats/{chat_id}/messages`

**Response**:
```json
[
  {
    "id": "<message_id>",
    "user_id": "user1",
    "type": "text",
    "content": "Hello!",
    "timestamp": "2024-12-01T12:00:00Z"
  }
]
```

#### 4. Send a Message
**Endpoint**: `POST /chats/{chat_id}/messages`

**Request Body**:
```json
{
  "user_id": "user1",
  "type": "text",
  "content": "Hello, world!"
}
```

**Response**:
```json
{
  "status": "message_sent"
}
```

#### 5. Update User Presence
**Endpoint**: `POST /chats/{chat_id}/presence`

**Request Body**:
```json
{
  "user_id": "user1",
  "status": "online"
}
```

**Response**:
```json
{
  "chat_id": "<chat_id>",
  "user_id": "user1",
  "status": "online"
}
```

#### 6. Mark Chat as Read
**Endpoint**: `POST /chats/{chat_id}/read`

**Request Body**:
```json
{
  "user_id": "user1"
}
```

**Response**:
```json
{
  "chat_id": "<chat_id>",
  "user_id": "user1",
  "last_read_message_id": "<message_id>"
}
```

---

### WebSocket Endpoint

#### Connect to a Chat
**Endpoint**: `ws://<host>:8000/ws/{chat_id}`

- Replace `<host>` with your server (e.g., `localhost` for local testing).
- Replace `{chat_id}` with the desired chat ID.

**Example JavaScript WebSocket Client**:
```javascript
const chatId = "<chat_id>";
const socket = new WebSocket(`ws://localhost:8000/ws/${chatId}`);

// Listen for incoming messages
socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Event Type:", data.event);
  console.log("Payload:", data.data);
};

// Send a message to the server (if applicable)
socket.onopen = () => {
  console.log("WebSocket connection established");
};

socket.onerror = (error) => {
  console.error("WebSocket error:", error);
};

socket.onclose = () => {
  console.log("WebSocket connection closed");
};
```

---

### WebSocket Events
The WebSocket server sends events in the following format:

```json
{
  "event": "<event_type>",
  "data": { <event_payload> }
}
```

**Supported Events**:

1. **`message_received`**
   - Sent when a new message is added to the chat.
   - Payload:
     ```json
     {
       "id": "<message_id>",
       "user_id": "<user_id>",
       "type": "<message_type>",
       "content": "<content>",
       "timestamp": "<timestamp>"
     }
     ```

2. **`presence_updated`**
   - Sent when a user updates their presence.
   - Payload:
     ```json
     {
       "user_id": "<user_id>",
       "status": "<online|offline|typing>",
       "last_seen": "<timestamp>"
     }
     ```

3. **`chat_read`**
   - Sent when a user marks a chat as read.
   - Payload:
     ```json
     {
       "chat_id": "<chat_id>",
       "user_id": "<user_id>",
       "last_read_message_id": "<message_id>"
     }
     ```

---

## Notes
- The bot user (`bot_user`) automatically responds with predefined messages after a delay.
- Use the WebSocket connection for real-time updates instead of polling.

Feel free to customize this backend as per your requirements!


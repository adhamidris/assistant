# AI Personal Business Assistant - Frontend

A modern Next.js frontend for the AI Personal Business Assistant system, featuring both customer portal and business dashboard interfaces.

## Features

### Customer Portal (`/portal`)
- **Phone-based Authentication**: Simple phone number entry for customer identification
- **Real-time Chat Interface**: Text messaging with AI assistant
- **File Upload Support**: Drag-and-drop file sharing with automatic processing
- **Audio Messaging**: Voice message recording with automatic transcription
- **Responsive Design**: Mobile-first design that works on all devices
- **Session Management**: Persistent conversations across browser sessions

### Business Dashboard (`/dashboard`)
- **Conversation Management**: View and manage all customer conversations
- **Contact Directory**: Comprehensive customer contact management
- **Draft Approval System**: Review and approve AI-generated responses
- **Knowledge Base Manager**: Upload and manage documents for AI training
- **Analytics Overview**: Key metrics and performance insights
- **Real-time Updates**: Live updates for new messages and conversations

## Tech Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Headless UI, Lucide React icons
- **HTTP Client**: Axios
- **Form Handling**: React Hook Form with Zod validation
- **State Management**: React hooks and context
- **Date Handling**: date-fns

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── page.tsx           # Landing page
│   ├── portal/            # Customer portal
│   │   └── page.tsx       # Portal entry point
│   └── dashboard/         # Business dashboard
│       └── page.tsx       # Dashboard main page
├── components/            # Reusable UI components
│   ├── ChatInterface.tsx  # Main chat component
│   ├── ConversationList.tsx
│   ├── ContactList.tsx
│   ├── DraftManagement.tsx
│   └── KnowledgeBaseManager.tsx
├── lib/                   # Utility libraries
│   ├── api.ts            # API client and functions
│   └── utils.ts          # Helper utilities
└── globals.css           # Global styles and components
```

## Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Running backend API (see ../assistant/README.md)

### Installation

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Set up environment variables**:
   ```bash
   cp env.local.example .env.local
   ```
   
   Update `.env.local` with your configuration:
   ```env
   NEXT_PUBLIC_API_BASE=http://localhost:8000
   NEXT_PUBLIC_DEMO_WORKSPACE_ID=demo-workspace-123
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```

4. **Open your browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## Usage

### Customer Experience

1. **Access Portal**: Visit `/portal` or click "Customer Portal" from homepage
2. **Enter Phone Number**: Provide phone number for identification
3. **Start Conversation**: Begin chatting with the AI assistant
4. **Send Messages**: Use text, voice, or file uploads
5. **Get Responses**: Receive intelligent AI responses based on knowledge base

### Business Owner Experience

1. **Access Dashboard**: Visit `/dashboard` or click "Owner Dashboard" from homepage
2. **View Conversations**: Monitor all customer interactions in real-time
3. **Manage Contacts**: View customer information and conversation history
4. **Review Drafts**: Approve or modify AI-generated responses (manual mode)
5. **Upload Documents**: Add knowledge base content for better AI responses
6. **Monitor Analytics**: Track performance metrics and conversation insights

## API Integration

The frontend communicates with the Django backend through a comprehensive API client (`lib/api.ts`) that handles:

- **Session Management**: Create and validate customer sessions
- **Messaging**: Send/receive messages, upload files and audio
- **Knowledge Base**: Search and manage documents
- **Admin Functions**: Conversation and contact management

### Key API Functions

```typescript
// Session management
createSession(phoneNumber, workspaceId)
validateSession(sessionToken)

// Messaging
sendMessage(text)
uploadFile(file)
uploadAudio(audioFile)
getMessages(conversationId)

// Admin functions
getConversations(workspaceId)
getContacts(workspaceId)
getDrafts()
approveDraft(draftId, action, modifiedText)
```

## Components

### ChatInterface
Main chat component with:
- Message bubbles for different senders
- File and audio upload
- Voice recording
- Real-time message updates
- Typing indicators

### Dashboard Components
- **ConversationList**: Browse and view conversations
- **ContactList**: Customer contact management
- **DraftManagement**: Review AI-generated responses
- **KnowledgeBaseManager**: Document upload and search

## Styling

### Tailwind CSS Configuration
- Custom component classes for chat bubbles
- Responsive design utilities
- Animation classes for loading states
- Color schemes for different message types

### Custom CSS Classes
```css
.message-bubble        # Base message styling
.message-bubble.client # Customer messages
.message-bubble.assistant # AI responses
.typing-indicator     # AI thinking animation
.file-upload-area     # Drag-and-drop zones
.scrollbar-thin       # Custom scrollbars
```

## Features in Detail

### Real-time Communication
- Automatic message polling every 3 seconds
- Optimistic UI updates for sent messages
- Loading states and error handling
- Session persistence across page reloads

### File Handling
- Drag-and-drop file uploads
- File type validation and size limits
- Progress indicators and error states
- Support for documents, images, and audio

### Voice Messages
- Browser-based audio recording
- Automatic transcription display
- Audio playback controls
- Microphone permission handling

### Responsive Design
- Mobile-first approach
- Touch-friendly interface
- Adaptive layouts for all screen sizes
- Progressive enhancement

## Performance Optimizations

- **Code Splitting**: Automatic route-based code splitting
- **Image Optimization**: Next.js Image component
- **Bundle Analysis**: Webpack bundle analyzer integration
- **Caching**: API response caching where appropriate

## Security Considerations

- **Session Tokens**: Secure token-based authentication
- **Input Validation**: Client-side validation with server verification
- **File Upload Security**: File type and size restrictions
- **XSS Protection**: Sanitized user inputs and outputs

## Development

### Available Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript checker
```

### Code Quality

- **TypeScript**: Full type safety
- **ESLint**: Code linting and formatting
- **Prettier**: Code formatting (via ESLint)
- **Husky**: Git hooks for quality checks

## Deployment

### Build for Production

```bash
npm run build
npm run start
```

### Environment Variables for Production

```env
NEXT_PUBLIC_API_BASE=https://your-api-domain.com
NEXT_PUBLIC_DEMO_WORKSPACE_ID=your-workspace-id
```

### Deployment Platforms

The app can be deployed to:
- **Vercel** (recommended for Next.js)
- **Netlify**
- **AWS Amplify**
- **Docker containers**

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **API Connection Errors**: Check backend is running on correct port
2. **File Upload Failures**: Verify file size and type restrictions
3. **Audio Recording Issues**: Check browser microphone permissions
4. **Session Expiration**: Clear localStorage and restart session

### Debug Mode

Enable debug logging by setting:
```javascript
localStorage.setItem('debug', 'true')
```

## License

This project is part of the AI Personal Business Assistant system.